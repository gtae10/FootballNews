"""RSS 기반 기사 수집 모듈."""

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import feedparser


@dataclass
class CollectedArticle:
    source: str
    original_url: str
    title_original: str
    content_original: str
    published_at: datetime
    forced_club: Optional[str] = None
    source_tier: Optional[int] = None


def collect_from_rss(
    source_name: str,
    rss_url: str,
    forced_club: Optional[str] = None,
    source_tier: Optional[int] = None,
    max_pages: int = 1,
    delay_seconds: float = 0,
) -> List[CollectedArticle]:
    """지정한 RSS 피드에서 기사 목록을 수집한다.

    실제 본문은 요약(summary)만 우선 사용하고,
    상세 본문이 필요하면 별도 크롤링 단계에서 보강한다.
    `forced_club`, `source_tier`는 sources.py에 등록된 값을 그대로 전달받는다.
    `forced_club`은 리버풀 팬 매체처럼 소스 자체가 특정 구단 전용일 때만 채운다 — 나머지는
    None으로 두고, db.py에서 club_matcher.detect_clubs()로 본문에서 구단을 감지해 채운다.

    `max_pages`가 1보다 크면 `?paged=N` 쿼리 파라미터로 과거 페이지까지 순회한다
    (세 소스 모두 워드프레스 계열 `paged` 파라미터를 지원함을 확인했다 — 2026-09 기준).
    평소 주기 실행(scheduler.py)은 기본값 max_pages=1만 사용해 최신 페이지만
    조회하고, 과거 기사 백필은 backfill.py에서 max_pages를 늘려 호출한다.
    `delay_seconds`는 페이지 간 요청 사이의 최소 대기 시간이다(기본 0, 즉 지연 없음).
    """
    articles: List[CollectedArticle] = []

    for page in range(1, max_pages + 1):
        page_url = rss_url if page == 1 else _paged_url(rss_url, page)
        feed = feedparser.parse(page_url)

        if not feed.entries:
            break  # 더 이상 과거 페이지가 없음 (아카이브 끝에 도달)

        for entry in feed.entries:
            published_at = _parse_published(entry)
            articles.append(
                CollectedArticle(
                    source=source_name,
                    original_url=entry.get("link", ""),
                    title_original=entry.get("title", ""),
                    content_original=entry.get("summary", ""),
                    published_at=published_at,
                    forced_club=forced_club,
                    source_tier=source_tier,
                )
            )

        if page < max_pages and delay_seconds > 0:
            time.sleep(delay_seconds)

    return articles


def _paged_url(rss_url: str, page: int) -> str:
    separator = "&" if "?" in rss_url else "?"
    return f"{rss_url}{separator}paged={page}"


def _parse_published(entry) -> datetime:
    # feedparser의 published_parsed는 UTC 기준 struct_time이다. db.py의 나머지
    # datetime 값들과 일관되게 타임존 인식(aware) 값으로 맞추고, Python 3.12+에서
    # 사용 중단된 datetime.utcnow() 대신 datetime.now(timezone.utc)를 사용한다.
    if getattr(entry, "published_parsed", None):
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)
