"""주기적으로 뉴스 수집을 실행하는 스케줄러."""

from apscheduler.schedulers.blocking import BlockingScheduler

import db
from rss_collector import collect_from_rss
from sources import RSS_SOURCES, CRAWL_SOURCES


def run_collection_job():
    all_articles = []

    for source in RSS_SOURCES:
        articles = collect_from_rss(
            source["name"],
            source["rss_url"],
            forced_club=source.get("forced_club"),
            source_tier=source.get("source_tier"),
        )
        all_articles.extend(articles)

    # CRAWL_SOURCES는 현재 등록된 소스가 없다 (sources.py 참고).
    # 크롤링 대상이 추가되면 crawler.crawl_article_list/crawl_article_detail을
    # 사용해 같은 방식으로 all_articles에 합류시킨다.
    if CRAWL_SOURCES:
        print(f"CRAWL_SOURCES 처리 로직이 아직 없습니다: {len(CRAWL_SOURCES)}개 소스 건너뜀")

    engine = db.get_engine()
    saved_count = db.save_articles(engine, all_articles)

    print(f"수집된 기사 수: {len(all_articles)}, 신규 저장: {saved_count}")
    return all_articles


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(run_collection_job, "interval", minutes=30)

    print("수집 스케줄러 시작 (30분 간격)")
    run_collection_job()  # 시작 시 1회 즉시 실행
    scheduler.start()
