"""기사 카테고리 분류(article_classifier.py)에 쓰는 키워드 목록.

MATCH/PLAYER 카테고리 판정에만 쓰는 키워드를 모아 튜닝하기 쉽게 별도 파일로 뺐다.
TRANSFER 판정은 이 파일에 별도 키워드 목록을 두지 않는다 — rumor_clusterer.py의
_STAGE_KEYWORDS(이적 스토리 단계 판정에 쓰는 키워드)가 사실상 "이적 관련 키워드
목록"과 같아서, 같은 목록을 article_classifier.py가 detect_story_stage()를 통해
그대로 재사용한다(중복 유지 방지). 이적 스토리 단계 키워드를 조정하고 싶으면
rumor_clusterer.py의 _STAGE_KEYWORDS를 수정한다.

실제 저장된 기사 제목을 DB에서 직접 훑어보고 보완하지는 못했다(이 환경에서는 로컬
MySQL에 접근할 수 없었다) — 아래 목록은 영어 축구 뉴스 매체에서 흔히 쓰는 표현을
기준으로 작성했다. 오탐/누락이 보이면 이 파일만 수정하면 된다.
"""

import re

# 경기 프리뷰/라이브 업데이트/결과/평점 등에서 흔히 쓰는 표현.
MATCH_KEYWORDS = [
    "match report",
    "match preview",
    "preview",
    "player ratings",
    "predicted lineup",
    "predicted line-up",
    "highlights",
    "final score",
    "full time",
    "full-time",
    "half time",
    "half-time",
    "team news",
    "matchday squad",
    "starting line up",
    "starting lineup",
    "line-up",
    "kick off",
    "kick-off",
    "how to watch",
    "tv channel",
    "as it happened",
    "live updates",
    "live blog",
    "post-match",
    "post match",
    "match analysis",
    "reaction",
]

# 부상/수상/계약 연장 등 선수 개인 소식에서 흔히 쓰는 표현.
PLAYER_KEYWORDS = [
    "injury",
    "injured",
    "sidelined",
    "ruled out",
    "out for the season",
    "return date",
    "returns to training",
    "return to training",
    "fitness update",
    "wins award",
    "named player of the",
    "player of the month",
    "player of the season",
    "man of the match",
    "signs new contract",
    "contract extension",
    "extends his contract",
    "new deal",
    "testimonial",
    "retires",
    "retirement",
]

# 제목에 "X 2-1 Y"처럼 스코어가 포함되면 경기 결과 기사로 본다.
SCORE_PATTERN = re.compile(r"\b\d{1,2}-\d{1,2}\b")
