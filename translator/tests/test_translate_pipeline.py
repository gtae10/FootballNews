"""번역 파이프라인 전체 배관(plumbing)이 실제로 연결돼 있는지 확인하는 테스트.

test_translate.py는 db 모듈 전체를 mock으로 대체해 호출 인자만 검증하지만, 이
파일은 db.fetch_untranslated_articles / db.save_translation을 실제로 실행해
(SQLite in-memory) status 필터링, translations 저장, status 갱신, 용어집
후처리까지 end-to-end로 검증한다. Argos Translate 호출만 mock으로 대체하며
(모델 다운로드나 실제 NMT 추론 없이), 실제 네트워크 요청은 발생하지 않는다.
"""

from unittest.mock import patch

from sqlalchemy import create_engine, text

import translate


def _make_engine():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title_original TEXT,
                    content_original TEXT,
                    status TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE translations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER,
                    title_ko TEXT,
                    content_ko TEXT,
                    model_version TEXT,
                    translated_at TEXT
                )
                """
            )
        )
    return engine


def test_run_translation_batch_only_translates_collected_articles():
    engine = _make_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO articles (title_original, content_original, status) "
                "VALUES ('아직 번역 안 됨 1', '본문1', 'COLLECTED')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO articles (title_original, content_original, status) "
                "VALUES ('아직 번역 안 됨 2', '본문2', 'COLLECTED')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO articles (title_original, content_original, status) "
                "VALUES ('이미 번역됨', '본문3', 'TRANSLATED')"
            )
        )

    with patch("translate.db.get_engine", return_value=engine), \
         patch("argos_engine.translate", return_value=("MOCK 제목", "MOCK 요약", "argos-translate-en-ko")) as mock_translate:
        translated_count = translate.run_translation_batch()

    assert translated_count == 2
    assert mock_translate.call_count == 2  # 이미 TRANSLATED인 기사는 호출 대상에서 제외됨.

    with engine.connect() as connection:
        statuses = connection.execute(
            text("SELECT id, status FROM articles ORDER BY id")
        ).fetchall()
        translation_rows = connection.execute(
            text("SELECT article_id, title_ko, content_ko, model_version FROM translations")
        ).fetchall()

    assert [row.status for row in statuses] == ["TRANSLATED", "TRANSLATED", "TRANSLATED"]
    assert len(translation_rows) == 2
    for row in translation_rows:
        assert row.title_ko == "MOCK 제목"
        assert row.content_ko == "MOCK 요약"
        assert row.model_version == "argos-translate-en-ko"


def test_run_translation_batch_applies_glossary_to_saved_translation():
    engine = _make_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO articles (title_original, content_original, status) "
                "VALUES ('제목', '본문', 'COLLECTED')"
            )
        )

    with patch("translate.db.get_engine", return_value=engine), \
         patch("argos_engine.translate", return_value=("제목", "We kept a clean sheet today", "argos-translate-en-ko")):
        translate.run_translation_batch()

    with engine.connect() as connection:
        row = connection.execute(text("SELECT content_ko FROM translations")).one()

    assert "무실점" in row.content_ko
    assert "clean sheet" not in row.content_ko.lower()


def test_run_translation_batch_does_not_reprocess_already_translated_articles():
    engine = _make_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO articles (title_original, content_original, status) "
                "VALUES ('제목', '본문', 'COLLECTED')"
            )
        )

    with patch("translate.db.get_engine", return_value=engine), \
         patch("argos_engine.translate", return_value=("MOCK", "MOCK", "argos-translate-en-ko")) as mock_translate:
        first_run_count = translate.run_translation_batch()
        second_run_count = translate.run_translation_batch()

    assert first_run_count == 1
    assert second_run_count == 0  # status가 TRANSLATED로 바뀌었으므로 재조회 대상에서 제외.
    assert mock_translate.call_count == 1  # 두 번째 실행에서는 엔진이 호출되지 않음.
