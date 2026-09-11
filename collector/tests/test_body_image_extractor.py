from unittest.mock import MagicMock, patch

import requests

from body_image_extractor import extract_body_images, fetch_body_images


def test_extract_body_images_finds_images_inside_article_tag():
    html = """
    <html><body>
        <header><img src="https://example.com/logo.png"></header>
        <article>
            <p>본문 시작</p>
            <img src="https://example.com/photo1.jpg">
            <p>본문 계속</p>
            <img src="https://example.com/photo2.jpg">
        </article>
    </body></html>
    """

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"]


def test_extract_body_images_falls_back_to_other_selectors_when_no_article_tag():
    html = """
    <html><body>
        <div class="entry-content">
            <img src="https://example.com/photo1.jpg">
        </div>
    </body></html>
    """

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://example.com/photo1.jpg"]


def test_extract_body_images_resolves_relative_urls_to_absolute():
    html = '<article><img src="/images/photo.jpg"></article>'

    urls = extract_body_images(html, base_url="https://example.com/sport/article/1")

    assert urls == ["https://example.com/images/photo.jpg"]


def test_extract_body_images_uses_data_src_when_src_missing():
    html = '<article><img data-src="https://example.com/lazy.jpg"></article>'

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://example.com/lazy.jpg"]


def test_extract_body_images_uses_data_src_when_src_is_a_lazy_load_placeholder():
    """지연 로딩 플러그인은 실제 로드 전까지 src에 1x1 투명 GIF 같은 data: URI
    플레이스홀더를 넣어두고 실제 이미지는 data-src에 담아둔다(theanfieldwrap.com에서
    실제로 발견된 패턴)."""
    html = (
        '<article><img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAA'
        'AAABAAEAAAICTAEAOw==" data-src="https://example.com/real-photo.jpg"></article>'
    )

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://example.com/real-photo.jpg"]


def test_extract_body_images_excludes_ad_and_share_and_logo_images_by_url():
    html = """
    <article>
        <img src="https://example.com/photo1.jpg">
        <img src="https://ads.example.com/ad-banner.jpg">
        <img src="https://example.com/share-icon.png">
        <img src="https://example.com/site-logo.png">
        <img src="https://example.com/tracking-pixel.gif">
    </article>
    """

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://example.com/photo1.jpg"]


def test_extract_body_images_excludes_theme_bundled_badge_and_sponsor_images():
    """planetfootball.com 실제 기사에서 본문 영역 안에 "Google 뉴스 선호 소스" 배지
    이미지(사이트 테마 번들 자산, /content/themes/ 경로)가 섞여 나와 실제 기사 사진을
    밀어내는 문제가 실제로 발견됐다."""
    html = """
    <article>
        <img src="https://example.com/content/themes/site/img/preferred_source_badge_dark.png">
        <img src="https://example.com/content/themes/site/img/preferred_source_badge_light.png">
        <img src="https://cdn.example.com/uploads/2026/09/real-photo-1200x675.jpg">
    </article>
    """

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://cdn.example.com/uploads/2026/09/real-photo-1200x675.jpg"]


def test_extract_body_images_excludes_small_club_crest_icons_by_badges_path():
    """Sky Sports/Football365류 사이트는 팀 엠블럼 아이콘을 /football/badges/ 경로의
    CDN에 담아둔다(예: e0.365dm.com/football/badges/96/608.png) — 실제 기사 사진이
    아니라 작은 배지 아이콘이므로 제외한다."""
    html = """
    <article>
        <img src="https://e0.365dm.com/football/badges/96/608.png">
        <img src="https://cdn.example.com/uploads/2026/09/real-photo.jpg">
    </article>
    """

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://cdn.example.com/uploads/2026/09/real-photo.jpg"]


def test_extract_body_images_does_not_exclude_legitimate_photos_with_badge_in_filename():
    """"badge"라는 단어 자체로는 거르지 않는다 — Football365는 "F365-One-Badge-..."
    처럼 합성 편집 사진 파일명에 badge가 들어가는 경우가 있는데, 이는 실제 기사용
    이미지이지 테마 자산이나 배지 아이콘이 아니다."""
    html = """
    <article>
        <img src="https://cdn.example.com/uploads/2026/09/F365-One-Badge-Bruno-Fernandes.jpg">
    </article>
    """

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://cdn.example.com/uploads/2026/09/F365-One-Badge-Bruno-Fernandes.jpg"]


def test_extract_body_images_excludes_images_inside_promotional_strapline_widget():
    """Sky Sports 실제 기사에서 WhatsApp 팔로우 유도/Super 6 배팅 홍보 이미지가
    <article> 태그 안의 `sdc-article-strapline` 위젯 div 안에 들어 있어, img 태그
    자신의 class/src만으로는 걸러지지 않는 사례가 실제로 발견됐다 — 조상 요소의
    클래스명까지 봐야 한다."""
    html = """
    <article>
        <p>본문</p>
        <div class="sdc-article-widget sdc-article-strapline">
            <picture><img src="https://example.com/whatsapp-cta.jpg"></picture>
        </div>
        <img src="https://example.com/real-photo.jpg">
    </article>
    """

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://example.com/real-photo.jpg"]


def test_extract_body_images_excludes_images_inside_related_articles_tile_grid():
    """Sky Sports 하단 "관련 기사 더 보기" 추천 그리드(`sdc-site-tile`)도 <article>
    태그 범위 안에 포함돼 있어 같은 방식으로 걸러야 한다."""
    html = """
    <article>
        <img src="https://example.com/real-photo.jpg">
        <div class="sdc-site-tile" data-testid="sitewide-tiles-item">
            <img src="https://example.com/related-article-thumb.jpg">
        </div>
    </article>
    """

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://example.com/real-photo.jpg"]


def test_extract_body_images_excludes_gambling_compliance_banner_by_filename():
    """football365.com 실제 기사에서 gambleaware.org로 링크되는 도박 책임 고지
    배너(Please-Gamble-Responsibly.jpg)가 본문 안에 그대로 삽입돼 있어 실제로
    발견됐다."""
    html = """
    <article>
        <img src="https://example.com/real-photo.jpg">
        <a href="https://www.gambleaware.org/"><img src="https://example.com/Please-Gamble-Responsibly.jpg" width="1600" height="200"></a>
    </article>
    """

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://example.com/real-photo.jpg"]


def test_extract_body_images_excludes_wide_banner_strip_by_aspect_ratio():
    html = """
    <article>
        <img src="https://example.com/real-photo.jpg" width="1200" height="675">
        <img src="https://example.com/some-banner.jpg" width="1600" height="200">
    </article>
    """

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://example.com/real-photo.jpg"]


def test_extract_body_images_excludes_small_square_icon_by_size():
    html = """
    <article>
        <img src="https://example.com/real-photo.jpg" width="1200" height="675">
        <img src="https://example.com/small-icon.jpg" width="120" height="120">
    </article>
    """

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://example.com/real-photo.jpg"]


def test_extract_body_images_keeps_images_without_width_or_height_attributes():
    """width/height 속성이 없으면(CSS로만 크기가 정해지는 경우가 흔함) 정보 부족을
    이유로 보수적으로 포함시킨다."""
    html = '<article><img src="https://example.com/real-photo.jpg"></article>'

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://example.com/real-photo.jpg"]


def test_extract_body_images_excludes_images_by_class_name():
    html = """
    <article>
        <img src="https://example.com/photo1.jpg" class="hero-image">
        <img src="https://example.com/photo2.jpg" class="author-avatar">
    </article>
    """

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://example.com/photo1.jpg"]


def test_extract_body_images_excludes_thumbnail_already_used_as_representative_image():
    html = """
    <article>
        <img src="https://example.com/thumb.jpg">
        <img src="https://example.com/photo2.jpg">
    </article>
    """

    urls = extract_body_images(
        html, base_url="https://example.com/article/1", exclude_url="https://example.com/thumb.jpg"
    )

    assert urls == ["https://example.com/photo2.jpg"]


def test_extract_body_images_deduplicates_repeated_images():
    html = """
    <article>
        <img src="https://example.com/photo1.jpg">
        <img src="https://example.com/photo1.jpg">
    </article>
    """

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == ["https://example.com/photo1.jpg"]


def test_extract_body_images_caps_at_max_images_per_article():
    imgs = "".join(f'<img src="https://example.com/photo{i}.jpg">' for i in range(10))
    html = f"<article>{imgs}</article>"

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert len(urls) == 5


def test_extract_body_images_returns_empty_list_when_no_images_found():
    html = "<article><p>이미지가 없는 본문입니다.</p></article>"

    urls = extract_body_images(html, base_url="https://example.com/article/1")

    assert urls == []


@patch("body_image_extractor.requests.get")
def test_fetch_body_images_returns_extracted_urls_on_success(mock_get):
    mock_response = MagicMock()
    mock_response.text = '<article><img src="https://example.com/photo1.jpg"></article>'
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    urls = fetch_body_images("https://example.com/article/1")

    assert urls == ["https://example.com/photo1.jpg"]
    mock_get.assert_called_once()


@patch("body_image_extractor.requests.get")
def test_fetch_body_images_returns_empty_list_on_network_error(mock_get):
    mock_get.side_effect = requests.ConnectionError("연결 실패")

    urls = fetch_body_images("https://example.com/article/1")

    assert urls == []


@patch("body_image_extractor.requests.get")
def test_fetch_body_images_returns_empty_list_on_http_error_status(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("404")
    mock_get.return_value = mock_response

    urls = fetch_body_images("https://example.com/article/1")

    assert urls == []


@patch("body_image_extractor.requests.get")
def test_fetch_body_images_returns_empty_list_on_timeout(mock_get):
    mock_get.side_effect = requests.Timeout("타임아웃")

    urls = fetch_body_images("https://example.com/article/1")

    assert urls == []
