from unittest.mock import patch

from sqlalchemy import create_engine, text

from backfill_missing_content import (
    MIN_CONTENT_LENGTH,
    cleanup_short_content_articles,
    find_short_content_articles,
)


def _make_engine():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    original_url TEXT,
                    content_original TEXT
                )
                """
            )
        )
        connection.execute(
            text("CREATE TABLE article_clubs (article_id INTEGER, club_name TEXT)")
        )
        connection.execute(
            text("CREATE TABLE article_images (article_id INTEGER, position INTEGER, image_url TEXT)")
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
        connection.execute(text("CREATE TABLE rumor_threads (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE translations (article_id INTEGER, title_ko TEXT, content_ko TEXT)"
            )
        )
    return engine


def _insert_article(engine, source, url, content):
    with engine.begin() as connection:
        result = connection.execute(
            text(
                "INSERT INTO articles (source, original_url, content_original) "
                "VALUES (:source, :url, :content)"
            ),
            {"source": source, "url": url, "content": content},
        )
        return result.lastrowid


def test_find_short_content_articles_includes_empty_and_below_threshold():
    engine = _make_engine()
    empty_id = _insert_article(engine, "Sky Sports Football", "https://example.com/1", "")
    short_id = _insert_article(engine, "Sky Sports Football", "https://example.com/2", "too short")
    ok_id = _insert_article(engine, "Sky Sports Football", "https://example.com/3", "x" * MIN_CONTENT_LENGTH)

    rows = find_short_content_articles(engine)

    found_ids = {row.id for row in rows}
    assert empty_id in found_ids
    assert short_id in found_ids
    assert ok_id not in found_ids


@patch("backfill_missing_content.fetch_recovered_content")
def test_cleanup_recovers_article_when_content_can_be_fetched(mock_fetch):
    engine = _make_engine()
    article_id = _insert_article(engine, "Sky Sports Football", "https://example.com/1", "")
    mock_fetch.return_value = "A" * (MIN_CONTENT_LENGTH + 10)

    recovered, deleted, deleted_by_source = cleanup_short_content_articles(engine)

    assert recovered == 1
    assert deleted == 0
    with engine.connect() as connection:
        content = connection.execute(
            text("SELECT content_original FROM articles WHERE id = :id"), {"id": article_id}
        ).scalar_one()
    assert content == "A" * (MIN_CONTENT_LENGTH + 10)


@patch("backfill_missing_content.fetch_recovered_content")
def test_cleanup_deletes_article_and_related_rows_when_content_cannot_be_recovered(mock_fetch):
    engine = _make_engine()
    article_id = _insert_article(engine, "Sky Sports Football", "https://example.com/1", "")
    mock_fetch.return_value = None
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO article_clubs (article_id, club_name) VALUES (:id, 'Liverpool')"),
            {"id": article_id},
        )
        connection.execute(
            text(
                "INSERT INTO article_images (article_id, position, image_url) "
                "VALUES (:id, 0, 'https://example.com/img.jpg')"
            ),
            {"id": article_id},
        )
        connection.execute(
            text("INSERT INTO translations (article_id, title_ko, content_ko) VALUES (:id, 't', 'c')"),
            {"id": article_id},
        )

    recovered, deleted, deleted_by_source = cleanup_short_content_articles(engine)

    assert recovered == 0
    assert deleted == 1
    assert deleted_by_source == {"Sky Sports Football": 1}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM articles")).scalar() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM article_clubs")).scalar() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM article_images")).scalar() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM translations")).scalar() == 0


@patch("backfill_missing_content.fetch_recovered_content")
def test_cleanup_deletes_rumor_thread_left_empty_by_the_deleted_article(mock_fetch):
    """삭제된 기사가 어떤 루머 스레드의 마지막 연결이었다면, 그 빈 스레드도 함께
    정리해 고아 레코드를 남기지 않는다."""
    engine = _make_engine()
    article_id = _insert_article(engine, "Sky Sports Football", "https://example.com/1", "")
    mock_fetch.return_value = None
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO rumor_threads (id) VALUES (1)"))
        connection.execute(
            text("INSERT INTO rumor_thread_articles (rumor_thread_id, article_id) VALUES (1, :id)"),
            {"id": article_id},
        )

    cleanup_short_content_articles(engine)

    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM rumor_threads")).scalar() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM rumor_thread_articles")).scalar() == 0


@patch("backfill_missing_content.fetch_recovered_content")
def test_cleanup_keeps_rumor_thread_still_used_by_other_articles(mock_fetch):
    """같은 스레드에 다른 기사가 남아 있으면 스레드 자체는 지우지 않는다."""
    engine = _make_engine()
    bad_article_id = _insert_article(engine, "Sky Sports Football", "https://example.com/1", "")
    other_article_id = _insert_article(
        engine, "Sky Sports Football", "https://example.com/2", "fine content that is long enough"
    )
    mock_fetch.return_value = None
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO rumor_threads (id) VALUES (1)"))
        connection.execute(
            text("INSERT INTO rumor_thread_articles (rumor_thread_id, article_id) VALUES (1, :id)"),
            {"id": bad_article_id},
        )
        connection.execute(
            text("INSERT INTO rumor_thread_articles (rumor_thread_id, article_id) VALUES (1, :id)"),
            {"id": other_article_id},
        )

    cleanup_short_content_articles(engine)

    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM rumor_threads")).scalar() == 1
