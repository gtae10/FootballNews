from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine, text

from db import save_articles
from rss_collector import CollectedArticle


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
                    published_at TEXT,
                    collected_at TEXT,
                    status TEXT,
                    source_tier INTEGER,
                    quoted_reporter TEXT,
                    image_url TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE article_clubs (
                    article_id INTEGER,
                    club_name TEXT,
                    PRIMARY KEY (article_id, club_name)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE rumor_threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT,
                    club_name TEXT,
                    latest_stage TEXT,
                    independent_source_count INTEGER,
                    cross_reported INTEGER,
                    created_at TEXT,
                    updated_at TEXT
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
                    article_id INTEGER,
                    story_stage TEXT
                )
                """
            )
        )
    return engine


# save_articles()는 매번 GET /clubs를 호출해 별칭 맵을 만드는데, 이 파일의 테스트는 DB
# 저장 로직만 검증하면 되므로 club_matcher._load_alias_map을 고정 값으로 대체해 네트워크
# 호출 없이 결정적으로 동작하게 한다. 감지 로직 자체(별칭 매칭)는 test_club_matcher.py에서 검증한다.
_ALIAS_MAP = {"Liverpool": ["Liverpool"], "Arsenal": ["Arsenal"]}


def _club_names(connection, article_id):
    rows = connection.execute(
        text("SELECT club_name FROM article_clubs WHERE article_id = :id ORDER BY club_name"),
        {"id": article_id},
    ).all()
    return [row.club_name for row in rows]


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
def test_save_articles_inserts_new_article_with_forced_club_and_tier(mock_alias_map):
    engine = _make_engine()
    article = CollectedArticle(
        source="The Anfield Wrap",
        original_url="https://theanfieldwrap.com/article/1",
        title_original="Test Title",
        content_original="Test Summary",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club="Liverpool",
        source_tier=2,
    )

    saved_count = save_articles(engine, [article])

    assert saved_count == 1
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT id, source, source_tier, status FROM articles")
        ).one()
        assert row.source == "The Anfield Wrap"
        assert row.source_tier == 2
        assert row.status == "COLLECTED"
        assert _club_names(connection, row.id) == ["Liverpool"]


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
def test_save_articles_persists_image_url_when_present(mock_alias_map):
    engine = _make_engine()
    article = CollectedArticle(
        source="The Anfield Wrap",
        original_url="https://theanfieldwrap.com/article/with-image",
        title_original="Test Title",
        content_original="Test Summary",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club="Liverpool",
        source_tier=2,
        image_url="https://theanfieldwrap.com/thumb.jpg",
    )

    save_articles(engine, [article])

    with engine.begin() as connection:
        row = connection.execute(text("SELECT image_url FROM articles")).one()
        assert row.image_url == "https://theanfieldwrap.com/thumb.jpg"


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
def test_save_articles_stores_null_image_url_when_not_found(mock_alias_map):
    engine = _make_engine()
    article = CollectedArticle(
        source="The Anfield Wrap",
        original_url="https://theanfieldwrap.com/article/no-image",
        title_original="Test Title",
        content_original="Test Summary",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club="Liverpool",
        source_tier=2,
    )

    save_articles(engine, [article])

    with engine.begin() as connection:
        row = connection.execute(text("SELECT image_url FROM articles")).one()
        assert row.image_url is None


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
def test_save_articles_detects_multiple_clubs_from_content(mock_alias_map):
    engine = _make_engine()
    article = CollectedArticle(
        source="Sky Sports Football",
        original_url="https://www.skysports.com/article/1",
        title_original="Liverpool reignite interest in Arsenal target",
        content_original="Liverpool and Arsenal are both chasing the same midfielder.",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club=None,
        source_tier=1,
    )

    save_articles(engine, [article])

    with engine.begin() as connection:
        row = connection.execute(text("SELECT id FROM articles")).one()
        assert _club_names(connection, row.id) == ["Arsenal", "Liverpool"]


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
def test_save_articles_leaves_article_unclubbed_when_nothing_detected(mock_alias_map):
    engine = _make_engine()
    article = CollectedArticle(
        source="Sky Sports Football",
        original_url="https://www.skysports.com/article/2",
        title_original="Premier League announces new broadcast deal",
        content_original="The league-wide announcement does not mention any specific club.",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club=None,
        source_tier=1,
    )

    save_articles(engine, [article])

    with engine.begin() as connection:
        row = connection.execute(text("SELECT id FROM articles")).one()
        assert _club_names(connection, row.id) == []


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
def test_save_articles_skips_duplicate_original_url(mock_alias_map):
    engine = _make_engine()
    article = CollectedArticle(
        source="Empire of The Kop",
        original_url="https://www.empireofthekop.com/article/1",
        title_original="Title",
        content_original="Summary",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club="Liverpool",
        source_tier=3,
    )

    first_saved = save_articles(engine, [article])
    second_saved = save_articles(engine, [article])

    assert first_saved == 1
    assert second_saved == 0


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
def test_save_articles_creates_rumor_thread_when_player_name_and_club_detected(mock_alias_map):
    engine = _make_engine()
    article = CollectedArticle(
        source="The Anfield Wrap",
        original_url="https://theanfieldwrap.com/article/isak",
        title_original="Liverpool make contact over Alexander Isak",
        content_original="Liverpool are keen on a deal for the striker.",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club="Liverpool",
        source_tier=2,
    )

    save_articles(engine, [article])

    with engine.begin() as connection:
        thread = connection.execute(
            text("SELECT player_name, club_name, latest_stage FROM rumor_threads")
        ).one()
        assert thread.player_name == "Alexander Isak"
        assert thread.club_name == "Liverpool"
        assert thread.latest_stage == "INTEREST"

        link = connection.execute(text("SELECT article_id FROM rumor_thread_articles")).one()
        article_id = connection.execute(text("SELECT id FROM articles")).one().id
        assert link.article_id == article_id


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
def test_save_articles_does_not_create_rumor_thread_when_story_stage_is_unknown(mock_alias_map):
    """이적 관련 키워드가 전혀 없는 기사(예: 경기 리포트)는 선수명+구단이 함께 언급돼도
    루머 스레드로 묶이지 않는다 — 그렇지 않으면 이적과 무관한 기사가 "교차검증"으로
    오인될 수 있다."""
    engine = _make_engine()
    article = CollectedArticle(
        source="Sky Sports Football",
        original_url="https://www.skysports.com/article/isak-brace",
        title_original="Isak nets double as Liverpool win",
        content_original="A dominant performance saw the striker score twice.",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club="Liverpool",
        source_tier=1,
    )

    save_articles(engine, [article])

    with engine.begin() as connection:
        count = connection.execute(text("SELECT COUNT(*) AS cnt FROM rumor_threads")).one()
        assert count.cnt == 0


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
def test_save_articles_does_not_create_rumor_thread_when_no_club_detected(mock_alias_map):
    engine = _make_engine()
    article = CollectedArticle(
        source="Sky Sports Football",
        original_url="https://www.skysports.com/article/isak-league",
        title_original="Alexander Isak wins Premier League player of the month",
        content_original="A league-wide award with no specific club angle.",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club=None,
        source_tier=1,
    )

    save_articles(engine, [article])

    with engine.begin() as connection:
        count = connection.execute(text("SELECT COUNT(*) AS cnt FROM rumor_threads")).one()
        assert count.cnt == 0
