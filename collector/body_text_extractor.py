"""RSS summary가 비어 있는 기사의 본문 텍스트를 원문 페이지에서 대신 추출하는 모듈.

RSS의 <description>이 빈 문자열인 기사(주로 Sky Sports Football의 라이브 블로그)는
content_original도 비어서 저장된다. 빈 본문을 그대로 번역기에 넘기면 LLM이 제목만
보고 요약을 지어내는(할루시네이션) 문제가 실제로 발견됐다(translate.py 가드 참고).
이 모듈은 그 공백을 메우기 위해 원문 기사 페이지를 직접 요청해 본문 텍스트를
추출한다 — body_image_extractor.py와 동일한 본문 컨테이너 셀렉터를 재사용한다.

라이브 블로그 페이지는 콘텐츠가 만료되면 서버가 "Sorry, this blog is currently
unavailable." 플레이스홀더만 내려준다(JS 렌더링 문제가 아니라 원본 자체가 더 이상
제공되지 않음, 실제 확인함) — 이 경우 추출 실패로 처리한다. 일반 뉴스 기사
페이지는 <main>/<article> 안에 실제 본문 문단이 있어 추출이 가능하다.
"""

import re
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from body_image_extractor import _BODY_SELECTORS

REQUEST_TIMEOUT_SECONDS = 10
MIN_TEXT_LENGTH = 80

# 개별 기사 페이지 직접 크롤링이 이용약관상 금지된 도메인 (RSS 피드 자체는 계속 사용).
# empireofthekop.com: robots.txt가 링크하는 라이선스 계약(m4ow.uk/socw/2.txt)이 검색
# 인덱싱 외 목적의 스크래핑/AI 학습/임베딩 생성/데이터셋 구축을 전면 금지한다(2026-09-13
# 확인, sources.py에서 Football Italia/CaughtOffside를 제외시킨 것과 동일한 계약).
_FALLBACK_CRAWL_BLOCKED_DOMAINS = ("empireofthekop.com",)


def _is_fallback_crawl_blocked(article_url: str) -> bool:
    host = urlparse(article_url).netloc.lower()
    return any(host == domain or host.endswith("." + domain) for domain in _FALLBACK_CRAWL_BLOCKED_DOMAINS)

# 본문이 아니라 바이라인(기자명+SNS 핸들)/타임스탬프/영상 플레이어 안내처럼
# 사이트 공통 UI에서 반복되는 문단을 걸러낸다. 완벽하지 않을 수 있다.
_NOISE_PATTERNS = re.compile(
    r"(^[A-Za-z ]+Writer@\w+$|^@\w+$|^Please use Chrome browser|"
    r"^\w+day \d{1,2} \w+ \d{4} \d{2}:\d{2},?\s*(UK)?$)",
    re.IGNORECASE,
)

# 라이브 블로그가 만료되면 원문 서버가 실제 본문 대신 이 문구만 내려준다
# (JS 렌더링 문제가 아니라 원본 자체가 더 이상 제공되지 않음, 실제 확인함).
_UNAVAILABLE_MARKER = "currently unavailable"


def extract_body_text(html: str) -> Optional[str]:
    """본문 HTML에서 문단 텍스트를 추출한다. 못 찾거나 내용이 부실하면 None을 반환한다."""
    soup = BeautifulSoup(html, "html.parser")

    container = None
    for selector in _BODY_SELECTORS:
        container = soup.select_one(selector)
        if container:
            break
    if container is None:
        return None

    paragraphs = []
    for p in container.find_all("p"):
        text = p.get_text(strip=True)
        if not text or _NOISE_PATTERNS.search(text):
            continue
        paragraphs.append(text)

    body_text = "\n\n".join(paragraphs)
    if len(body_text) < MIN_TEXT_LENGTH or _UNAVAILABLE_MARKER in body_text.lower():
        return None

    return body_text


def extract_og_description(html: str) -> Optional[str]:
    """<meta property="og:description">의 내용을 대체 요약으로 추출한다.

    본문 크롤링(extract_body_text)도 실패했을 때 마지막으로 시도하는 수단이다.
    소셜 공유용으로 작성된 짧은 요약이라 본문만큼 상세하지 않을 수 있지만,
    RSS summary도 본문 크롤링도 실패한 경우엔 완전한 공백보다 낫다.
    """
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("meta", attrs={"property": "og:description"})
    if not tag:
        return None

    content = (tag.get("content") or "").strip()
    return content or None


def fetch_recovered_content(article_url: str) -> Optional[str]:
    """RSS summary가 비어 있거나 너무 짧은 기사의 본문을 원문 페이지에서 복구한다.

    페이지를 한 번만 요청해 본문 텍스트(extract_body_text) → 실패하면
    og:description(extract_og_description) 순으로 시도한다. 요청 자체가
    실패하거나(네트워크 오류, 타임아웃, 4xx/5xx) 둘 다 못 찾으면 None을
    반환한다 — 호출부(collector/db.py)가 이 경우 기사를 아예 저장하지 않고
    건너뛴다(번역도 안 되고 보여줄 내용도 없는 죽은 데이터를 만들지 않기 위함).

    이용약관상 개별 기사 페이지 크롤링이 금지된 도메인(_FALLBACK_CRAWL_BLOCKED_DOMAINS)은
    요청 자체를 보내지 않고 바로 None을 반환한다.
    """
    if _is_fallback_crawl_blocked(article_url):
        return None

    try:
        response = requests.get(article_url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException:
        return None

    body_text = extract_body_text(response.text)
    if body_text:
        return body_text

    return extract_og_description(response.text)
