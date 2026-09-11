"""기존에 수집된 기사에 본문 이미지(article_images)를 소급 크롤링하는 1회성 배치.

save_articles()(db.py)는 신규로 저장되는 기사에만 body_image_extractor 기반 본문
이미지 크롤링을 적용한다. 이 기능 도입 전에 이미 저장돼 있던 기사는 article_images에
아무 row도 없다 — retag_articles.py/backfill_categories.py와 같은 소급 적용 공백이다.

article_images에 이미 row가 있는 기사는 건드리지 않으므로 여러 번 실행해도 안전하다
(idempotent). 다만 "크롤링을 시도했지만 이미지를 못 찾음"과 "아직 시도하지 않음"을
구분하지 못한다는 한계가 있다(둘 다 row 0개) — 재실행하면 못 찾았던 기사도 다시
크롤링을 시도한다(소스에 반복 요청을 보내게 되므로 필요할 때만 실행한다).

기사 하나를 처리할 때마다 원문 서버에 요청을 보내므로 db.py와 동일하게
BODY_IMAGE_REQUEST_DELAY_SECONDS만큼 지연한다. 기사 하나가 끝날 때마다 즉시
커밋하므로, 중간에 중단해도 이미 처리한 기사의 결과는 남는다(재실행 시 자동으로
이어서 처리됨).

사용법:
    python backfill_article_images.py
    python backfill_article_images.py --limit 50   # 앞 50건만 처리(테스트용)
"""

import argparse
import time

from sqlalchemy import text
from sqlalchemy.engine import Engine

import db
from body_image_extractor import fetch_body_images


def backfill_article_images(engine: Engine, limit: int = None) -> tuple:
    """article_images에 row가 없는 기사를 모두 크롤링한다.

    반환값은 (이미지를 하나 이상 찾아 저장한 기사 수, 크롤링을 시도했지만 이미지를
    하나도 못 찾은 기사 수)다.
    """
    query = """
        SELECT a.id, a.original_url, a.image_url
        FROM articles a
        LEFT JOIN article_images ai ON ai.article_id = a.id
        WHERE ai.article_id IS NULL
        ORDER BY a.id
    """
    params = {}
    if limit:
        query += " LIMIT :limit"
        params["limit"] = limit

    with engine.connect() as connection:
        rows = connection.execute(text(query), params).all()

    total = len(rows)
    found_count = 0
    empty_count = 0

    for index, row in enumerate(rows, start=1):
        body_images = fetch_body_images(row.original_url, exclude_url=row.image_url)

        with engine.begin() as connection:
            for position, image_url in enumerate(body_images):
                connection.execute(
                    text(
                        """
                        INSERT INTO article_images (article_id, position, image_url)
                        VALUES (:article_id, :position, :image_url)
                        """
                    ),
                    {"article_id": row.id, "position": position, "image_url": image_url},
                )

        if body_images:
            found_count += 1
        else:
            empty_count += 1

        print(f"[{index}/{total}] 기사 id={row.id}: 이미지 {len(body_images)}개")
        time.sleep(db.BODY_IMAGE_REQUEST_DELAY_SECONDS)

    return found_count, empty_count


def main() -> None:
    parser = argparse.ArgumentParser(description="기존 기사에 본문 이미지를 소급 크롤링한다.")
    parser.add_argument("--limit", type=int, default=None, help="처리할 최대 기사 수 (기본값: 전체)")
    args = parser.parse_args()

    engine = db.get_engine()
    found_count, empty_count = backfill_article_images(engine, limit=args.limit)

    print(f"본문 이미지 소급 크롤링 완료: 이미지 찾음 {found_count}건 / 못 찾음 {empty_count}건")


if __name__ == "__main__":
    main()
