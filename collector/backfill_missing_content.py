"""content_original이 빈 기사에 대해 원문 페이지에서 본문 텍스트를 소급 크롤링하는
1회성 배치.

RSS의 <description>이 비어 있던 기사(주로 Sky Sports Football 라이브 블로그)는
content_original도 빈 문자열로 저장돼 있다 — 이 상태로는 translate.py의 가드가
번역 자체를 건너뛴다(할루시네이션 방지, translate.py 참고). 이 스크립트는 그런
기사의 원문 페이지를 직접 요청해 본문을 채워, 다음 번역 배치에서 정상적으로
처리되게 한다.

라이브 블로그 페이지는 원본이 만료되면 서버가 플레이스홀더만 내려줘 크롤링해도
못 채우는 경우가 많다(body_text_extractor.py 참고, 정상적인 실패로 간주) — 이
경우 content_original은 빈 문자열로 그대로 둔다(재실행해도 안전, idempotent).

기사 하나를 처리할 때마다 원문 서버에 요청을 보내므로 다른 배치와 동일하게
BODY_IMAGE_REQUEST_DELAY_SECONDS만큼 지연한다.

사용법:
    python backfill_missing_content.py
"""

import time

from sqlalchemy import text
from sqlalchemy.engine import Engine

import db
from body_text_extractor import fetch_body_text


def backfill_missing_content(engine: Engine) -> tuple:
    """content_original이 빈 기사를 모두 크롤링한다.

    반환값은 (본문을 채운 기사 수, 크롤링해도 못 채운 기사 수)다.
    """
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT id, original_url FROM articles "
                "WHERE content_original IS NULL OR content_original = '' "
                "ORDER BY id"
            )
        ).all()

    total = len(rows)
    filled_count = 0
    still_empty_count = 0

    for index, row in enumerate(rows, start=1):
        body_text = fetch_body_text(row.original_url)

        if body_text:
            with engine.begin() as connection:
                connection.execute(
                    text("UPDATE articles SET content_original = :content WHERE id = :id"),
                    {"content": body_text, "id": row.id},
                )
            filled_count += 1
            print(f"[{index}/{total}] 기사 id={row.id}: 본문 {len(body_text)}자 채움")
        else:
            still_empty_count += 1
            print(f"[{index}/{total}] 기사 id={row.id}: 본문 못 찾음 (라이브 블로그 만료 등)")

        time.sleep(db.BODY_IMAGE_REQUEST_DELAY_SECONDS)

    return filled_count, still_empty_count


def main() -> None:
    engine = db.get_engine()
    filled_count, still_empty_count = backfill_missing_content(engine)

    print(f"본문 소급 크롤링 완료: 채움 {filled_count}건 / 여전히 못 채움 {still_empty_count}건")


if __name__ == "__main__":
    main()
