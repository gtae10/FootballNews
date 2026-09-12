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

import requests
from bs4 import BeautifulSoup

from body_image_extractor import _BODY_SELECTORS

REQUEST_TIMEOUT_SECONDS = 10
MIN_TEXT_LENGTH = 80

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


def fetch_body_text(article_url: str) -> Optional[str]:
    """기사 원문 페이지를 요청해 본문 텍스트를 추출한다.

    실패하면(네트워크 오류, 타임아웃, 4xx/5xx, 본문을 못 찾음) None을 반환한다.
    """
    try:
        response = requests.get(article_url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException:
        return None

    return extract_body_text(response.text)
