"""기사를 MATCH/TRANSFER/PLAYER/OTHER 4개 카테고리로 분류하는 규칙 기반 모듈.

LLM 없이 아래 우선순위로만 판정한다 (순서가 중요하다 — 위에서부터 먼저 매칭되는
규칙을 따른다):

1. 이미 루머 스레드(rumor_thread)에 묶인 기사 → TRANSFER. 같은 선수+구단으로
   여러 매체가 다루고 있다는 신호(rumor_clusterer.py)가 이미 있으므로 키워드
   재검사 없이 최우선으로 확정한다.
2. 경기 프리뷰/라이브 업데이트/결과/평점 등 경기 관련 키워드(MATCH_KEYWORDS) 또는
   제목의 스코어 패턴("3-1" 등) → MATCH.
3. 부상/수상/계약 연장 등 선수 개인 소식 키워드(PLAYER_KEYWORDS) → PLAYER.
4. 이적 관련 키워드는 있지만(아직 구단 미태깅/선수명 후보 없음 등의 이유로) 루머
   스레드에 묶이지 않은 단발성 기사 → TRANSFER. rumor_clusterer.detect_story_stage()
   를 그대로 재사용한다 — 그 함수의 키워드 목록이 사실상 "이적 관련 키워드
   목록"과 같아서 별도로 중복 유지하지 않는다.
5. 위 어디에도 해당하지 않으면 → OTHER (리그 전반 이슈 등).
"""

from category_keywords import MATCH_KEYWORDS, PLAYER_KEYWORDS, SCORE_PATTERN
from rumor_clusterer import detect_story_stage


def classify_category(title: str, content: str, is_transfer_clustered: bool) -> str:
    """기사 제목+본문과 루머 스레드 클러스터링 여부로 카테고리를 판정한다.

    is_transfer_clustered는 이 기사가 rumor_thread_articles에 연결될 예정이거나
    이미 연결돼 있는지를 나타낸다 (db.py는 저장 시점에 미리 계산한 값을,
    backfill_categories.py는 rumor_thread_articles 조회 결과를 그대로 넘긴다).
    """
    if is_transfer_clustered:
        return "TRANSFER"

    text_lower = f"{title}\n{content}".lower()

    if any(keyword in text_lower for keyword in MATCH_KEYWORDS) or SCORE_PATTERN.search(title):
        return "MATCH"

    if any(keyword in text_lower for keyword in PLAYER_KEYWORDS):
        return "PLAYER"

    if detect_story_stage(title, content) != "UNKNOWN":
        return "TRANSFER"

    return "OTHER"
