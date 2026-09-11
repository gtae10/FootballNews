"""번역 일관성을 위한 축구 용어집.

두 가지 방식으로 쓰인다:
- `build_glossary_prompt()`: LLM 프롬프트에 포함시켜 번역 시점에 용어를 통일시킨다
  (anthropic_engine.py/openai_engine.py처럼 시스템 프롬프트를 지원하는 엔진에서 사용).
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
    # 아래는 실제 Argos Translate 번역 결과에서 영단어가 그대로 남거나 어색하게
    # 옮겨지는 것이 관찰되어 추가했다 (예: "23세의 Midfielder", "Liverpool Transfer").
    "midfielder": "미드필더",
    "striker": "스트라이커",
    "winger": "윙어",
    "manager": "감독",
    "transfer": "이적",
    "medical": "메디컬 테스트",
    "here we go": "히어 위 고",  # 파브리지오 로마노 특유의 표현, 한국 축구 팬들 사이에서도 음역 그대로 통용된다.
    "green light": "청신호",
    "agreement": "합의",
    "verdict": "평가",
}

# Argos Translate가 영단어를 그대로 남기는 게 아니라 아예 다른 뜻의 한국어로
# 잘못 옮기는 경우(위 apply_glossary는 영단어 매칭이라 이런 경우는 못 잡는다).
# 실제로 관찰된 사례만 좁게 넣는다 — "transfer window"를 "전송 창"으로 옮기는
# 것("전송"은 데이터 전송이라는 뜻이라 축구 이적과 무관하다).
KOREAN_MISTRANSLATION_FIXES = {
    "전송 창": "이적 시장",
}


def build_glossary_prompt() -> str:
    lines = [f"- {en} → {ko}" for en, ko in FOOTBALL_GLOSSARY.items()]
    return "다음 축구 용어는 아래 번역을 일관되게 사용하세요:\n" + "\n".join(lines)


def apply_glossary(text: str) -> str:
    """번역 결과 텍스트에 남아있는 영문 축구 용어를 한국어 용어로 치환한다.

    대소문자를 구분하지 않고 매칭하며, 원문의 대소문자와 무관하게 항상 용어집에
    정의된 한국어 표기로 통일한다. 이미 한국어로 잘 번역된 텍스트는 매칭될
    영문이 없으므로 그대로 유지된다(안전하게 여러 번 적용해도 무해하다).

    일반적인 `\\b`(단어 경계) 대신 `(?<![A-Za-z])`/`(?![A-Za-z])`를 쓴다 —
    Python 정규식의 `\\b`는 한글도 "단어 문자"로 취급해서, "Midfielder는"처럼
    영단어 바로 뒤에 한국어 조사가 공백 없이 붙는 실제 번역 결과에서 경계로
    인식되지 않아 매칭에 실패하기 때문이다.
    """
    for en, ko in FOOTBALL_GLOSSARY.items():
        pattern = r"(?<![A-Za-z])" + re.escape(en) + r"(?![A-Za-z])"
        text = re.sub(pattern, ko, text, flags=re.IGNORECASE)
    for wrong, right in KOREAN_MISTRANSLATION_FIXES.items():
        text = text.replace(wrong, right)
    return text
