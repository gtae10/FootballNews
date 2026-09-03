"""과거 기사 백필 실행 스크립트.

scheduler.py의 평소 주기 실행(run_collection_job)은 각 RSS 피드의 최신 페이지만
조회한다. 이 스크립트는 그와 분리된 1회성 실행으로, 세 RSS 소스가 모두 지원하는
`?paged=N` 파라미터를 이용해 과거 페이지까지 순회하며 기사를 수집한다.

평소 스케줄러는 이 로직을 전혀 거치지 않으므로, 30분 간격 주기 실행이 매번
아카이브까지 훑는 일은 없다. 실행 시간이 길고 소스별 요청 수도 많으므로
직접 필요할 때만(예: 신규 소스 추가 직후 과거 데이터 확보) 수동 실행한다.

사용법:
    python backfill.py                # 기본 5페이지씩 백필
    python backfill.py --pages 10     # 소스당 10페이지까지 백필
"""

import argparse
import time

import db
from rss_collector import collect_from_rss
from sources import RSS_SOURCES

DEFAULT_BACKFILL_PAGES = 5

# 소스/페이지 요청 사이 최소 지연 시간(초). 짧은 시간에 과도한 요청을 보내지
# 않기 위한 것으로, RSS_SOURCES 세 곳 모두 robots.txt에서 일반 크롤링을
# 허용하지만(2026-09 확인, docs/LEGAL_NOTES.md 참고) 예의상 최소한의 간격을 둔다.
REQUEST_DELAY_SECONDS = 1.5


def run_backfill(max_pages: int = DEFAULT_BACKFILL_PAGES) -> int:
    all_articles = []

    for index, source in enumerate(RSS_SOURCES):
        articles = collect_from_rss(
            source["name"],
            source["rss_url"],
            forced_club=source.get("forced_club"),
            source_tier=source.get("source_tier"),
            max_pages=max_pages,
            delay_seconds=REQUEST_DELAY_SECONDS,
        )
        print(f"{source['name']}: {len(articles)}건 수집 (최대 {max_pages}페이지)")
        all_articles.extend(articles)

        is_last_source = index == len(RSS_SOURCES) - 1
        if not is_last_source:
            time.sleep(REQUEST_DELAY_SECONDS)

    engine = db.get_engine()
    saved_count = db.save_articles(engine, all_articles)

    print(f"백필 수집 기사 수(중복 포함): {len(all_articles)}, 신규 저장: {saved_count}")
    return saved_count


def main() -> None:
    parser = argparse.ArgumentParser(description="RSS 아카이브 페이지를 순회해 과거 기사를 백필한다.")
    parser.add_argument(
        "--pages",
        type=int,
        default=DEFAULT_BACKFILL_PAGES,
        help=f"소스당 순회할 페이지 수 (기본값 {DEFAULT_BACKFILL_PAGES})",
    )
    args = parser.parse_args()

    if args.pages < 1:
        raise SystemExit("--pages는 1 이상이어야 합니다.")

    run_backfill(max_pages=args.pages)


if __name__ == "__main__":
    main()
