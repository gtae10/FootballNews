"""backend와 동일한 DB 스키마를 사용해 미번역 기사를 조회하고 번역 결과를 저장하는 모듈.

연결 정보는 환경 변수로만 주입하며, 비밀번호를 코드에 하드코딩하지 않는다.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List

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


def get_engine() -> Engine:
    """환경 변수 TRANSLATOR_DB_URL로 DB 연결 엔진을 생성한다.

    설정하지 않으면 backend/docker-compose.yml의 로컬 개발용 기본값과 동일한
    주소를 사용한다 (프로덕션에서는 반드시 TRANSLATOR_DB_URL을 지정해야 한다).
    """
    db_url = os.environ.get("TRANSLATOR_DB_URL", DEFAULT_DB_URL)
    return create_engine(db_url, pool_pre_ping=True)


def fetch_untranslated_articles(engine: Engine) -> List[UntranslatedArticle]:
    """status가 COLLECTED인(아직 번역되지 않은) 기사 목록을 조회한다."""
    with engine.begin() as connection:
        rows = connection.execute(
            text(
                "SELECT id, title_original, content_original "
                "FROM articles WHERE status = 'COLLECTED'"
            )
        ).all()

    return [
        UntranslatedArticle(
            id=row.id,
            title_original=row.title_original,
            content_original=row.content_original,
        )
        for row in rows
    ]


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
