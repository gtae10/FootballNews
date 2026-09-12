from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text

import db
from db import save_articles
from rss_collector import CollectedArticle


# save_articles()는 기사마다 원문 페이지를 크롤링해 본문 이미지를 찾는다
# (body_image_extractor.fetch_body_images). DB 저장 로직만 검증하는 이 파일의
# 대부분의 테스트는 실제 네트워크 호출이나 지연(BODY_IMAGE_REQUEST_DELAY_SECONDS)
# 없이 결정적으로 빠르게 동작해야 하므로, 기본값으로 빈 리스트를 반환하도록
# 자동 패치한다. 이미지 저장 자체를 검증하는 테스트는 이 패치를 개별적으로
# 덮어쓴다(@patch("db.fetch_body_images", ...)가 더 안쪽에서 적용되어 우선한다).
@pytest.fixture(autouse=True)
def _no_network_body_image_crawl():
    with patch("db.fetch_body_images", return_value=[]), patch("db.time.sleep"):
        yield


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
                    image_url TEXT,
                    category TEXT
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
        connection.execute(
            text(
                """
                CREATE TABLE article_images (
                    article_id INTEGER,
                    position INTEGER,
                    image_url TEXT,
                    PRIMARY KEY (article_id, position)
                )
                """
            )
        )
    return engine


# save_articles()는 매번 clubs 테이블을 조회해 별칭 맵을 만드는데, 이 파일의 테스트는 DB
# 저장 로직만 검증하면 되므로 db._load_alias_map을 고정 값으로 대체해 clubs 테이블을 매번
# 만들 필요 없이 결정적으로 동작하게 한다. 감지 로직 자체(별칭 매칭)는 test_club_matcher.py에서,
# _load_alias_map 자체의 조회/실패 처리는 아래 별도 테스트에서 검증한다.
_ALIAS_MAP = {"Liverpool": ["Liverpool"], "Arsenal": ["Arsenal"]}


def test_load_alias_map_builds_map_from_clubs_table():
    engine = _make_engine()
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE clubs (id INTEGER PRIMARY KEY, name TEXT, league TEXT)"))
        connection.execute(text("INSERT INTO clubs (id, name, league) VALUES (1, 'Liverpool', 'EPL')"))

    alias_map = db._load_alias_map(engine)

    assert "Liverpool" in alias_map["Liverpool"]


def test_load_alias_map_logs_clearly_and_returns_empty_map_when_clubs_table_missing(capsys):
    """clubs 테이블 조회가 실패해도(예외 상황) 수집 자체는 막지 않아야 하지만, 예전처럼
    조용히 넘어가지 않고 눈에 띄는 경고를 남겨야 한다 — 백엔드가 꺼져 있으면 구단 태깅이
    통째로 스킵되는데 로그에서 알아차리기 어려웠던 문제가 실제로 있었다."""
    engine = create_engine("sqlite:///:memory:")  # clubs 테이블을 일부러 만들지 않음

    alias_map = db._load_alias_map(engine)

    assert alias_map == {}
    captured = capsys.readouterr()
    assert "[WARNING]" in captured.err
    assert "clubs" in captured.err


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


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
def test_save_articles_stores_transfer_category_when_clustered(mock_alias_map):
    engine = _make_engine()
    article = CollectedArticle(
        source="The Anfield Wrap",
        original_url="https://theanfieldwrap.com/article/isak-category",
        title_original="Liverpool make contact over Alexander Isak",
        content_original="Liverpool are keen on a deal for the striker.",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club="Liverpool",
        source_tier=2,
    )

    save_articles(engine, [article])

    with engine.begin() as connection:
        row = connection.execute(text("SELECT category FROM articles")).one()
        assert row.category == "TRANSFER"


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
def test_save_articles_stores_match_category_for_match_report(mock_alias_map):
    engine = _make_engine()
    article = CollectedArticle(
        source="Sky Sports Football",
        original_url="https://www.skysports.com/article/match-report",
        title_original="Match report: Liverpool 3-1 Arsenal",
        content_original="Goals from Salah and Nunez sealed the win.",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club=None,
        source_tier=1,
    )

    save_articles(engine, [article])

    with engine.begin() as connection:
        row = connection.execute(text("SELECT category FROM articles")).one()
        assert row.category == "MATCH"


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
def test_save_articles_stores_other_category_when_nothing_matches(mock_alias_map):
    engine = _make_engine()
    article = CollectedArticle(
        source="Football365",
        original_url="https://www.football365.com/article/broadcast-deal",
        title_original="Premier League announces new broadcast deal",
        content_original="The league-wide announcement does not mention any specific club.",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club=None,
        source_tier=2,
    )

    save_articles(engine, [article])

    with engine.begin() as connection:
        row = connection.execute(text("SELECT category FROM articles")).one()
        assert row.category == "OTHER"


def _image_urls(connection, article_id):
    rows = connection.execute(
        text("SELECT image_url FROM article_images WHERE article_id = :id ORDER BY position"),
        {"id": article_id},
    ).all()
    return [row.image_url for row in rows]


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
@patch("db.fetch_body_images", return_value=["https://example.com/body1.jpg", "https://example.com/body2.jpg"])
def test_save_articles_stores_crawled_body_images_in_order(mock_fetch, mock_alias_map):
    engine = _make_engine()
    article = CollectedArticle(
        source="The Anfield Wrap",
        original_url="https://theanfieldwrap.com/article/with-body-images",
        title_original="Test Title",
        content_original="Test Summary",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club="Liverpool",
        source_tier=2,
        image_url="https://theanfieldwrap.com/thumb.jpg",
    )

    save_articles(engine, [article])

    with engine.begin() as connection:
        article_id = connection.execute(text("SELECT id FROM articles")).one().id
        assert _image_urls(connection, article_id) == [
            "https://example.com/body1.jpg",
            "https://example.com/body2.jpg",
        ]
    mock_fetch.assert_called_once_with(
        "https://theanfieldwrap.com/article/with-body-images",
        exclude_url="https://theanfieldwrap.com/thumb.jpg",
    )


@patch("db._load_alias_map", return_value=_ALIAS_MAP)
@patch("db.fetch_body_images", return_value=[])
def test_save_articles_stores_no_body_images_when_crawl_fails_or_finds_none(mock_fetch, mock_alias_map):
    """본문 크롤링이 실패하거나 이미지를 못 찾으면 article_images에 아무 row도 남기지
    않는다 — 프론트는 기존 대표 이미지(image_url) 하나만 표시하는 상태로 자연스럽게
    폴백한다."""
    engine = _make_engine()
    article = CollectedArticle(
        source="Sky Sports Football",
        original_url="https://www.skysports.com/article/no-body-images",
        title_original="Test Title",
        content_original="Test Summary",
        published_at=datetime(2026, 8, 30, 10, 0),
        forced_club=None,
        source_tier=1,
        image_url="https://www.skysports.com/thumb.jpg",
    )

    save_articles(engine, [article])

    with engine.begin() as connection:
        article_id = connection.execute(text("SELECT id FROM articles")).one().id
        assert _image_urls(connection, article_id) == []
