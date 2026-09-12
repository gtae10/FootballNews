"""기존에 저장된 기사의 title_original/content_original에 남아있는 이중 인코딩된
HTML 엔티티("&#8217;" 등)를 정리하는 1회성 배치.

일부 워드프레스 계열 RSS는 엔티티가 이중 인코딩돼 있어 feedparser의 기본 파싱만으로는
풀리지 않는다 — 화면에 글자 대신 "&#8217;" 같은 엔티티 코드가 그대로 노출되는 것으로
실제 확인됨. rss_collector.py는 이제 신규 수집 시점에 html.unescape()를 적용하도록
수정됐지만(collect_from_rss 참고), 이 수정 이전에 이미 저장된 기사는 그대로 남아있다.

html.unescape()는 이미 깨끗한 텍스트에 적용해도 대부분 그대로 반환하므로(엔티티가
없으면 변경 없음), 바뀐 값이 있는 기사만 업데이트한다 — 여러 번 실행해도 안전하다
(idempotent).

사용법:
    python backfill_unescape_titles.py
"""

import html

from sqlalchemy import text
from sqlalchemy.engine import Engine

import db


def backfill_unescape_titles(engine: Engine) -> int:
    """title_original/content_original에 html.unescape()를 적용해 바뀐 기사 수를 반환한다."""
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT id, title_original, content_original FROM articles")
        ).all()

    updated_count = 0
    with engine.begin() as connection:
        for row in rows:
            new_title = html.unescape(row.title_original or "")
            new_content = html.unescape(row.content_original or "")

            if new_title == row.title_original and new_content == row.content_original:
                continue

            connection.execute(
                text(
                    "UPDATE articles SET title_original = :title, content_original = :content "
                    "WHERE id = :id"
                ),
                {"title": new_title, "content": new_content, "id": row.id},
            )
            updated_count += 1

    return updated_count


def main() -> None:
    engine = db.get_engine()
    updated_count = backfill_unescape_titles(engine)
    print(f"HTML 엔티티 정리 완료: {updated_count}건 수정")


if __name__ == "__main__":
    main()
