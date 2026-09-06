from sqlalchemy import create_engine, text

from backfill_categories import backfill_uncategorized_articles


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
                    category TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE rumor_thread_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rumor_thread_id INTEGER,
                    article_id INTEGER
                )
                """
            )
        )
    return engine


def _insert_article(engine, title, content, category=None):
    with engine.begin() as connection:
        result = connection.execute(
            text(
                "INSERT INTO articles (title_original, content_original, category) "
                "VALUES (:title, :content, :category)"
            ),
            {"title": title, "content": content, "category": category},
        )
        return result.lastrowid


def _category_of(engine, article_id):
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT category FROM articles WHERE id = :id"), {"id": article_id}
        ).one()
        return row.category


def test_backfill_classifies_article_already_in_rumor_thread_as_transfer():
    engine = _make_engine()
    article_id = _insert_article(engine, "Isak nets brace as Liverpool cruise to win", "A big win at Anfield.")
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO rumor_thread_articles (rumor_thread_id, article_id) VALUES (1, :id)"),
            {"id": article_id},
        )

    counts = backfill_uncategorized_articles(engine)

    assert _category_of(engine, article_id) == "TRANSFER"
    assert counts["TRANSFER"] == 1


def test_backfill_classifies_unclustered_match_report_as_match():
    engine = _make_engine()
    article_id = _insert_article(
        engine, "Match report: Liverpool 3-1 Arsenal", "Goals from Salah and Nunez sealed the win."
    )

    counts = backfill_uncategorized_articles(engine)

    assert _category_of(engine, article_id) == "MATCH"
    assert counts["MATCH"] == 1


def test_backfill_skips_articles_that_already_have_a_category():
    engine = _make_engine()
    article_id = _insert_article(
        engine, "Match report: Liverpool 3-1 Arsenal", "Goals from Salah and Nunez sealed the win.",
        category="OTHER",
    )

    counts = backfill_uncategorized_articles(engine)

    assert _category_of(engine, article_id) == "OTHER"
    assert counts == {}
