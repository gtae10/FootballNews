"""기존에 수집된 기사에 카테고리(MATCH/TRANSFER/PLAYER/OTHER) 분류를 소급 적용하는
1회성 배치 스크립트.

save_articles()(db.py)는 신규로 저장되는 기사에만 article_classifier 기반 분류를
적용한다. 이 스크립트 도입 전에 이미 저장돼 있던 기사는 category가 NULL이다 —
retag_articles.py/build_rumor_threads.py와 같은 소급 적용 공백이다.

이 스크립트는 category가 NULL인 기사를 모두 찾아, 이미 rumor_thread_articles에
연결돼 있는지(=이적 건으로 클러스터링된 기사인지)를 조회해 그 결과를 그대로
article_classifier.classify_category()에 넘긴다. category가 이미 채워진 기사는
건드리지 않으므로 여러 번 실행해도 안전하다(idempotent).

사용법:
    python backfill_categories.py
"""

from collections import Counter

from sqlalchemy import text
from sqlalchemy.engine import Engine

import db
from article_classifier import classify_category


def backfill_uncategorized_articles(engine: Engine) -> Counter:
    """category가 NULL인 기사를 모두 분류하고, 카테고리별 건수를 반환한다."""
    counts: Counter = Counter()

    with engine.begin() as connection:
        rows = connection.execute(
            text(
                """
                SELECT a.id, a.title_original, a.content_original
                FROM articles a
                WHERE a.category IS NULL
                """
            )
        ).all()

        for row in rows:
            is_transfer_clustered = (
                connection.execute(
                    text("SELECT 1 FROM rumor_thread_articles WHERE article_id = :id LIMIT 1"),
                    {"id": row.id},
                ).first()
                is not None
            )

            category = classify_category(
                row.title_original, row.content_original, is_transfer_clustered
            )

            connection.execute(
                text("UPDATE articles SET category = :category WHERE id = :id"),
                {"category": category, "id": row.id},
            )
            counts[category] += 1

    return counts


def main() -> None:
    engine = db.get_engine()
    counts = backfill_uncategorized_articles(engine)

    if not counts:
        print("분류할 기사가 없습니다 (모든 기사에 이미 category가 있음).")
        return

    print(f"카테고리 소급 분류 완료: {sum(counts.values())}건")
    for category, count in counts.most_common():
        print(f"  {category}: {count}건")


if __name__ == "__main__":
    main()
