from datetime import timezone
from unittest.mock import call, patch, MagicMock

from rss_collector import collect_from_rss, _extract_image_url


class _FakeEntry:
    """MagicMock 대신 쓰는 간단한 가짜 feedparser 엔트리.

    MagicMock은 정의하지 않은 속성(media_thumbnail 등)에 접근해도 자동으로
    또 다른 MagicMock을 만들어 반환하기 때문에("있음"으로 오인됨), 이미지 추출
    경로별 분기(있음/없음)를 검증하려면 진짜로 속성이 "없을 때 없는" 이 가짜
    객체가 필요하다.
    """

    def __init__(self, data=None, **attrs):
        self._data = data or {}
        for key, value in attrs.items():
            setattr(self, key, value)

    def get(self, key, default=""):
        return self._data.get(key, default)


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
def test_collect_from_rss_unescapes_double_encoded_html_entities(mock_parse):
    """일부 워드프레스 RSS는 "&#8217;"처럼 이중 인코딩된 엔티티를 그대로 내려줘서
    화면에 글자 대신 엔티티 코드가 노출되는 문제가 실제 DB에서 발견됨."""
    mock_entry = MagicMock()
    mock_entry.get.side_effect = lambda key, default="": {
        "link": "https://example.com/article/1",
        "title": "Keane blasts Iraola&#8217;s side &#8216;all over the shop&#8217;",
        "summary": "It&#8217;s a big moment.",
    }.get(key, default)
    mock_entry.published_parsed = None
    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]
    mock_parse.return_value = mock_feed

    articles = collect_from_rss("테스트 매체", "https://example.com/feed")

    assert articles[0].title_original == "Keane blasts Iraola’s side ‘all over the shop’"
    assert articles[0].content_original == "It’s a big moment."


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


def test_extract_image_url_from_media_thumbnail():
    entry = _FakeEntry(media_thumbnail=[{"url": "https://example.com/thumb.jpg"}])

    assert _extract_image_url(entry) == "https://example.com/thumb.jpg"


def test_extract_image_url_from_media_content_with_image_medium():
    entry = _FakeEntry(media_content=[{"url": "https://example.com/photo.jpg", "medium": "image"}])

    assert _extract_image_url(entry) == "https://example.com/photo.jpg"


def test_extract_image_url_from_media_content_with_image_mime_type():
    entry = _FakeEntry(media_content=[{"url": "https://example.com/photo.jpg", "type": "image/jpeg"}])

    assert _extract_image_url(entry) == "https://example.com/photo.jpg"


def test_extract_image_url_ignores_non_image_media_content():
    entry = _FakeEntry(media_content=[{"url": "https://example.com/clip.mp4", "type": "video/mp4"}])

    assert _extract_image_url(entry) is None


def test_extract_image_url_from_image_enclosure():
    entry = _FakeEntry(enclosures=[{"href": "https://example.com/enclosure.jpg", "type": "image/jpeg"}])

    assert _extract_image_url(entry) == "https://example.com/enclosure.jpg"


def test_extract_image_url_ignores_non_image_enclosure():
    entry = _FakeEntry(enclosures=[{"href": "https://example.com/audio.mp3", "type": "audio/mpeg"}])

    assert _extract_image_url(entry) is None


def test_extract_image_url_falls_back_to_img_tag_in_summary():
    entry = _FakeEntry({"summary": '<p>본문 내용 <img src="https://example.com/inline.jpg" alt=""></p>'})

    assert _extract_image_url(entry) == "https://example.com/inline.jpg"


def test_extract_image_url_prefers_media_thumbnail_over_summary_img_tag():
    entry = _FakeEntry(
        {"summary": '<img src="https://example.com/inline.jpg">'},
        media_thumbnail=[{"url": "https://example.com/thumb.jpg"}],
    )

    assert _extract_image_url(entry) == "https://example.com/thumb.jpg"


def test_extract_image_url_returns_none_when_nothing_found():
    entry = _FakeEntry({"summary": "이미지가 전혀 없는 본문입니다."})

    assert _extract_image_url(entry) is None


@patch("rss_collector.feedparser.parse")
def test_collect_from_rss_includes_extracted_image_url(mock_parse):
    entry = _FakeEntry(
        {
            "link": "https://example.com/article/1",
            "title": "제목",
            "summary": "요약",
        },
        media_thumbnail=[{"url": "https://example.com/thumb.jpg"}],
    )
    mock_feed = MagicMock()
    mock_feed.entries = [entry]
    mock_parse.return_value = mock_feed

    articles = collect_from_rss("테스트 매체", "https://example.com/feed")

    assert articles[0].image_url == "https://example.com/thumb.jpg"


@patch("rss_collector.feedparser.parse")
def test_collect_from_rss_sets_image_url_to_none_when_not_found(mock_parse):
    entry = _FakeEntry(
        {
            "link": "https://example.com/article/1",
            "title": "제목",
            "summary": "이미지 없는 요약",
        }
    )
    mock_feed = MagicMock()
    mock_feed.entries = [entry]
    mock_parse.return_value = mock_feed

    articles = collect_from_rss("테스트 매체", "https://example.com/feed")

    assert articles[0].image_url is None
