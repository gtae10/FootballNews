from sqlalchemy import create_engine, text

from db import UntranslatedArticle, fetch_untranslated_articles, save_translation


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
