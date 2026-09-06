"""기사를 이적 루머 스레드(같은 선수 + 구단 건)로 묶는 규칙 기반 클러스터링 모듈.

LLM 없이 아래 규칙만으로 동작한다.

1. player_extractor로 뽑은 선수명 후보와 article_clubs에 태깅된 구단을 조합해
   (선수명, 구단) 쌍마다 스레드를 찾거나 새로 만든다. 같은 조합의 기존 스레드가
   있고, 그 스레드에 이미 포함된 기사 중 가장 최근 발행일로부터 14일 이내면
   거기 합류시키고, 없으면 새 스레드를 만든다(rumor_threads.CLUSTER_WINDOW_DAYS).
2. 기사 본문 키워드로 스토리 단계(INTEREST < NEGOTIATION < CONFIRMED < OFFICIAL,
   매칭 안 되면 UNKNOWN)를 추정해 그 기사의 story_stage로 저장하고, 스레드
   전체의 latest_stage는 지금까지 등장한 기사들 중 가장 진전된 단계로 갱신한다.
3. 스레드의 최초 기사 발행 시각으로부터 48시간 이내에 보도한, 서로 다른
   source(매체)의 수를 independent_source_count로 계산해 저장한다. 이 값이
   2 이상이면 cross_reported를 True로 표시한다.

용어에 대한 주의: `independent_source_count`/`cross_reported`는 "여러 매체가
서로 독립적으로 같은 이야기를 보도했다"는 뜻일 뿐, "이적이 사실로 확인됐다"는
뜻이 아니다. 의도적으로 `verified_*`라는 이름을 피했다 — 그 이름은 "사실
검증됨"으로 오해하기 쉽기 때문이다. API 응답과 문서에도 같은 이름/설명을
그대로 사용한다(docs/API.md 참고).
"""

from datetime import datetime, timedelta, timezone
from typing import Iterable, List

from sqlalchemy import text
from sqlalchemy.engine import Connection

CLUSTER_WINDOW_DAYS = 14
CROSS_VERIFY_WINDOW_HOURS = 48
CROSS_VERIFY_MIN_SOURCES = 2

# 앞쪽(더 진전된 단계)을 먼저 확인한다 — 공식 발표 기사도 배경 설명에서
# "linked"처럼 초기 단계 단어를 함께 쓰는 경우가 있어, 가장 진전된 신호를
# 우선한다.
_STAGE_KEYWORDS = [
    ("OFFICIAL", ["official", "complet", "signs for", "signs a", "unveiled as", "confirms move"]),
    ("CONFIRMED", [
        "here we go", "medical", "agreed terms", "agreement reached",
        "verbal agreement", "personal terms",
    ]),
    ("NEGOTIATION", [
        "bid", "offer", "in talks", "talks", "negotiat", "edging closer", "swoop",
        "green light", "set to sign", "deal off", "close to joining",
    ]),
    ("INTEREST", [
        "linked", "interested in", "keen on", "monitoring", "target", "eyeing",
        "on radar", "on the radar",
        "transfer deadline",
    ]),
]
_STAGE_ORDER = ["UNKNOWN", "INTEREST", "NEGOTIATION", "CONFIRMED", "OFFICIAL"]


def detect_story_stage(title: str, content: str) -> str:
    """제목+본문 키워드로 스토리 단계를 추정한다. 매칭되는 키워드가 없으면 UNKNOWN."""
    text_lower = f"{title}\n{content}".lower()
    for stage, keywords in _STAGE_KEYWORDS:
        if any(keyword in text_lower for keyword in keywords):
            return stage
    return "UNKNOWN"


def _more_advanced(a: str, b: str) -> str:
    return a if _STAGE_ORDER.index(a) >= _STAGE_ORDER.index(b) else b


def cluster_article(
    connection: Connection,
    article_id: int,
    published_at: datetime,
    player_candidates: Iterable[str],
    clubs: Iterable[str],
    story_stage: str,
) -> List[int]:
    """기사 하나를 (선수명 후보 x 구단) 조합마다 스레드에 연결한다.

    한 기사가 여러 선수/구단을 함께 언급하면(예: "Liverpool and PSG both chase
    Isak") 여러 스레드에 동시에 연결될 수 있다. 연결된 rumor_thread id 목록을
    반환한다.
    """
    thread_ids = []
    for player_name in player_candidates:
        for club_name in clubs:
            thread_id = _find_or_create_thread(connection, player_name, club_name, published_at)
            connection.execute(
                text(
                    "INSERT INTO rumor_thread_articles (rumor_thread_id, article_id, story_stage) "
                    "VALUES (:thread_id, :article_id, :stage)"
                ),
                {"thread_id": thread_id, "article_id": article_id, "stage": story_stage},
            )
            _touch_thread(connection, thread_id, story_stage)
            _recompute_cross_verification(connection, thread_id)
            thread_ids.append(thread_id)
    return thread_ids


def _find_or_create_thread(connection: Connection, player_name: str, club_name: str, published_at: datetime) -> int:
    window_start = published_at - timedelta(days=CLUSTER_WINDOW_DAYS)
    row = connection.execute(
        text(
            """
            SELECT rt.id
            FROM rumor_threads rt
            JOIN rumor_thread_articles rta ON rta.rumor_thread_id = rt.id
            JOIN articles a ON a.id = rta.article_id
            WHERE LOWER(rt.player_name) = LOWER(:player_name)
              AND rt.club_name = :club_name
            GROUP BY rt.id
            HAVING MAX(a.published_at) >= :window_start
            ORDER BY MAX(a.published_at) DESC
            LIMIT 1
            """
        ),
        {"player_name": player_name, "club_name": club_name, "window_start": window_start},
    ).first()
    if row:
        return row.id

    now = datetime.now(timezone.utc)
    result = connection.execute(
        text(
            """
            INSERT INTO rumor_threads
                (player_name, club_name, latest_stage, independent_source_count,
                 cross_reported, created_at, updated_at)
            VALUES (:player_name, :club_name, 'UNKNOWN', 0, 0, :now, :now)
            """
        ),
        {"player_name": player_name, "club_name": club_name, "now": now},
    )
    return result.lastrowid


def _touch_thread(connection: Connection, thread_id: int, story_stage: str) -> None:
    row = connection.execute(
        text("SELECT latest_stage FROM rumor_threads WHERE id = :id"), {"id": thread_id}
    ).first()
    new_stage = _more_advanced(row.latest_stage, story_stage)
    connection.execute(
        text("UPDATE rumor_threads SET latest_stage = :stage, updated_at = :now WHERE id = :id"),
        {"stage": new_stage, "now": datetime.now(timezone.utc), "id": thread_id},
    )


def _recompute_cross_verification(connection: Connection, thread_id: int) -> None:
    first_row = connection.execute(
        text(
            "SELECT MIN(a.published_at) AS first_at FROM rumor_thread_articles rta "
            "JOIN articles a ON a.id = rta.article_id WHERE rta.rumor_thread_id = :id"
        ),
        {"id": thread_id},
    ).first()
    if first_row is None or first_row.first_at is None:
        return

    first_at = first_row.first_at
    if isinstance(first_at, str):  # sqlite(테스트)는 TEXT로 저장하므로 파싱해 되돌린다
        first_at = datetime.fromisoformat(first_at)
    window_end = first_at + timedelta(hours=CROSS_VERIFY_WINDOW_HOURS)

    count_row = connection.execute(
        text(
            "SELECT COUNT(DISTINCT a.source) AS cnt FROM rumor_thread_articles rta "
            "JOIN articles a ON a.id = rta.article_id "
            "WHERE rta.rumor_thread_id = :id AND a.published_at <= :window_end"
        ),
        {"id": thread_id, "window_end": window_end},
    ).first()
    independent_source_count = count_row.cnt or 0
    cross_reported = independent_source_count >= CROSS_VERIFY_MIN_SOURCES

    connection.execute(
        text(
            "UPDATE rumor_threads SET independent_source_count = :cnt, cross_reported = :cross "
            "WHERE id = :id"
        ),
        {"cnt": independent_source_count, "cross": cross_reported, "id": thread_id},
    )
