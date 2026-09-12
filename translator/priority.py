"""번역 배치가 COLLECTED 기사를 처리할 순서를 정하는 우선순위 로직.

DAILY_TRANSLATION_LIMIT(하루 처리 상한, translate.py 참고)을 넘긴 기사는 당장
처리되지 않고 COLLECTED 상태 그대로 남아 다음 배치(다음날)로 자연스럽게
이월된다. 어떤 기사를 먼저 처리할지가 그래서 중요하다 — 단순 발행일순으로만
처리하면 하루 안에 여러 매체가 검증한 중요한 속보가 뒤로 밀릴 수 있다.

우선순위(숫자가 작을수록 먼저 처리):
1. `source_tier == 1`(대형/공식 매체)이거나 `quoted_reporter`가 채워져 있는
   기사(신뢰도 높은 기자가 인용됨, 예: Fabrizio Romano)
2. 이적 루머 스레드에 속한 기사 — `independent_source_count`(48시간 이내
   교차 보도한 매체 수, `docs/DB_SCHEMA.md`의 `rumor_threads` 참고) 내림차순
3. 나머지는 `published_at` 최신순
"""

from datetime import datetime, timezone
from typing import List, Protocol


class PrioritizableArticle(Protocol):
    """정렬에 필요한 필드만 명시한 프로토콜 — db.UntranslatedArticle이 이 모양을 만족한다."""

    source_tier: object
    quoted_reporter: object
    independent_source_count: object
    published_at: object


_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _recency_seconds(published_at) -> float:
    """published_at을 정렬 가능한 초 단위 값으로 바꾼다. 없으면 가장 오래된 값(0)으로 취급한다."""
    if published_at is None:
        return 0.0
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    return (published_at - _EPOCH).total_seconds()


def _priority_key(article: PrioritizableArticle):
    is_top_tier = article.source_tier == 1 or bool(article.quoted_reporter)
    has_cross_reports = bool(article.independent_source_count)

    if is_top_tier:
        tier = 0
    elif has_cross_reports:
        tier = 1
    else:
        tier = 2

    # 튜플의 각 항목을 오름차순으로 비교하므로, "클수록 먼저"인 값(교차보도 수,
    # 최신순)은 음수로 뒤집어 넣는다.
    return (
        tier,
        -(article.independent_source_count or 0),
        -_recency_seconds(article.published_at),
    )


def sort_by_priority(articles: List[PrioritizableArticle]) -> List[PrioritizableArticle]:
    """우선순위대로 정렬한 새 리스트를 반환한다 (원본 리스트는 변경하지 않는다)."""
    return sorted(articles, key=_priority_key)
