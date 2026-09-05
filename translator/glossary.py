"""번역 일관성을 위한 축구 용어집.

두 가지 방식으로 쓰인다:
- `build_glossary_prompt()`: LLM 프롬프트에 포함시켜 번역 시점에 용어를 통일시킨다
  (anthropic_engine.py처럼 시스템 프롬프트를 지원하는 엔진에서 사용).
- `apply_glossary()`: 번역이 끝난 결과 텍스트에 후처리로 용어를 치환한다. Argos
  Translate 같은 NMT 엔진은 프롬프트 개념이 없어 번역 도중에 용어를 지시할 수
  없으므로, 번역 후 원문에 남아있는 영문 용어(NMT가 통째로 못 옮기고 그대로 둔
  경우가 흔하다)를 찾아 정해진 한국어 용어로 바꿔치기한다.
"""

import re

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


def apply_glossary(text: str) -> str:
    """번역 결과 텍스트에 남아있는 영문 축구 용어를 한국어 용어로 치환한다.

    대소문자를 구분하지 않고 단어 경계 기준으로 매칭하며, 원문의 대소문자와
    무관하게 항상 용어집에 정의된 한국어 표기로 통일한다. 이미 한국어로 잘
    번역된 텍스트는 매칭될 영문이 없으므로 그대로 유지된다(안전하게 여러 번
    적용해도 무해하다).
    """
    for en, ko in FOOTBALL_GLOSSARY.items():
        text = re.sub(r"\b" + re.escape(en) + r"\b", ko, text, flags=re.IGNORECASE)
    return text
