"""기사 본문에서 언급된 구단을 자동으로 감지하는 모듈.

백엔드의 GET /clubs가 반환하는 50개 구단 이름을 기준으로 삼는다. 기사 하나가 여러 구단을
언급하면(예: 이적 기사) 감지된 구단을 모두 반환한다 — 저장 방식은 db.py/article_clubs 참고.

대소문자를 구분하지 않고 매칭하면 "Nice"(OGC Nice), "Lens"(RC Lens)처럼 흔한 영어 단어와
겹치는 구단 축약명에서 오탐이 생긴다. 뉴스 기사 제목/본문은 고유명사를 정상적으로 대문자로
표기하므로, 원문 대소문자를 그대로 유지한 채(대소문자 구분) 매칭해 이 문제를 피한다.
"""

import os
import re
from typing import Dict, Iterable, List

import requests

DEFAULT_BACKEND_API_URL = os.environ.get("COLLECTOR_BACKEND_API_URL", "http://localhost:8080/api/v1")

# 구단 공식명만으로는 기사 본문에서 잘 안 잡히는 흔한 축약형/별칭을 보완한다.
# 여기 없는 구단은 GET /clubs가 반환한 공식명만으로 매칭한다.
ALIAS_OVERRIDES: Dict[str, List[str]] = {
    "Manchester United": ["Man United", "Man Utd", "MUFC"],
    "Manchester City": ["Man City", "MCFC"],
    "Tottenham Hotspur": ["Tottenham", "Spurs"],
    "Newcastle United": ["Newcastle"],
    "West Ham United": ["West Ham"],
    "Aston Villa": ["Villa"],
    "Real Madrid": ["Real Madrid"],
    "Barcelona": ["Barca", "Barça", "FC Barcelona"],
    "Atletico Madrid": ["Atletico", "Atlético Madrid"],
    "Athletic Bilbao": ["Athletic Club"],
    "Bayern Munich": ["Bayern", "FC Bayern"],
    "Borussia Dortmund": ["Dortmund", "BVB"],
    "Bayer Leverkusen": ["Leverkusen"],
    "RB Leipzig": ["Leipzig"],
    "Eintracht Frankfurt": ["Frankfurt"],
    "VfB Stuttgart": ["Stuttgart"],
    "Borussia Monchengladbach": ["Monchengladbach", "Gladbach", "Borussia Mönchengladbach"],
    "Inter Milan": ["Inter"],
    "AC Milan": ["Milan"],
    "AS Roma": ["Roma"],
    "Paris Saint-Germain": ["PSG"],
}


def fetch_clubs(api_base_url: str = DEFAULT_BACKEND_API_URL) -> List[dict]:
    """백엔드 GET /clubs를 호출해 구단 목록({id, name, league})을 가져온다."""
    response = requests.get(f"{api_base_url}/clubs", timeout=10)
    response.raise_for_status()
    return response.json()


def build_alias_map(clubs: Iterable[dict]) -> Dict[str, List[str]]:
    """구단명 -> [구단명, 별칭...] 매핑을 만든다. 키는 클럽 공식명(GET /clubs의 name)이다."""
    alias_map: Dict[str, List[str]] = {}
    for club in clubs:
        name = club["name"]
        aliases = {name, *ALIAS_OVERRIDES.get(name, [])}
        alias_map[name] = sorted(aliases)
    return alias_map


def detect_clubs(text: str, alias_map: Dict[str, List[str]]) -> List[str]:
    """text(제목+본문)에서 언급된 구단명을 모두 찾아 반환한다 (대소문자 구분, 단어 경계 매칭)."""
    matched = []
    for club_name, aliases in alias_map.items():
        for alias in aliases:
            if re.search(r"\b" + re.escape(alias) + r"\b", text):
                matched.append(club_name)
                break
    return sorted(matched)
