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

from bs4 import BeautifulSoup

from body_image_extractor import _BODY_SELECTORS, fetch_article_html

MIN_TEXT_LENGTH = 80

# db.py의 save_articles()와 backfill_missing_content.py가 공유하는 "본문이 번역/
# 게시에 쓸 만큼 충분히 확보됐는가" 기준. 예전엔 backfill_missing_content.py에만
# 지역 상수로 있었는데, 저장 시점 검증도 같은 기준을 써야 해서 여기로 옮겼다.
MIN_CONTENT_LENGTH = 20

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


def recover_content_from_html(html: str) -> Optional[str]:
    """이미 받아온 페이지 HTML에서 본문(extract_body_text) → 실패하면
    og:description(extract_og_description) 순으로 복구를 시도한다.

    네트워크 요청은 하지 않는다 — 이미지 추출(body_image_extractor.py)과 페이지
    접속을 공유하는 호출부(db.py)가 이미 받아온 HTML을 그대로 넘길 때 쓴다.
    """
    body_text = extract_body_text(html)
    if body_text:
        return body_text

    return extract_og_description(html)


def fetch_recovered_content(article_url: str) -> Optional[str]:
    """RSS summary가 비어 있거나 너무 짧은 기사의 본문을 원문 페이지에서 복구한다.

    페이지를 한 번만 요청해 본문 텍스트 → 실패하면 og:description 순으로
    시도한다(recover_content_from_html). 요청 자체가 실패하거나(네트워크 오류,
    타임아웃, 4xx/5xx) 둘 다 못 찾으면 None을 반환한다 — 호출부가 이 경우 기사를
    아예 저장하지 않고 건너뛴다(번역도 안 되고 보여줄 내용도 없는 죽은 데이터를
    만들지 않기 위함).

    이용약관상 개별 기사 페이지 크롤링이 금지된 도메인(_FALLBACK_CRAWL_BLOCKED_DOMAINS)은
    요청 자체를 보내지 않고 바로 None을 반환한다.
    """
    if _is_fallback_crawl_blocked(article_url):
        return None

    html = fetch_article_html(article_url)
    if html is None:
        return None

    return recover_content_from_html(html)
