"""기사 제목에서 선수명(고유명사) 후보를 추출하는 규칙 기반 모듈.

LLM 없이 정규식 휴리스틱만으로 동작한다: 대문자로 시작하는 단어가 1~3개
연속되면 후보로 보되, 이미 알려진 구단명/기자명/대회명/흔한 문장 시작
단어(스톱워드)는 제외한다.

정확도 트레이드오프 (완벽한 개체명 인식이 아니므로 감안해야 한다):
- 오탐(false positive): 무명 대회명, 지명, 문장 맨 앞의 흔한 단어("Report",
  "Exclusive" 등)가 후보로 잡힐 수 있다 — 스톱워드/대회명 목록으로 흔한
  사례만 걸러낸다. 완전히 막을 수는 없다.
- 누락(false negative): 소문자로 표기되는 별명, 하이픈/아포스트로피 포함
  이름의 일부, 구단명 별칭과 우연히 겹치는 성씨(예: 구단명이 곧 사람 성씨인
  경우)는 못 잡거나 걸러질 수 있다.
- 완벽을 목표로 하지 않는다. rumor_clusterer.py가 "구단 태그 + 이름 후보
  일치 + 14일 이내 발행"이라는 다중 조건으로 묶기 때문에, 이름 후보 하나가
  다소 부정확해도 전혀 다른 스레드로 잘못 묶일 가능성은 조건들이 함께
  걸러준다.
"""

import re
from typing import Iterable, List, Set

_CAPITALIZED_RUN = re.compile(r"\b[A-Z][a-zA-Z'\-]*(?:\s+[A-Z][a-zA-Z'\-]*){0,2}\b")

# 문장 맨 앞이라 대문자로 시작하지만 사람 이름이 아닌 흔한 단어들.
_STOPWORDS = {
    "The", "A", "An", "This", "That", "These", "Those", "Why", "How", "What",
    "Who", "When", "Where", "Which", "In", "On", "At", "For", "With", "Report",
    "Reports", "Exclusive", "Confirmed", "Revealed", "Update", "Breaking",
    "Watch", "Video", "Photo", "Live", "New", "Latest", "Opinion", "Analysis",
    "Preview", "Special", "Rated", "Ranked", "Explained", "Podcast",
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "Here", "Anfield",  # "Here We Go"(로마노 특유의 표현), 경기장 이름은 선수명이 아니다.
}

# 흔히 기사 제목에 등장하는 대회/기구명. 구단명 목록(GET /clubs)에는 없어서
# 별도로 걸러야 한다.
_COMPETITIONS = {
    "Premier League", "Champions League", "Europa League",
    "Europa Conference League", "FA Cup", "League Cup", "Carabao Cup",
    "World Cup", "La Liga", "Serie A", "Bundesliga", "Ligue 1", "EFL",
    "UEFA", "FIFA",
}


def extract_player_candidates(title: str, excluded_names: Iterable[str]) -> List[str]:
    """제목에서 선수명 후보(대문자로 시작하는 1~3단어 연속)를 추출한다.

    excluded_names(구단명+별칭, 기자명+별칭을 합친 집합)와 대회명/스톱워드에
    해당하는 후보는 제외한다. 다른 후보의 부분 문자열인 후보(예: "Isak"이
    "Alexander Isak"의 일부)는 더 긴 쪽만 남긴다.
    """
    excluded_lower = {name.lower() for name in excluded_names} | {
        c.lower() for c in _COMPETITIONS
    }

    candidates: Set[str] = set()
    for match in _CAPITALIZED_RUN.finditer(title):
        words = match.group().split()
        while words and words[0] in _STOPWORDS:
            words = words[1:]
        if not words:
            continue

        candidate = " ".join(words)
        if len(candidate) < 3:
            continue
        if candidate.lower() in excluded_lower:
            continue
        candidates.add(candidate)

    return sorted(
        candidate
        for candidate in candidates
        if not any(candidate != other and candidate in other for other in candidates)
    )


def build_excluded_names(alias_map: dict, reporter_aliases: Iterable[str]) -> Set[str]:
    """구단 별칭 맵(club_matcher.build_alias_map 결과)과 기자 별칭을 하나의 제외 목록으로 합친다."""
    excluded: Set[str] = set()
    for aliases in alias_map.values():
        excluded.update(aliases)
    excluded.update(reporter_aliases)
    return excluded
