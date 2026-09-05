from html_cleanup import clean_for_translation


def test_strips_html_tags():
    assert clean_for_translation("<p>Hello <b>world</b></p>") == "Hello world"


def test_decodes_html_entities():
    # &#8217;는 직선 아포스트로피(')가 아니라 둥근 작은따옴표(U+2019)로 디코딩된다.
    assert clean_for_translation("Liverpool&#8217;s squad") == "Liverpool’s squad"


def test_removes_wordpress_footer():
    raw = (
        "<p>Real content here.</p>\n"
        '<p>The post <a href="https://example.com/a">Title</a> appeared first on '
        '<a href="https://example.com">Site Name</a>.</p>'
    )

    assert clean_for_translation(raw) == "Real content here."


def test_collapses_whitespace():
    assert clean_for_translation("Hello\n\n   world") == "Hello world"


def test_leaves_plain_text_without_html_unchanged():
    assert clean_for_translation("Plain text, no HTML.") == "Plain text, no HTML."


def test_does_not_corrupt_urls_inside_removed_tags():
    raw = '<p>See <a href="https://example.com/here-we-go-transfer-news">this link</a> for details.</p>'

    result = clean_for_translation(raw)

    assert "See" in result
    assert "this link" in result
    assert "https://" not in result  # 링크 텍스트만 남고 URL 자체는 태그와 함께 제거된다
