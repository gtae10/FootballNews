"""번역 일관성을 위한 축구 용어집.

LLM 프롬프트에 포함시켜 용어 번역을 통일하는 데 사용한다.
"""

FOOTBALL_GLOSSARY = {
    "clean sheet": "무실점",
    "offside": "오프사이드",
    "set piece": "세트피스",
    "clean strike": "깔끔한 슈팅",
    "matchday": "경기일",
    "starting XI": "선발 라인업",
    "loan move": "임대 이적",
}


def build_glossary_prompt() -> str:
    lines = [f"- {en} → {ko}" for en, ko in FOOTBALL_GLOSSARY.items()]
    return "다음 축구 용어는 아래 번역을 일관되게 사용하세요:\n" + "\n".join(lines)
