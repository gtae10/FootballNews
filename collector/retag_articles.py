"""기존에 수집된 기사에 구단 자동 태깅을 소급 적용하는 1회성 배치 스크립트.

save_articles()(db.py)는 신규로 저장되는 기사에만 club_matcher 기반 구단 태깅을
적용한다. 이 스크립트가 실행되기 전 수집된 기사들은 article_clubs에 태깅이 전혀
없다 — docs/DB_SCHEMA.md의 "마이그레이션 메모"에 남아 있듯, 리버풀 단일 구단 앱이던
시절의 스키마(articles.club 단일 컬럼)에서 다중 구단 태깅 구조(article_clubs)로
옮겨오면서 기존 데이터를 새 구조로 옮기는 마이그레이션이 실제 DB에는 아직 적용되지
못했기 때문이다.

이 스크립트는 article_clubs에 태깅이 하나도 없는 기사를 모두 찾아, save_articles()와
동일한 규칙(제목+본문 매칭 + 소스별 forced_club)으로 재태깅한다. 이미 태그가 있는
기사는 건드리지 않으므로 여러 번 실행해도 안전하다(idempotent).

사용법:
    python retag_articles.py
"""

import argparse
from collections import Counter

from sqlalchemy import text
from sqlalchemy.engine import Engine

import db
from club_matcher import build_alias_map, detect_clubs, fetch_clubs_from_db
from sources import RSS_SOURCES

UNTAGGED_LABEL = "(태깅 안 됨)"

# save_articles()가 신규 기사에 적용하는 규칙과 동일하게, 소스 자체가 특정 구단
# 전용인 경우(sources.py의 forced_club) 본문 감지 결과와 무관하게 항상 태깅한다.
SOURCE_FORCED_CLUB = {
    source["name"]: source["forced_club"]
    for source in RSS_SOURCES
    if source.get("forced_club")
}


def retag_untagged_articles(engine: Engine, alias_map: dict) -> Counter:
    """article_clubs에 row가 하나도 없는 기사를 찾아 재태깅하고, 구단별 태깅 건수를 반환한다."""
    counts: Counter = Counter()

    with engine.begin() as connection:
        rows = connection.execute(
            text(
                """
                SELECT a.id, a.source, a.title_original, a.content_original
                FROM articles a
                LEFT JOIN article_clubs ac ON ac.article_id = a.id
                WHERE ac.article_id IS NULL
                """
            )
        ).all()

        for row in rows:
            detected = set(
                detect_clubs(f"{row.title_original}\n{row.content_original}", alias_map)
            )
            forced_club = SOURCE_FORCED_CLUB.get(row.source)
            if forced_club:
                detected.add(forced_club)

            for club_name in sorted(detected):
                connection.execute(
                    text(
                        "INSERT INTO article_clubs (article_id, club_name) VALUES (:article_id, :club_name)"
                    ),
                    {"article_id": row.id, "club_name": club_name},
                )
                counts[club_name] += 1

            if not detected:
                counts[UNTAGGED_LABEL] += 1

    return counts


def retag_all_articles_for_new_aliases(engine: Engine, alias_map: dict) -> Counter:
    """club_matcher.ALIAS_OVERRIDES에 별칭이 새로 추가된 뒤, 이미 태그가 있는 기사를
    포함한 전체 기사를 다시 검사해 새로 인식되는 구단을 추가로 태깅한다.

    retag_untagged_articles()는 태그가 하나도 없는 기사만 보므로, 이미 다른 구단으로
    태깅된 기사에 새 별칭으로만 인식되는 구단이 하나 더 있어도 놓친다(예: "Roma,
    Betis, Fenerbahce" 기사가 이미 AS Roma로 태깅돼 있으면 "Betis" 별칭을 나중에
    추가해도 그 기사를 다시 보지 않음). 이 함수는 기사별 기존 태그를 먼저 확인해
    거기 없는 것만 추가하므로 중복 삽입 없이 여러 번 실행해도 안전하다(idempotent).
    """
    counts: Counter = Counter()

    with engine.begin() as connection:
        rows = connection.execute(
            text("SELECT id, source, title_original, content_original FROM articles")
        ).all()

        for row in rows:
            detected = set(
                detect_clubs(f"{row.title_original}\n{row.content_original}", alias_map)
            )
            forced_club = SOURCE_FORCED_CLUB.get(row.source)
            if forced_club:
                detected.add(forced_club)

            if not detected:
                continue

            existing = {
                existing_row.club_name
                for existing_row in connection.execute(
                    text("SELECT club_name FROM article_clubs WHERE article_id = :id"),
                    {"id": row.id},
                ).all()
            }

            for club_name in sorted(detected - existing):
                connection.execute(
                    text(
                        "INSERT INTO article_clubs (article_id, club_name) VALUES (:article_id, :club_name)"
                    ),
                    {"article_id": row.id, "club_name": club_name},
                )
                counts[club_name] += 1

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="구단 자동 태깅을 기존 기사에 소급 적용한다."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="이미 태그가 있는 기사도 포함해 전체 기사를 다시 검사한다 "
        "(club_matcher에 별칭을 새로 추가한 뒤 사용). 기본값은 태그가 하나도 없는 기사만 처리한다.",
    )
    args = parser.parse_args()

    engine = db.get_engine()
    alias_map = build_alias_map(fetch_clubs_from_db(engine))

    if args.all:
        counts = retag_all_articles_for_new_aliases(engine, alias_map)
    else:
        counts = retag_untagged_articles(engine, alias_map)

    if not counts:
        print("재태깅할 기사가 없습니다 (모든 기사에 이미 태그가 있음).")
        return

    print("재태깅 결과:")
    for club_name, count in counts.most_common():
        print(f"  {club_name}: {count}건")


if __name__ == "__main__":
    main()
