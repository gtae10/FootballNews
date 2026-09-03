"""번역 파이프라인 전체 배관(plumbing)이 실제로 연결돼 있는지 확인하는 테스트.

test_translate.py의 run_translation_batch 테스트는 db 모듈 전체를 mock으로 대체해
호출 인자만 검증하지만, 이 파일은 db.fetch_untranslated_articles / db.save_translation을
실제로 실행해(SQLite in-memory) status 필터링, translations 저장, status 갱신,
시스템 프롬프트에 용어집이 실제로 포함되는지까지 end-to-end로 검증한다.
Anthropic 클라이언트 호출만 MagicMock으로 대체하며, 실제 네트워크 요청은 발생하지 않는다.
"""

import json
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, text

import translate
from glossary import FOOTBALL_GLOSSARY


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


def _mock_response(payload: dict):
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = json.dumps(payload, ensure_ascii=False)
    response = MagicMock()
    response.content = [text_block]
    return response


def _make_mock_client(captured_calls):
    client = MagicMock()

    def _create(**kwargs):
        captured_calls.append(kwargs)
        return _mock_response({"title_ko": "MOCK 제목", "content_ko": "MOCK 요약"})

    client.messages.create.side_effect = _create
    return client


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

    captured_calls = []
    with patch("translate.db.get_engine", return_value=engine), \
         patch("translate._get_client", return_value=_make_mock_client(captured_calls)), \
         patch("translate.anthropic.Anthropic") as mock_anthropic_ctor:
        translated_count = translate.run_translation_batch()

    assert translated_count == 2
    mock_anthropic_ctor.assert_not_called()  # 실제 Anthropic 클라이언트는 생성조차 되지 않는다.
    assert len(captured_calls) == 2  # 이미 TRANSLATED인 기사는 호출 대상에서 제외됨.

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
        assert row.model_version == translate.MODEL


def test_run_translation_batch_sends_glossary_in_system_prompt():
    engine = _make_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO articles (title_original, content_original, status) "
                "VALUES ('제목', '본문', 'COLLECTED')"
            )
        )

    captured_calls = []
    with patch("translate.db.get_engine", return_value=engine), \
         patch("translate._get_client", return_value=_make_mock_client(captured_calls)):
        translate.run_translation_batch()

    assert len(captured_calls) == 1
    system_prompt = captured_calls[0]["system"]
    for en, ko in FOOTBALL_GLOSSARY.items():
        assert en in system_prompt
        assert ko in system_prompt


def test_run_translation_batch_does_not_reprocess_already_translated_articles():
    engine = _make_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO articles (title_original, content_original, status) "
                "VALUES ('제목', '본문', 'COLLECTED')"
            )
        )

    captured_calls = []
    with patch("translate.db.get_engine", return_value=engine), \
         patch("translate._get_client", return_value=_make_mock_client(captured_calls)):
        first_run_count = translate.run_translation_batch()

    with patch("translate.db.get_engine", return_value=engine), \
         patch("translate._get_client", return_value=_make_mock_client(captured_calls)):
        second_run_count = translate.run_translation_batch()

    assert first_run_count == 1
    assert second_run_count == 0  # status가 TRANSLATED로 바뀌었으므로 재조회 대상에서 제외.
    assert len(captured_calls) == 1  # 두 번째 실행에서는 클라이언트가 호출되지 않음.
