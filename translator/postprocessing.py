"""번역 결과에 흔히 남는 어색함을 규칙 기반으로 다듬는 후처리.

완벽한 한국어 교정이 목표가 아니다 — 실제 Argos Translate 번역 결과에서
반복적으로 관찰된, 눈에 띄는 어색함 몇 가지만 줄이는 수준이다:

- 조사 중복("이 이", "은 은" 같은 인접 중복)
- "형용사어간 + 공백 + 인" 패턴("긍정적 인" -> "긍정적인") — Argos가 한국어
  형용사형 어미 앞에 불필요한 공백을 넣는 경우가 실제로 관찰됐다.
- 구두점 앞 불필요한 공백(" ." -> ".")
- 연속 공백
"""

import re

# Python 정규식의 `\b`는 한글도 "단어 문자"로 취급하므로 한국어 텍스트에서는
# 경계로 동작하지 않는다(공백/문장부호가 아니면 항상 "경계 없음"으로 판정됨).
# 그래서 `\b` 대신 조사가 실제로 어디 붙어있는지(앞 글자에 바로 붙어있고, 뒤는
# 공백/문장 끝/문장부호로 끝나는지)를 직접 lookaround로 지정한다.
_DUPLICATE_PARTICLE = re.compile(r"(?<=\S)(이|가|은|는|을|를|의|에|와|과)\s+\1(?=\s|$|[.,!?])")
_ADJECTIVE_SPACE_IN = re.compile(r"(적|스럽|롭)\s+(인|게|다)")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([.,!?])")
_WHITESPACE_RUN = re.compile(r"\s{2,}")


def clean_translation_output(text: str) -> str:
    """번역 결과 텍스트의 흔한 어색함을 정리한다."""
    text = _DUPLICATE_PARTICLE.sub(r"\1", text)
    text = _ADJECTIVE_SPACE_IN.sub(r"\1\2", text)
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = _WHITESPACE_RUN.sub(" ", text)
    return text.strip()
