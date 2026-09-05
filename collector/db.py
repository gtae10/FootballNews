"""수집된 기사 원문을 DB(articles 테이블)에 저장하는 모듈.

backend(Spring Boot)와 동일한 스키마(`docs/DB_SCHEMA.md` 참고)를 사용한다.
연결 정보는 환경 변수로만 주입하며, 비밀번호를 코드에 하드코딩하지 않는다.
"""

import os
from datetime import datetime, timezone
from typing import Iterable

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from club_matcher import build_alias_map, detect_clubs, fetch_clubs
from player_extractor import build_excluded_names, extract_player_candidates
from reporter_detector import detect_quoted_reporter, resolve_source_tier
from rss_collector import CollectedArticle
from rumor_clusterer import cluster_article, detect_story_stage
from trusted_reporters import TRUSTED_REPORTERS

# .env가 있으면 그 값을 os.environ에 채워 넣는다. 파일이 없으면 조용히 아무 일도
# 하지 않고, get_engine()의 DEFAULT_DB_URL 폴백이 그대로 사용된다. 이미 설정된
# 실제 환경 변수(예: CI에서 export한 값)는 덮어쓰지 않는다.
load_dotenv()

DEFAULT_DB_URL = "mysql+pymysql://root:password@localhost:3306/liverpool_news"


def get_engine() -> Engine:
    """환경 변수 COLLECTOR_DB_URL로 DB 연결 엔진을 생성한다.

    설정하지 않으면 backend/docker-compose.yml의 로컬 개발용 기본값과 동일한
    주소를 사용한다 (프로덕션에서는 반드시 COLLECTOR_DB_URL을 지정해야 한다).
    """
    db_url = os.environ.get("COLLECTOR_DB_URL", DEFAULT_DB_URL)
    return create_engine(db_url, pool_pre_ping=True)


def _load_alias_map() -> dict:
    """백엔드 GET /clubs를 한 번 호출해 구단 별칭 맵을 만든다.

    백엔드가 떠 있지 않거나 호출에 실패하면(collector가 백엔드보다 먼저 실행되는 경우 등)
    빈 맵을 반환한다 — 이 경우 본문 기반 구단 감지는 건너뛰고 소스별 forced_club만 적용된다.
    """
    try:
        return build_alias_map(fetch_clubs())
    except Exception as error:  # noqa: BLE001 - 백엔드 연결 실패는 수집 자체를 막지 않는다
        print(f"GET /clubs 호출 실패 — 구단 자동 태깅을 건너뜁니다: {error}")
        return {}


def _reporter_aliases() -> list:
    aliases = []
    for reporter in TRUSTED_REPORTERS:
        aliases.extend(reporter["aliases"])
    return aliases


def save_articles(engine: Engine, articles: Iterable[CollectedArticle]) -> int:
    """수집된 기사 중 원문 URL이 아직 없는 기사만 저장한다.

    반환값은 새로 저장된 기사 수다. 이미 저장된 기사(original_url 중복)는 건너뛴다.
    """
    alias_map = _load_alias_map()
    excluded_names = build_excluded_names(alias_map, _reporter_aliases())
    saved = 0
    with engine.begin() as connection:
        for article in articles:
            already_exists = connection.execute(
                text("SELECT 1 FROM articles WHERE original_url = :url"),
                {"url": article.original_url},
            ).first()
            if already_exists:
                continue

            detected_reporter = detect_quoted_reporter(article.title_original, article.content_original)
            quoted_reporter = detected_reporter["name"] if detected_reporter else None
            effective_source_tier = resolve_source_tier(article.source_tier, detected_reporter)

            detected_clubs = set(
                detect_clubs(f"{article.title_original}\n{article.content_original}", alias_map)
            )
            if article.forced_club:
                detected_clubs.add(article.forced_club)

            result = connection.execute(
                text(
                    """
                    INSERT INTO articles
                        (source, original_url, title_original, content_original,
                         published_at, collected_at, status, source_tier, quoted_reporter, image_url)
                    VALUES
                        (:source, :original_url, :title_original, :content_original,
                         :published_at, :collected_at, 'COLLECTED', :source_tier, :quoted_reporter, :image_url)
                    """
                ),
                {
                    "source": article.source,
                    "original_url": article.original_url,
                    "title_original": article.title_original,
                    "content_original": article.content_original,
                    "published_at": article.published_at,
                    "collected_at": datetime.now(timezone.utc),
                    "source_tier": effective_source_tier,
                    "quoted_reporter": quoted_reporter,
                    "image_url": article.image_url,
                },
            )
            article_id = result.lastrowid

            for club_name in detected_clubs:
                connection.execute(
                    text(
                        "INSERT INTO article_clubs (article_id, club_name) VALUES (:article_id, :club_name)"
                    ),
                    {"article_id": article_id, "club_name": club_name},
                )

            # story_stage가 UNKNOWN이면(이적 관련 키워드가 전혀 없으면) 클러스터링하지 않는다.
            # 그렇지 않으면 경기 리포트처럼 이적과 무관한 기사도 "같은 선수+구단 언급"이라는
            # 이유만으로 루머 스레드에 섞여 들어가 교차검증으로 오인될 수 있다.
            if detected_clubs:
                story_stage = detect_story_stage(article.title_original, article.content_original)
                if story_stage != "UNKNOWN":
                    player_candidates = extract_player_candidates(article.title_original, excluded_names)
                    if player_candidates:
                        cluster_article(
                            connection, article_id, article.published_at,
                            player_candidates, detected_clubs, story_stage,
                        )

            saved += 1

    return saved
