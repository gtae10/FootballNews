from datetime import timezone
from unittest.mock import call, patch, MagicMock

from rss_collector import collect_from_rss


def _mock_entry(published_parsed=None):
    mock_entry = MagicMock()
    mock_entry.get.side_effect = lambda key, default="": {
        "link": "https://example.com/article/1",
        "title": "테스트 기사 제목",
        "summary": "테스트 요약 내용",
    }.get(key, default)
    mock_entry.published_parsed = published_parsed
    return mock_entry


@patch("rss_collector.feedparser.parse")
def test_collect_from_rss_returns_parsed_articles(mock_parse):
    mock_feed = MagicMock()
    mock_feed.entries = [_mock_entry(published_parsed=None)]
    mock_parse.return_value = mock_feed

    articles = collect_from_rss("테스트 매체", "https://example.com/feed")

    assert len(articles) == 1
    assert articles[0].source == "테스트 매체"
    assert articles[0].original_url == "https://example.com/article/1"
    assert articles[0].title_original == "테스트 기사 제목"


@patch("rss_collector.feedparser.parse")
def test_collect_from_rss_published_at_is_timezone_aware(mock_parse):
    mock_feed = MagicMock()
    mock_feed.entries = [_mock_entry(published_parsed=None)]
    mock_parse.return_value = mock_feed

    articles = collect_from_rss("테스트 매체", "https://example.com/feed")

    assert articles[0].published_at.tzinfo == timezone.utc


@patch("rss_collector.feedparser.parse")
def test_collect_from_rss_parses_published_parsed_as_utc(mock_parse):
    struct_time = (2026, 8, 30, 10, 0, 0, 0, 0, 0)
    mock_feed = MagicMock()
    mock_feed.entries = [_mock_entry(published_parsed=struct_time)]
    mock_parse.return_value = mock_feed

    articles = collect_from_rss("테스트 매체", "https://example.com/feed")

    assert articles[0].published_at.tzinfo == timezone.utc
    assert articles[0].published_at.year == 2026
    assert articles[0].published_at.month == 8
    assert articles[0].published_at.day == 30


@patch("rss_collector.feedparser.parse")
def test_collect_from_rss_passes_through_forced_club_and_source_tier(mock_parse):
    mock_feed = MagicMock()
    mock_feed.entries = [_mock_entry(published_parsed=None)]
    mock_parse.return_value = mock_feed

    articles = collect_from_rss(
        "테스트 매체", "https://example.com/feed", forced_club="Liverpool", source_tier=2
    )

    assert articles[0].forced_club == "Liverpool"
    assert articles[0].source_tier == 2


def _mock_feed_with(n: int):
    feed = MagicMock()
    feed.entries = [_mock_entry() for _ in range(n)]
    return feed


@patch("rss_collector.feedparser.parse")
def test_collect_from_rss_default_max_pages_makes_only_one_request(mock_parse):
    mock_parse.return_value = _mock_feed_with(1)

    collect_from_rss("테스트 매체", "https://example.com/feed")

    mock_parse.assert_called_once_with("https://example.com/feed")


@patch("rss_collector.feedparser.parse")
def test_collect_from_rss_with_max_pages_requests_paged_urls_and_merges_results(mock_parse):
    mock_parse.side_effect = [_mock_feed_with(2), _mock_feed_with(3), _mock_feed_with(1)]

    articles = collect_from_rss("테스트 매체", "https://example.com/feed", max_pages=3)

    assert len(articles) == 6  # 2 + 3 + 1
    mock_parse.assert_has_calls(
        [
            call("https://example.com/feed"),
            call("https://example.com/feed?paged=2"),
            call("https://example.com/feed?paged=3"),
        ]
    )


@patch("rss_collector.feedparser.parse")
def test_collect_from_rss_appends_paged_param_when_url_already_has_query(mock_parse):
    mock_parse.side_effect = [_mock_feed_with(1), _mock_feed_with(1)]

    collect_from_rss("테스트 매체", "https://example.com/feed?lang=en", max_pages=2)

    mock_parse.assert_any_call("https://example.com/feed?lang=en&paged=2")


@patch("rss_collector.feedparser.parse")
def test_collect_from_rss_stops_early_when_a_page_has_no_entries(mock_parse):
    mock_parse.side_effect = [_mock_feed_with(2), _mock_feed_with(0), _mock_feed_with(5)]

    articles = collect_from_rss("테스트 매체", "https://example.com/feed", max_pages=5)

    assert len(articles) == 2  # 아카이브 끝에 도달하면 이후 페이지는 요청하지 않음
    assert mock_parse.call_count == 2


@patch("rss_collector.time.sleep")
@patch("rss_collector.feedparser.parse")
def test_collect_from_rss_sleeps_between_pages_but_not_after_the_last_page(mock_parse, mock_sleep):
    mock_parse.side_effect = [_mock_feed_with(1), _mock_feed_with(1), _mock_feed_with(1)]

    collect_from_rss("테스트 매체", "https://example.com/feed", max_pages=3, delay_seconds=1.5)

    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(1.5)


@patch("rss_collector.time.sleep")
@patch("rss_collector.feedparser.parse")
def test_collect_from_rss_does_not_sleep_when_delay_seconds_is_zero(mock_parse, mock_sleep):
    mock_parse.side_effect = [_mock_feed_with(1), _mock_feed_with(1)]

    collect_from_rss("테스트 매체", "https://example.com/feed", max_pages=2, delay_seconds=0)

    mock_sleep.assert_not_called()
