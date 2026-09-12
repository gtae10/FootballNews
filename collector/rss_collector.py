"""RSS 기반 기사 수집 모듈."""

import html
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import feedparser

_IMG_TAG_SRC = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)


@dataclass
class CollectedArticle:
    source: str
    original_url: str
    title_original: str
    content_original: str
    published_at: datetime
    forced_club: Optional[str] = None
    source_tier: Optional[int] = None
    image_url: Optional[str] = None


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
                    # 일부 워드프레스 계열 RSS(예: "&#8217;")는 HTML 엔티티가 이중 인코딩돼
                    # 있어 feedparser의 기본 파싱만으로는 안 풀린다 — 실제 DB에서 제목에
                    # "&#8217;"가 그대로 노출되는 것으로 확인됨. html.unescape()로 한 번 더 푼다.
                    title_original=html.unescape(entry.get("title", "")),
                    content_original=html.unescape(entry.get("summary", "")),
                    published_at=published_at,
                    forced_club=forced_club,
                    source_tier=source_tier,
                    image_url=_extract_image_url(entry),
                )
            )

        if page < max_pages and delay_seconds > 0:
            time.sleep(delay_seconds)

    return articles


def _paged_url(rss_url: str, page: int) -> str:
    separator = "&" if "?" in rss_url else "?"
    return f"{rss_url}{separator}paged={page}"


def _extract_image_url(entry) -> Optional[str]:
    """RSS 엔트리에서 대표 이미지 URL을 찾는다. 이미지 자체는 절대 다운로드/재호스핑하지
    않고 URL만 반환한다 — 저작권 문제를 피하기 위해 프론트엔드가 원본 서버에서 직접
    이미지를 불러온다 (docs/LEGAL_NOTES.md 참고).

    소스마다 이미지를 싣는 방식이 달라 여러 경로를 순서대로 시도한다:
    media:thumbnail → media:content(이미지 타입) → enclosure(이미지 타입) →
    본문(summary) HTML에 박힌 첫 <img> 태그. 어디에도 없으면 None을 반환하며,
    이 경우 프론트는 텍스트만으로 정상 표시한다(이미지 영역 자체를 렌더링하지 않음).
    """
    thumbnails = getattr(entry, "media_thumbnail", None)
    if thumbnails:
        url = thumbnails[0].get("url")
        if url:
            return url

    for media in getattr(entry, "media_content", None) or []:
        medium = media.get("medium")
        media_type = media.get("type") or ""
        if medium == "image" or media_type.startswith("image"):
            url = media.get("url")
            if url:
                return url

    for enclosure in getattr(entry, "enclosures", None) or []:
        enclosure_type = enclosure.get("type") or ""
        if enclosure_type.startswith("image"):
            url = enclosure.get("href") or enclosure.get("url")
            if url:
                return url

    summary = entry.get("summary", "")
    match = _IMG_TAG_SRC.search(summary)
    if match:
        return match.group(1)

    return None


def _parse_published(entry) -> datetime:
    # feedparser의 published_parsed는 UTC 기준 struct_time이다. db.py의 나머지
    # datetime 값들과 일관되게 타임존 인식(aware) 값으로 맞추고, Python 3.12+에서
    # 사용 중단된 datetime.utcnow() 대신 datetime.now(timezone.utc)를 사용한다.
    if getattr(entry, "published_parsed", None):
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)
