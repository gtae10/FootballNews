from unittest.mock import patch

from body_text_extractor import (
    extract_body_text,
    extract_og_description,
    fetch_recovered_content,
    recover_content_from_html,
)


def test_extract_body_text_joins_paragraphs_inside_article_tag():
    html = """
    <html><body>
        <article>
            <p>Palmer and Rogers have combined for nine chances this season, more than any other pair.</p>
            <p>Their understanding on the pitch has grown since their time together at Manchester City's academy.</p>
        </article>
    </body></html>
    """

    text = extract_body_text(html)

    assert "Palmer and Rogers have combined" in text
    assert "Manchester City's academy" in text


def test_extract_body_text_filters_byline_and_timestamp_noise():
    html = """
    <main>
        <p>Football Features Writer@nicholaspwright</p>
        <p>Friday 11 September 2026 10:22, UK</p>
        <p>Please use Chrome browser for a more accessible video player</p>
        <p>Rogers was bemused when he found out Palmer was named man of the match against Leeds.</p>
    </main>
    """

    text = extract_body_text(html)

    assert "nicholaspwright" not in text
    assert "10:22" not in text
    assert "Chrome browser" not in text
    assert "man of the match against Leeds" in text


def test_extract_body_text_returns_none_when_live_blog_is_unavailable():
    html = """
    <main>
        <p>Saturday 12 September 2026 08:09, UK</p>
        <p>Sorry, this blog is currently unavailable. Please try again later.</p>
    </main>
    """

    assert extract_body_text(html) is None


def test_extract_body_text_returns_none_when_no_container_found():
    html = "<html><body><div>no article container here</div></body></html>"

    assert extract_body_text(html) is None


def test_extract_body_text_returns_none_when_content_too_short():
    html = "<article><p>Too short.</p></article>"

    assert extract_body_text(html) is None


def test_extract_og_description_returns_meta_tag_content():
    html = '<html><head><meta property="og:description" content="Palmer scores late winner for Chelsea."></head></html>'

    assert extract_og_description(html) == "Palmer scores late winner for Chelsea."


def test_extract_og_description_returns_none_when_tag_missing():
    html = "<html><head></head></html>"

    assert extract_og_description(html) is None


def test_extract_og_description_returns_none_when_content_empty():
    html = '<html><head><meta property="og:description" content="  "></head></html>'

    assert extract_og_description(html) is None


@patch("body_text_extractor.fetch_article_html", return_value=None)
def test_fetch_recovered_content_returns_none_on_request_error(mock_fetch_html):
    assert fetch_recovered_content("https://example.com/article/1") is None


@patch("body_text_extractor.fetch_article_html")
def test_fetch_recovered_content_prefers_body_text_over_og_description(mock_fetch_html):
    html = """
    <html><head><meta property="og:description" content="short social summary"></head>
    <body><article>
        <p>Palmer and Rogers have combined for nine chances this season, more than any other pair.</p>
        <p>Their understanding on the pitch has grown since their time together at Manchester City's academy.</p>
    </article></body></html>
    """
    mock_fetch_html.return_value = html

    result = fetch_recovered_content("https://example.com/article/1")

    assert "Palmer and Rogers have combined" in result


@patch("body_text_extractor.fetch_article_html")
def test_fetch_recovered_content_falls_back_to_og_description_when_body_text_fails(mock_fetch_html):
    html = '<html><head><meta property="og:description" content="Palmer scores late winner for Chelsea."></head><body><div>no article container</div></body></html>'
    mock_fetch_html.return_value = html

    result = fetch_recovered_content("https://example.com/article/1")

    assert result == "Palmer scores late winner for Chelsea."


@patch("body_text_extractor.fetch_article_html")
def test_fetch_recovered_content_returns_none_when_both_fail(mock_fetch_html):
    html = "<html><head></head><body><div>nothing usable here</div></body></html>"
    mock_fetch_html.return_value = html

    assert fetch_recovered_content("https://example.com/article/1") is None


@patch("body_text_extractor.fetch_article_html")
def test_fetch_recovered_content_skips_blocked_domain_without_requesting(mock_fetch_html):
    result = fetch_recovered_content("https://www.empireofthekop.com/2026/09/some-article/")

    assert result is None
    mock_fetch_html.assert_not_called()


@patch("body_text_extractor.fetch_article_html")
def test_recover_content_from_html_reuses_already_fetched_page(mock_fetch_html):
    """db.py처럼 이미 받아온 HTML이 있을 때는 네트워크 요청 없이 그 문자열만으로
    본문/og:description을 복구할 수 있어야 한다(이미지 크롤링과 페이지 접속 공유)."""
    html = '<html><head><meta property="og:description" content="Palmer scores late winner for Chelsea."></head><body><div>no article container</div></body></html>'

    result = recover_content_from_html(html)

    assert result == "Palmer scores late winner for Chelsea."
    mock_fetch_html.assert_not_called()
