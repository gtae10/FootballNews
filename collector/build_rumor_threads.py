"""기존에 수집된 기사에 루머 스레드 클러스터링을 소급 적용하는 1회성 배치 스크립트.

save_articles()(db.py)는 신규로 저장되는 기사에만 rumor_clusterer 기반 클러스터링을
적용한다. 이 스크립트 도입 전에 이미 저장돼 있던 기사는 rumor_thread_articles에
연결이 전혀 없다 — retag_articles.py/retag_reporters.py와 같은 소급 적용 공백이다.

이 스크립트는 rumor_thread_articles에 연결이 없는 기사를 발행일 오름차순으로 모두
찾아 클러스터링을 적용한다. 발행일 순서대로 처리해야 "먼저 보도한 스레드에 나중
기사가 합류"하는 타임라인이 실제 보도 순서와 일치한다. 이미 스레드에 연결된 기사는
건드리지 않으므로 여러 번 실행해도 안전하다(idempotent) — 다만 구단 태그나 선수명
후보가 없어 스레드를 만들 수 없었던 기사는(club_matcher용 retag_articles.py와
동일한 특성으로) 매번 다시 검사한다.

사용법:
    python build_rumor_threads.py
"""

from collections import Counter

from sqlalchemy import text
from sqlalchemy.engine import Engine

import db
from club_matcher import build_alias_map, fetch_clubs_from_db
from player_extractor import build_excluded_names, extract_player_candidates
from rumor_clusterer import cluster_article, detect_story_stage
from trusted_reporters import TRUSTED_REPORTERS


def _reporter_aliases():
    aliases = []
    for reporter in TRUSTED_REPORTERS:
        aliases.extend(reporter["aliases"])
    return aliases


def build_threads_for_unclustered(engine: Engine, excluded_names: set) -> Counter:
    """rumor_thread_articles에 연결이 없는 기사를 발행일순으로 클러스터링한다.

    반환값은 (선수명, 구단) 조합별로 새로 연결된 기사 수 카운터다.
    """
    counts: Counter = Counter()

    with engine.begin() as connection:
        rows = connection.execute(
            text(
                """
                SELECT a.id, a.title_original, a.content_original, a.published_at
                FROM articles a
                LEFT JOIN rumor_thread_articles rta ON rta.article_id = a.id
                WHERE rta.article_id IS NULL
                ORDER BY a.published_at ASC
                """
            )
        ).all()

        for row in rows:
            clubs = [
                club_row.club_name
                for club_row in connection.execute(
                    text("SELECT club_name FROM article_clubs WHERE article_id = :id"),
                    {"id": row.id},
                ).all()
            ]
            if not clubs:
                continue

            # story_stage가 UNKNOWN이면(이적 관련 키워드가 전혀 없으면) 클러스터링 대상에서
            # 제외한다 — db.py의 save_articles()와 동일한 규칙 (경기 리포트 등 이적과 무관한
            # 기사가 "같은 선수+구단 언급"만으로 루머 스레드에 섞이는 것을 막는다).
            stage = detect_story_stage(row.title_original, row.content_original)
            if stage == "UNKNOWN":
                continue

            candidates = extract_player_candidates(row.title_original, excluded_names)
            if not candidates:
                continue

            cluster_article(connection, row.id, row.published_at, candidates, clubs, stage)

            for player_name in candidates:
                for club_name in clubs:
                    counts[f"{player_name} → {club_name}"] += 1

    return counts


def main() -> None:
    engine = db.get_engine()
    alias_map = build_alias_map(fetch_clubs_from_db(engine))
    excluded_names = build_excluded_names(alias_map, _reporter_aliases())

    counts = build_threads_for_unclustered(engine, excluded_names)

    if not counts:
        print("클러스터링할 기사가 없습니다 (모두 처리됐거나, 구단 태그/선수명 후보가 없음).")
        return

    print(f"루머 스레드 소급 클러스터링 완료: {sum(counts.values())}건 연결")
    for label, count in counts.most_common(10):
        print(f"  {label}: {count}건")


if __name__ == "__main__":
    main()
