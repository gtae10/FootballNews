"""기존/신규 기사에 유명 기자·계정 인용 감지를 소급 적용하는 1회성 배치 스크립트.

save_articles()(db.py)는 신규로 저장되는 기사에만 reporter_detector 기반 인용 감지를
적용해 quoted_reporter/source_tier를 채운다. trusted_reporters.py/reporter_detector.py가
도입되기 전에 저장된 기사들은 quoted_reporter가 NULL로 남아 있다 (club_matcher를 신규
소스에 추가할 때 겪었던 것과 같은 소급 적용 공백).

이 스크립트는 quoted_reporter가 비어 있는(NULL) 기사를 모두 찾아 다시 감지를 적용한다.
감지되면 quoted_reporter를 채우고, resolve_source_tier 규칙대로(기존 값보다 신뢰도가
더 높을 때만) source_tier를 갱신한다. 이미 quoted_reporter가 채워진 기사는 건드리지
않으므로 여러 번 실행해도 안전하다(idempotent) — 다만 감지된 사람이 없어 NULL로 남은
기사는 매번 다시 검사한다(club_matcher용 retag_articles.py와 동일한 특성).

사용법:
    python retag_reporters.py
"""

from collections import Counter

from sqlalchemy import text
from sqlalchemy.engine import Engine

import db
from reporter_detector import detect_quoted_reporter, resolve_source_tier


def retag_reporters(engine: Engine) -> Counter:
    """quoted_reporter가 NULL인 기사를 찾아 재감지하고, 기자별 감지 건수를 반환한다."""
    counts: Counter = Counter()

    with engine.begin() as connection:
        rows = connection.execute(
            text(
                """
                SELECT id, title_original, content_original, source_tier
                FROM articles
                WHERE quoted_reporter IS NULL
                """
            )
        ).all()

        for row in rows:
            detected = detect_quoted_reporter(row.title_original, row.content_original)
            if detected is None:
                continue

            new_tier = resolve_source_tier(row.source_tier, detected)
            connection.execute(
                text(
                    "UPDATE articles SET quoted_reporter = :name, source_tier = :tier WHERE id = :id"
                ),
                {"name": detected["name"], "tier": new_tier, "id": row.id},
            )
            counts[detected["name"]] += 1

    return counts


def main() -> None:
    engine = db.get_engine()
    counts = retag_reporters(engine)

    if not counts:
        print("감지된 인용이 없습니다.")
        return

    print("기자/계정 인용 감지 결과:")
    for name, count in counts.most_common():
        print(f"  {name}: {count}건")


if __name__ == "__main__":
    main()
