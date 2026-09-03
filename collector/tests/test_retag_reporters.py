from sqlalchemy import create_engine, text

from retag_reporters import retag_reporters


def _make_engine():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    original_url TEXT UNIQUE,
                    title_original TEXT,
                    content_original TEXT,
                    source_tier INTEGER,
                    quoted_reporter TEXT
                )
                """
            )
        )
    return engine


def _insert_article(engine, title, content, source_tier=None, quoted_reporter=None):
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO articles (source, original_url, title_original, content_original, source_tier, quoted_reporter)
                VALUES ('Test Source', :url, :title, :content, :tier, :quoted_reporter)
                """
            ),
            {
                "url": f"https://example.com/{title}",
                "title": title,
                "content": content,
                "tier": source_tier,
                "quoted_reporter": quoted_reporter,
            },
        )
        return result.lastrowid


def _row(engine, article_id):
    with engine.begin() as connection:
        return connection.execute(
            text("SELECT quoted_reporter, source_tier FROM articles WHERE id = :id"),
            {"id": article_id},
        ).one()


def test_fills_quoted_reporter_and_upgrades_tier_when_detected():
    engine = _make_engine()
    article_id = _insert_article(
        engine,
        "Reds close in on deal",
        "Fabrizio Romano reports the deal is close to completion.",
        source_tier=3,
    )

    counts = retag_reporters(engine)

    row = _row(engine, article_id)
    assert row.quoted_reporter == "Fabrizio Romano"
    assert row.source_tier == 1
    assert counts["Fabrizio Romano"] == 1


def test_does_not_downgrade_tier_when_existing_tier_is_already_better():
    engine = _make_engine()
    article_id = _insert_article(
        engine,
        "Official announcement",
        "IndyKaila claims the move is imminent.",
        source_tier=1,
    )

    retag_reporters(engine)

    row = _row(engine, article_id)
    assert row.quoted_reporter == "IndyKaila"
    assert row.source_tier == 1


def test_leaves_quoted_reporter_null_when_nothing_detected():
    engine = _make_engine()
    article_id = _insert_article(
        engine, "Premier League fixture list", "The league announced the new fixture schedule.", source_tier=2
    )

    counts = retag_reporters(engine)

    row = _row(engine, article_id)
    assert row.quoted_reporter is None
    assert row.source_tier == 2
    assert counts == {}


def test_does_not_touch_articles_that_already_have_a_quoted_reporter():
    engine = _make_engine()
    article_id = _insert_article(
        engine,
        "Reds close in on deal",
        "Fabrizio Romano reports the deal is close to completion.",
        source_tier=3,
        quoted_reporter="Paul Joyce",
    )

    counts = retag_reporters(engine)

    row = _row(engine, article_id)
    assert row.quoted_reporter == "Paul Joyce"
    assert row.source_tier == 3
    assert counts == {}
