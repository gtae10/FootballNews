"""backend와 동일한 DB 스키마를 사용해 미번역 기사를 조회하고 번역 결과를 저장하는 모듈.

연결 정보는 환경 변수로만 주입하며, 비밀번호를 코드에 하드코딩하지 않는다.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# .env가 있으면 그 값을 os.environ에 채워 넣는다
# (TRANSLATOR_DB_URL, ANTHROPIC_API_KEY, OPENAI_API_KEY 등).
# translate.py가 이 모듈을 최상단에서 import하므로 여기서 한 번만 로드하면 된다.
# 파일이 없으면 조용히 아무 일도 하지 않고, get_engine()의 DEFAULT_DB_URL 폴백이
# 그대로 사용된다. 이미 설정된 실제 환경 변수는 덮어쓰지 않는다.
load_dotenv()

DEFAULT_DB_URL = "mysql+pymysql://root:password@localhost:3306/liverpool_news"


@dataclass
class UntranslatedArticle:
    id: int
    title_original: str
    content_original: str
    # 우선순위 큐(priority.py)가 정렬에 쓰는 메타데이터. 기존 호출부와의 호환을
    # 위해 전부 기본값을 둔다(위치 인자 3개만 넘기던 기존 코드/테스트도 그대로 동작).
    source_tier: Optional[int] = None
    quoted_reporter: Optional[str] = None
    independent_source_count: Optional[int] = None
    published_at: Optional[datetime] = None


def get_engine() -> Engine:
    """환경 변수 TRANSLATOR_DB_URL로 DB 연결 엔진을 생성한다.

    설정하지 않으면 backend/docker-compose.yml의 로컬 개발용 기본값과 동일한
    주소를 사용한다 (프로덕션에서는 반드시 TRANSLATOR_DB_URL을 지정해야 한다).
    """
    db_url = os.environ.get("TRANSLATOR_DB_URL", DEFAULT_DB_URL)
    return create_engine(db_url, pool_pre_ping=True)


def fetch_untranslated_articles(engine: Engine) -> List[UntranslatedArticle]:
    """status가 COLLECTED인(아직 번역되지 않은) 기사 목록을, 우선순위 정렬(priority.py)에
    필요한 메타데이터와 함께 조회한다.

    rumor_thread_articles/rumor_threads를 LEFT JOIN해 각 기사가 속한 이적 루머
    스레드의 independent_source_count(교차 보도한 매체 수)를 함께 가져온다 —
    스레드에 속하지 않은 기사는 NULL이 된다. 한 기사가 여러 스레드에 걸치는 건
    현재 구조상 없지만(collector 쪽에서 기사당 스레드 하나로 묶음), 혹시 모를
    경우를 대비해 MAX로 안전하게 하나만 남긴다.
    """
    with engine.begin() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    a.id, a.title_original, a.content_original,
                    a.source_tier, a.quoted_reporter, a.published_at,
                    MAX(rt.independent_source_count) AS independent_source_count
                FROM articles a
                LEFT JOIN rumor_thread_articles rta ON rta.article_id = a.id
                LEFT JOIN rumor_threads rt ON rt.id = rta.rumor_thread_id
                WHERE a.status = 'COLLECTED'
                GROUP BY a.id, a.title_original, a.content_original,
                         a.source_tier, a.quoted_reporter, a.published_at
                """
            )
        ).all()

    return [
        UntranslatedArticle(
            id=row.id,
            title_original=row.title_original,
            content_original=row.content_original,
            source_tier=row.source_tier,
            quoted_reporter=row.quoted_reporter,
            independent_source_count=row.independent_source_count,
            published_at=row.published_at,
        )
        for row in rows
    ]


def count_translated_today(engine: Engine) -> int:
    """오늘(UTC 자정 기준) 이미 번역 완료된 기사 수를 반환한다.

    DAILY_TRANSLATION_LIMIT은 프로세스 한 번의 배치가 아니라 "하루 전체" 기준이다.
    scheduler.py가 30분마다 translate.py를 새 프로세스로 실행하므로 프로세스 간에
    공유되는 메모리 상태가 없다 — 그래서 이번 실행에서 얼마나 더 처리할 수
    있는지는 오늘 이미 처리한 건수를 DB에서 다시 세어 판단한다. `CURDATE()` 같은
    DB 방언 전용 함수 대신 Python에서 계산한 UTC 자정 경계로 비교해 MySQL/SQLite
    양쪽에서 동일하게 동작한다(테스트는 SQLite in-memory DB를 쓴다).
    """
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    tomorrow_start = today_start + timedelta(days=1)

    with engine.begin() as connection:
        count = connection.execute(
            text(
                "SELECT COUNT(*) FROM translations "
                "WHERE translated_at >= :start AND translated_at < :end"
            ),
            {"start": today_start, "end": tomorrow_start},
        ).scalar()
    return count or 0


def save_translation(engine: Engine, article_id: int, result: Any) -> None:
    """translations 테이블에 번역 결과를 저장하고 articles.status를 TRANSLATED로 갱신한다.

    `result`는 translate.TranslationResult(title_ko, content_ko, model_version)이다.
    (순환 import를 피하기 위해 타입을 직접 import하지 않는다.)
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO translations
                    (article_id, title_ko, content_ko, model_version, translated_at)
                VALUES
                    (:article_id, :title_ko, :content_ko, :model_version, :translated_at)
                """
            ),
            {
                "article_id": article_id,
                "title_ko": result.title_ko,
                "content_ko": result.content_ko,
                "model_version": result.model_version,
                "translated_at": datetime.now(timezone.utc),
            },
        )
        connection.execute(
            text("UPDATE articles SET status = 'TRANSLATED' WHERE id = :id"),
            {"id": article_id},
        )
