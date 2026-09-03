"""RSS가 없는 사이트를 위한 크롤링 모듈."""

from dataclasses import dataclass
from datetime import datetime
from typing import List

import requests
from bs4 import BeautifulSoup


@dataclass
class CrawledArticle:
    source: str
    original_url: str
    title_original: str
    content_original: str


def crawl_article_list(source_name: str, list_url: str, article_selector: str) -> List[str]:
    """기사 목록 페이지에서 개별 기사 URL 목록을 추출한다."""
    response = requests.get(list_url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.select(article_selector)
    return [link.get("href") for link in links if link.get("href")]


def crawl_article_detail(source_name: str, article_url: str) -> CrawledArticle:
    """개별 기사 페이지에서 제목/본문을 추출한다.

    실제 셀렉터는 매체별로 다르므로, 소스별 설정을 sources.py에서 관리하고
    이 함수에서 분기 처리하도록 확장이 필요하다.
    """
    response = requests.get(article_url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.string if soup.title else ""

    return CrawledArticle(
        source=source_name,
        original_url=article_url,
        title_original=title or "",
        content_original="",  # TODO: 매체별 본문 셀렉터 적용
    )
