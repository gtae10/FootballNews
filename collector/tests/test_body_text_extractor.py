from unittest.mock import patch

import requests

from body_text_extractor import extract_body_text, fetch_body_text


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


@patch("body_text_extractor.requests.get")
def test_fetch_body_text_returns_none_on_request_error(mock_get):
    mock_get.side_effect = requests.RequestException("network error")

    assert fetch_body_text("https://example.com/article/1") is None
