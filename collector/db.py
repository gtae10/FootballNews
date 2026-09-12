"""수집된 기사 원문을 DB(articles 테이블)에 저장하는 모듈.

backend(Spring Boot)와 동일한 스키마(`docs/DB_SCHEMA.md` 참고)를 사용한다.
연결 정보는 환경 변수로만 주입하며, 비밀번호를 코드에 하드코딩하지 않는다.
"""

import os
import sys
import time
from datetime import datetime, timezone
from typing import Iterable

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from article_classifier import classify_category
from body_image_extractor import fetch_body_images
from club_matcher import build_alias_map, detect_clubs, fetch_clubs_from_db
from player_extractor import build_excluded_names, extract_player_candidates
from reporter_detector import detect_quoted_reporter, resolve_source_tier
from rss_collector import CollectedArticle
from rumor_clusterer import cluster_article, detect_story_stage
from trusted_reporters import TRUSTED_REPORTERS

# 기사 원문 페이지에서 본문 이미지를 추가로 크롤링(body_image_extractor.py)할 때,
# 기사 저장마다 매번 원본 서버에 요청을 보내게 되므로 요청 사이 최소 지연을 둔다.
# backfill.py의 REQUEST_DELAY_SECONDS와 같은 취지 — 소스에 부담을 주지 않기 위함이다.
BODY_IMAGE_REQUEST_DELAY_SECONDS = 1.0

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


def _load_alias_map(engine: Engine) -> dict:
    """clubs 테이블에서 구단 별칭 맵을 만든다.

    예전에는 백엔드 GET /clubs를 HTTP로 호출했는데, 백엔드가 떠 있지 않거나 다른
    포트에 떠 있으면 구단 자동 태깅이 조용히 통째로 스킵되는 문제가 실제로 있었다
    (2026-09-11 백필, 2026-09-12 백필 중 각각 발생 확인). collector가 backend와
    같은 DB를 직접 보고 있으므로 club_matcher.fetch_clubs_from_db()로 바꿔 이
    의존성 자체를 없앴다 — 이제 원칙적으로 실패할 일이 없지만(articles 저장에
    쓰는 것과 같은 DB 연결이라 이게 안 되면 저장 자체도 안 됨), 혹시 clubs
    테이블이 아직 없는 등 예외적인 경우를 대비해 실패해도 수집 자체는 막지 않되
    stderr에 눈에 띄게 남긴다(예전처럼 stdout에 조용히 한 줄만 남기지 않는다).
    """
    try:
        return build_alias_map(fetch_clubs_from_db(engine))
    except Exception as error:  # noqa: BLE001 - clubs 조회 실패가 수집 자체를 막지 않는다
        print(
            f"[WARNING] clubs 테이블 조회 실패 - 구단 자동 태깅을 건너뜁니다: {error}",
            file=sys.stderr,
        )
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
    alias_map = _load_alias_map(engine)
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

            # story_stage가 UNKNOWN이면(이적 관련 키워드가 전혀 없으면) 클러스터링하지 않는다.
            # 그렇지 않으면 경기 리포트처럼 이적과 무관한 기사도 "같은 선수+구단 언급"이라는
            # 이유만으로 루머 스레드에 섞여 들어가 교차검증으로 오인될 수 있다. 이 조건을
            # INSERT 이전에 미리 계산해두면 article_classifier.classify_category()의
            # "이미 루머 스레드에 묶일 기사인가" 판정에도 그대로 재사용할 수 있다.
            story_stage = "UNKNOWN"
            player_candidates: list = []
            if detected_clubs:
                story_stage = detect_story_stage(article.title_original, article.content_original)
                if story_stage != "UNKNOWN":
                    player_candidates = extract_player_candidates(article.title_original, excluded_names)
            is_transfer_clustered = bool(detected_clubs) and story_stage != "UNKNOWN" and bool(player_candidates)

            category = classify_category(article.title_original, article.content_original, is_transfer_clustered)

            result = connection.execute(
                text(
                    """
                    INSERT INTO articles
                        (source, original_url, title_original, content_original,
                         published_at, collected_at, status, source_tier, quoted_reporter, image_url,
                         category)
                    VALUES
                        (:source, :original_url, :title_original, :content_original,
                         :published_at, :collected_at, 'COLLECTED', :source_tier, :quoted_reporter, :image_url,
                         :category)
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
                    "category": category,
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

            if is_transfer_clustered:
                cluster_article(
                    connection, article_id, article.published_at,
                    player_candidates, detected_clubs, story_stage,
                )

            # 본문 페이지를 직접 요청해 이미지를 추가로 찾는다. 실패하거나(네트워크
            # 오류 등) 이미지를 하나도 못 찾으면 빈 리스트가 반환되므로, 이 경우
            # article_images에는 아무것도 저장되지 않고 기존 대표 이미지(image_url)
            # 하나만 남는다 — 프론트가 자연스럽게 그 상태로 폴백한다.
            body_images = fetch_body_images(article.original_url, exclude_url=article.image_url)
            for position, image_url in enumerate(body_images):
                connection.execute(
                    text(
                        """
                        INSERT INTO article_images (article_id, position, image_url)
                        VALUES (:article_id, :position, :image_url)
                        """
                    ),
                    {"article_id": article_id, "position": position, "image_url": image_url},
                )
            time.sleep(BODY_IMAGE_REQUEST_DELAY_SECONDS)

            saved += 1

    return saved
