"""content_original이 비어 있거나 너무 짧은 기존 기사를 정리하는 1회성 배치.

RSS의 <description>이 비어 있던 기사(주로 Sky Sports Football 라이브 블로그)는
content_original도 짧게(또는 빈 문자열로) 저장돼 있다 — 이 상태로는 번역이
영원히 실패하고(translate.py의 빈 본문 가드), 사용자에게 보여줄 내용도 없다.

db.py의 save_articles()는 이제 저장 시점에 같은 로직(MIN_CONTENT_LENGTH 미만이면
본문 크롤링 → og:description 순으로 복구 시도, 그래도 실패하면 저장 자체를
건너뜀)을 적용하므로 앞으로 새로 이런 기사가 쌓이지 않는다. 이 스크립트는 그
로직이 도입되기 전에 이미 저장돼 있던 기존 오염 데이터를 정리하는 용도다 —
복구할 수 있는 건 복구하고, 그래도 못 살리면 삭제한다(article_clubs/
article_images/rumor_thread_articles/translations 등 연결된 데이터도 함께
지워 고아 레코드를 남기지 않는다).

기사 하나를 처리할 때마다 원문 서버에 요청을 보내므로 다른 배치와 동일하게
BODY_IMAGE_REQUEST_DELAY_SECONDS만큼 지연한다.

사용법:
    python backfill_missing_content.py
"""

import time
from collections import Counter

from sqlalchemy import text
from sqlalchemy.engine import Engine

import db
from body_text_extractor import MIN_CONTENT_LENGTH, fetch_recovered_content


def find_short_content_articles(engine: Engine) -> list:
    """content_original이 비어 있거나 MIN_CONTENT_LENGTH 미만인 기사를 찾는다."""
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT id, source, original_url, LENGTH(content_original) AS content_length "
                "FROM articles "
                "WHERE content_original IS NULL OR LENGTH(content_original) < :min_length "
                "ORDER BY id"
            ),
            {"min_length": MIN_CONTENT_LENGTH},
        ).all()
    return list(rows)


def _delete_article_and_related_rows(connection, article_id: int) -> None:
    """기사와 연결된 모든 데이터(article_clubs/article_images/rumor_thread_articles/
    translations)를 함께 지운다 — 고아 레코드를 남기지 않는다. 기사가 마지막
    연결이었던 rumor_thread가 비면 그 스레드도 함께 지운다.
    """
    thread_ids = [
        row.rumor_thread_id
        for row in connection.execute(
            text("SELECT rumor_thread_id FROM rumor_thread_articles WHERE article_id = :id"),
            {"id": article_id},
        ).all()
    ]

    connection.execute(text("DELETE FROM article_clubs WHERE article_id = :id"), {"id": article_id})
    connection.execute(text("DELETE FROM article_images WHERE article_id = :id"), {"id": article_id})
    connection.execute(
        text("DELETE FROM rumor_thread_articles WHERE article_id = :id"), {"id": article_id}
    )
    connection.execute(text("DELETE FROM translations WHERE article_id = :id"), {"id": article_id})
    connection.execute(text("DELETE FROM articles WHERE id = :id"), {"id": article_id})

    for thread_id in thread_ids:
        remaining = connection.execute(
            text("SELECT COUNT(*) FROM rumor_thread_articles WHERE rumor_thread_id = :id"),
            {"id": thread_id},
        ).scalar()
        if remaining == 0:
            connection.execute(text("DELETE FROM rumor_threads WHERE id = :id"), {"id": thread_id})


def cleanup_short_content_articles(engine: Engine) -> tuple:
    """본문이 없거나 너무 짧은 기사를 복구를 시도하고, 실패하면 삭제한다.

    반환값은 (복구한 기사 수, 삭제한 기사 수, 소스별 삭제 건수 Counter)다.
    """
    rows = find_short_content_articles(engine)
    total = len(rows)
    recovered_count = 0
    deleted_count = 0
    deleted_by_source: Counter = Counter()

    for index, row in enumerate(rows, start=1):
        recovered = fetch_recovered_content(row.original_url)

        if recovered and len(recovered.strip()) >= MIN_CONTENT_LENGTH:
            with engine.begin() as connection:
                connection.execute(
                    text("UPDATE articles SET content_original = :content WHERE id = :id"),
                    {"content": recovered, "id": row.id},
                )
            recovered_count += 1
            print(f"[{index}/{total}] 기사 id={row.id}: 본문 {len(recovered)}자로 복구")
        else:
            with engine.begin() as connection:
                _delete_article_and_related_rows(connection, row.id)
            deleted_count += 1
            deleted_by_source[row.source] += 1
            print(f"[{index}/{total}] 기사 id={row.id} ({row.source}): 복구 실패, 삭제함 — {row.original_url}")

        time.sleep(db.BODY_IMAGE_REQUEST_DELAY_SECONDS)

    return recovered_count, deleted_count, deleted_by_source


def main() -> None:
    engine = db.get_engine()
    rows = find_short_content_articles(engine)

    print(f"본문이 비어있거나 {MIN_CONTENT_LENGTH}자 미만인 기사 {len(rows)}건 발견")
    if not rows:
        return

    recovered_count, deleted_count, deleted_by_source = cleanup_short_content_articles(engine)

    print(f"\n정리 완료: 복구 {recovered_count}건 / 삭제 {deleted_count}건")
    if deleted_by_source:
        print("삭제된 기사의 소스별 분포:")
        for source, count in deleted_by_source.most_common():
            print(f"  {source}: {count}건")


if __name__ == "__main__":
    main()
