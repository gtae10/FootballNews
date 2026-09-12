"""기사 본문에서 언급된 구단을 자동으로 감지하는 모듈.

clubs 테이블(backend가 관리하는 것과 같은 DB)의 50개 구단 이름을 기준으로 삼는다.
기사 하나가 여러 구단을 언급하면(예: 이적 기사) 감지된 구단을 모두 반환한다 —
저장 방식은 db.py/article_clubs 참고.

대소문자를 구분하지 않고 매칭하면 "Nice"(OGC Nice), "Lens"(RC Lens)처럼 흔한 영어 단어와
겹치는 구단 축약명에서 오탐이 생긴다. 뉴스 기사 제목/본문은 고유명사를 정상적으로 대문자로
표기하므로, 원문 대소문자를 그대로 유지한 채(대소문자 구분) 매칭해 이 문제를 피한다.
"""

import re
from typing import Dict, Iterable, List

from sqlalchemy import text as sql_text
from sqlalchemy.engine import Engine

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
    "Real Betis": ["Betis"],
}


def fetch_clubs_from_db(engine: Engine) -> List[dict]:
    """clubs 테이블에서 구단 목록({id, name, league})을 직접 가져온다.

    예전에는 백엔드 GET /clubs를 HTTP로 호출했는데, collector가 백엔드보다 먼저
    실행되거나 백엔드가 다른 포트에 떠 있으면(로컬 개발 환경에서 실제로 발생함)
    구단 자동 태깅이 통째로 스킵되는 문제가 있었다. collector는 어차피 backend와
    같은 DB(clubs 테이블 포함)를 직접 보고 있으므로, 굳이 HTTP를 거칠 필요가
    없어 이 방식으로 바꿨다 — 백엔드 기동 여부와 무관하게 항상 동작한다.
    """
    with engine.connect() as connection:
        rows = connection.execute(sql_text("SELECT id, name, league FROM clubs")).all()
    return [{"id": row.id, "name": row.name, "league": row.league} for row in rows]


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
