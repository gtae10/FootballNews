from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text

from db import (
    UntranslatedArticle,
    count_translated_today,
    fetch_untranslated_articles,
    save_translation,
)


class _FakeTranslationResult:
    def __init__(self, title_ko, content_ko, model_version):
        self.title_ko = title_ko
        self.content_ko = content_ko
        self.model_version = model_version


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
                    status TEXT,
                    source_tier INTEGER,
                    quoted_reporter TEXT,
                    published_at TEXT
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
        # priority.py가 쓰는 교차 검증 정보(우선순위 2순위) — 이 파일의 대부분 테스트는
        # 루머 스레드가 없는 기사만 다루므로 빈 테이블로 둬도 LEFT JOIN에는 문제없다.
        connection.execute(
            text(
                """
                CREATE TABLE rumor_thread_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rumor_thread_id INTEGER,
                    article_id INTEGER,
                    story_stage TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE rumor_threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    independent_source_count INTEGER
                )
                """
            )
        )
    return engine


def test_fetch_untranslated_articles_returns_only_collected_status():
    engine = _make_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO articles (title_original, content_original, status) "
                "VALUES ('아직 번역 안 됨', '본문1', 'COLLECTED')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO articles (title_original, content_original, status) "
                "VALUES ('이미 번역됨', '본문2', 'TRANSLATED')"
            )
        )

    articles = fetch_untranslated_articles(engine)

    assert len(articles) == 1
    assert isinstance(articles[0], UntranslatedArticle)
    assert articles[0].title_original == "아직 번역 안 됨"


def test_fetch_untranslated_articles_includes_priority_metadata():
    engine = _make_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO articles "
                "(title_original, content_original, status, source_tier, quoted_reporter) "
                "VALUES ('제목', '본문', 'COLLECTED', 1, 'Fabrizio Romano')"
            )
        )

    articles = fetch_untranslated_articles(engine)

    assert articles[0].source_tier == 1
    assert articles[0].quoted_reporter == "Fabrizio Romano"


def test_fetch_untranslated_articles_includes_rumor_thread_source_count():
    engine = _make_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO articles (title_original, content_original, status) "
                "VALUES ('제목', '본문', 'COLLECTED')"
            )
        )
        connection.execute(
            text("INSERT INTO rumor_threads (id, independent_source_count) VALUES (1, 3)")
        )
        connection.execute(
            text(
                "INSERT INTO rumor_thread_articles (rumor_thread_id, article_id) VALUES (1, 1)"
            )
        )

    articles = fetch_untranslated_articles(engine)

    assert articles[0].independent_source_count == 3


def test_fetch_untranslated_articles_leaves_source_count_none_when_no_rumor_thread():
    engine = _make_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO articles (title_original, content_original, status) "
                "VALUES ('제목', '본문', 'COLLECTED')"
            )
        )

    articles = fetch_untranslated_articles(engine)

    assert articles[0].independent_source_count is None


def test_count_translated_today_counts_only_todays_translations():
    engine = _make_engine()
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO translations (article_id, title_ko, content_ko, model_version, translated_at) "
                "VALUES (1, 't', 'c', 'm', :translated_at)"
            ),
            {"translated_at": now},
        )
        connection.execute(
            text(
                "INSERT INTO translations (article_id, title_ko, content_ko, model_version, translated_at) "
                "VALUES (2, 't', 'c', 'm', :translated_at)"
            ),
            {"translated_at": now - timedelta(days=1)},
        )

    assert count_translated_today(engine) == 1


def test_save_translation_inserts_row_and_updates_article_status():
    engine = _make_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO articles (title_original, content_original, status) "
                "VALUES ('제목', '본문', 'COLLECTED')"
            )
        )

    result = _FakeTranslationResult("번역된 제목", "번역된 요약", "claude-opus-5")
    save_translation(engine, 1, result)

    with engine.begin() as connection:
        translation_row = connection.execute(
            text("SELECT article_id, title_ko, content_ko, model_version FROM translations")
        ).one()
        article_status = connection.execute(
            text("SELECT status FROM articles WHERE id = 1")
        ).scalar_one()

    assert translation_row.article_id == 1
    assert translation_row.title_ko == "번역된 제목"
    assert translation_row.content_ko == "번역된 요약"
    assert translation_row.model_version == "claude-opus-5"
    assert article_status == "TRANSLATED"
