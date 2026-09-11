"""기사 본문 페이지에서 이미지 URL을 추가로 추출하는 모듈.

RSS는 대표 이미지(썸네일) 하나만 제공하는 경우가 대부분이라(rss_collector.py의
_extract_image_url), 상세 페이지에 이미지를 더 보여주려면 원문 기사 페이지를 직접
요청해 본문 영역 안의 이미지를 추가로 찾아야 한다.

매체마다 HTML 구조가 달라 완벽한 정확도를 보장할 수 없다 — 뉴스 사이트에서 널리
쓰이는 본문 컨테이너 셀렉터를 우선순위대로 시도하는 휴리스틱 방식이다. 광고/공유
버튼/아바타/로고처럼 본문과 무관한 이미지는 클래스명·파일명 패턴으로 걸러내지만
완벽하지 않을 수 있다. 이미지 파일 자체는 절대 다운로드/재호스팅하지 않고 URL만
추출한다(썸네일과 동일한 저작권 원칙, docs/LEGAL_NOTES.md 참고).

크롤링이 실패하거나(네트워크 오류, 타임아웃, 4xx/5xx) 본문 컨테이너를 못 찾으면
빈 리스트를 반환한다 — 호출부(db.py)가 이 경우 기존 썸네일(image_url) 하나만
유지하는 폴백으로 자연스럽게 이어지게 하기 위함이다.
"""

import re
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT_SECONDS = 10
MAX_IMAGES_PER_ARTICLE = 5

# 뉴스 사이트에서 널리 쓰이는 본문 컨테이너 셀렉터를 우선순위대로 시도한다.
# 어느 것도 못 찾으면 문서 전체(soup)를 그대로 쓴다 — 이 경우 오탐(광고 등)
# 가능성이 커지므로, 아래 _EXCLUDE_PATTERNS로 최대한 걸러낸다.
_BODY_SELECTORS = [
    "article",
    '[itemprop="articleBody"]',
    ".article-body",
    ".entry-content",
    ".post-content",
    ".article__content",
    "main",
]

# 광고/공유버튼/아바타/로고/추적 픽셀처럼 본문과 무관한 이미지를 클래스명·URL
# 패턴으로 제외한다. 매체마다 명명 규칙이 달라 완벽하지 않을 수 있다.
# "/themes/"·"/theme/" 경로는 워드프레스 등에서 테마(템플릿) 번들에 포함된
# 정적 자산 경로로, 실제로는 기사 본문이 아니라 "Google 뉴스 선호 소스" 배지처럼
# 사이트 전역에 반복되는 UI 요소인 경우가 많다(planetfootball.com/football365.com/
# teamtalk.com 세 곳 모두에서 실제로 preferred_source_badge_*.png가 본문 영역 안에서
# 발견된 사례로 확인됨 — 셋 다 같은 테마를 쓰는 것으로 보인다). "/badges/" 경로는
# Sky Sports/Football365류 사이트가 팀 엠블럼 아이콘을 담아두는 CDN 경로다(예:
# e0.365dm.com/football/badges/96/608.png) — 실제 기사 사진이 아니라 작은 팀 배지
# 아이콘이라 제외한다. 바로 "badge"라는 단어 자체는 쓰지 않는다 — F365 등은
# "F365-One-Badge-Bruno-Fernandes..."처럼 합성 사진 파일명에 badge가 들어가는
# 경우가 있어(실제 기사 이미지), 경로가 아닌 단어 하나로 걸렀다면 이런 정상적인
# 기사 이미지까지 오탐으로 걸러졌을 것이다. "gambl"은 football365.com 실제 기사
# 본문에 삽입된 도박 책임 고지 배너(gambleaware.org로 링크되는
# Please-Gamble-Responsibly.jpg, 1600x200 가로 스트립 이미지)를 제외하기 위함이다.
_EXCLUDE_PATTERNS = re.compile(
    r"(avatar|logo|icon|sprite|pixel|tracking|share|social|advert|\bad[-_]|banner|"
    r"placeholder|emoji|sponsor|gambl|/badges?/|/themes?/)",
    re.IGNORECASE,
)

# img 태그 자신이 아니라 조상 요소(picture/div/figure 등)에 실려 있는 클래스명/
# data-component-name으로 판별해야 하는 경우 — "관련 기사"/"더 보기" 추천 위젯,
# 뉴스레터·SNS 팔로우 유도 스트랩라인처럼 기사 본문 컨테이너 안에 얹혀 있지만
# 실제로는 본문이 아닌 사이트 전역 위젯이다. Sky Sports 실제 기사에서
# `sdc-article-strapline`(WhatsApp 팔로우 유도, Super 6 배팅 홍보 이미지)와
# `sdc-site-tile`/`sitewide-tiles`(하단 "관련 기사 더 보기" 추천 그리드)가 각각
# <article> 태그 안에 포함돼 있어 img 자체의 src/class만으로는 걸러지지 않는
# 사례로 확인됨 — 조상 최대 6단계까지 올라가며 검사한다.
_EXCLUDE_ANCESTOR_PATTERN = re.compile(
    r"(widget|strapline|sitewide|site-tile|related|recommend|promo|newsletter|advert)",
    re.IGNORECASE,
)
_ANCESTOR_SEARCH_DEPTH = 6


def _is_excluded_by_ancestor(img) -> bool:
    for parent in img.find_parents(limit=_ANCESTOR_SEARCH_DEPTH):
        class_attr = " ".join(parent.get("class") or [])
        component_name = parent.get("data-component-name") or ""
        if _EXCLUDE_ANCESTOR_PATTERN.search(class_attr) or _EXCLUDE_ANCESTOR_PATTERN.search(component_name):
            return True
    return False


# 실제 편집 사진(선수/경기 등)은 거의 항상 16:9~4:3 근처의 가로 사진 비율이다.
# 배너 광고(가로로 아주 긴 띠 모양, 예: football365.com의 1600x200 도박 책임 고지
# 배너)나 작은 정사각형 아이콘/배지(150px 이하)는 이름·경로 패턴을 몰라도 이
# 크기 비율만으로 상당수 걸러낼 수 있다. width/height 속성이 아예 없는 img는
# (CSS로만 크기가 정해지는 경우가 흔해서) 그냥 통과시킨다 — 정보가 없을 때
# 보수적으로 포함하는 쪽을 택한다.
_MIN_DIMENSION_PX = 150
_MAX_ASPECT_RATIO = 4.0


def _is_excluded_by_size(img) -> bool:
    width = _parse_positive_int(img.get("width"))
    height = _parse_positive_int(img.get("height"))
    if not width or not height:
        return False
    if width <= _MIN_DIMENSION_PX or height <= _MIN_DIMENSION_PX:
        return True
    ratio = width / height
    return ratio >= _MAX_ASPECT_RATIO or ratio <= 1 / _MAX_ASPECT_RATIO


def _parse_positive_int(value) -> Optional[int]:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def extract_body_images(html: str, base_url: str, exclude_url: Optional[str] = None) -> List[str]:
    """본문 HTML에서 이미지 URL 목록을 추출한다 (최대 MAX_IMAGES_PER_ARTICLE개, 중복 제거).

    `exclude_url`을 지정하면(보통 이미 썸네일로 저장된 image_url) 결과에서
    제외해 같은 이미지가 두 번 노출되지 않게 한다.
    """
    soup = BeautifulSoup(html, "html.parser")

    container = None
    for selector in _BODY_SELECTORS:
        container = soup.select_one(selector)
        if container:
            break
    if container is None:
        container = soup

    urls: List[str] = []
    for img in container.find_all("img"):
        src = img.get("src")
        # 지연 로딩(lazy-load) 플러그인은 실제 이미지가 로드되기 전까지 src에 1x1
        # 투명 GIF 같은 data: URI 플레이스홀더를 넣어두고 실제 URL은 data-src/
        # data-lazy-src에 담아둔다. src가 없거나 이런 플레이스홀더면 그쪽을 대신
        # 쓴다 — 그렇지 않으면 플레이스홀더 자체가 "이미지"로 추출된다(실제로
        # theanfieldwrap.com 기사에서 이 문제가 발견됨).
        if not src or src.startswith("data:"):
            src = img.get("data-src") or img.get("data-lazy-src")
        if not src:
            continue

        class_attr = " ".join(img.get("class") or [])
        if _EXCLUDE_PATTERNS.search(src) or _EXCLUDE_PATTERNS.search(class_attr):
            continue
        if _is_excluded_by_ancestor(img):
            continue
        if _is_excluded_by_size(img):
            continue

        absolute_url = urljoin(base_url, src)
        if exclude_url and absolute_url == exclude_url:
            continue
        if absolute_url in urls:
            continue

        urls.append(absolute_url)
        if len(urls) >= MAX_IMAGES_PER_ARTICLE:
            break

    return urls


def fetch_body_images(article_url: str, exclude_url: Optional[str] = None) -> List[str]:
    """기사 원문 페이지를 요청해 본문 이미지 URL을 추출한다.

    실패하면(네트워크 오류, 타임아웃, 4xx/5xx) 예외를 던지지 않고 빈 리스트를
    반환한다 — 호출부가 실패 여부를 분기 처리할 필요 없이 항상 "리스트"를
    받아 기존 썸네일 폴백으로 자연스럽게 이어지게 하기 위함이다.
    """
    try:
        response = requests.get(article_url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException:
        return []

    return extract_body_images(response.text, article_url, exclude_url=exclude_url)
