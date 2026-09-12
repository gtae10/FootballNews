from datetime import datetime, timedelta, timezone

from db import UntranslatedArticle
from priority import sort_by_priority


def _article(id, **overrides):
    defaults = dict(id=id, title_original=f"title-{id}", content_original="content")
    defaults.update(overrides)
    return UntranslatedArticle(**defaults)


def test_top_tier_source_is_processed_before_ordinary_articles():
    """source_tier=1은 최우선이다. tier 2/3 사이에는 별도 우선순위가 없으므로
    (요청 사양에 없음) 둘 다 "나머지" 구간으로 취급돼 published_at으로만 갈린다."""
    tier1 = _article(1, source_tier=1)
    ordinary = _article(2, source_tier=3)

    result = sort_by_priority([ordinary, tier1])

    assert [a.id for a in result] == [1, 2]


def test_quoted_trusted_reporter_counts_as_top_tier_even_without_tier1_source():
    quoted = _article(1, source_tier=2, quoted_reporter="Fabrizio Romano")
    ordinary = _article(2, source_tier=2)

    result = sort_by_priority([ordinary, quoted])

    assert [a.id for a in result] == [1, 2]


def test_cross_verified_rumor_thread_articles_come_before_uncross_verified():
    verified = _article(1, independent_source_count=3)
    unverified = _article(2, independent_source_count=None)

    result = sort_by_priority([unverified, verified])

    assert [a.id for a in result] == [1, 2]


def test_cross_verified_articles_sort_by_independent_source_count_descending():
    two_sources = _article(1, independent_source_count=2)
    four_sources = _article(2, independent_source_count=4)
    three_sources = _article(3, independent_source_count=3)

    result = sort_by_priority([two_sources, four_sources, three_sources])

    assert [a.id for a in result] == [2, 3, 1]


def test_remaining_articles_sort_by_published_at_most_recent_first():
    now = datetime.now(timezone.utc)
    oldest = _article(1, published_at=now - timedelta(days=2))
    newest = _article(2, published_at=now)
    middle = _article(3, published_at=now - timedelta(days=1))

    result = sort_by_priority([oldest, middle, newest])

    assert [a.id for a in result] == [2, 3, 1]


def test_top_tier_beats_cross_verified_which_beats_plain_recency():
    tier1 = _article(1, source_tier=1)
    cross_verified = _article(2, independent_source_count=5)
    recent_but_plain = _article(3, published_at=datetime.now(timezone.utc))

    result = sort_by_priority([recent_but_plain, cross_verified, tier1])

    assert [a.id for a in result] == [1, 2, 3]


def test_sort_by_priority_does_not_mutate_input_list():
    articles = [_article(2, source_tier=2), _article(1, source_tier=1)]
    original_order = list(articles)

    sort_by_priority(articles)

    assert articles == original_order
