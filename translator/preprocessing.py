"""번역 입력을 다듬는 전처리.

Argos Translate 같은 문장 단위 NMT는 문장이 짧을수록 정확도가 높다는 전제로,
RSS 특유의 잡음을 제거하고 너무 긴 문장을 접속사/구두점 경계에서 잘게 쪼갠다.
`html_cleanup.clean_for_translation()`(HTML 태그/엔티티/워드프레스 푸터 제거)
다음 단계로 적용된다 — 이 모듈은 이미 평문이 된 텍스트를 대상으로 한다.
"""

import re
from typing import List

MAX_SENTENCE_WORDS = 40

_NOISE_PATTERNS = [
    re.compile(r"read more\.*", re.IGNORECASE),
    re.compile(r"\[\+\s*\d+\s*chars?\]", re.IGNORECASE),  # 예: "[+1234 chars]"
    re.compile(r"\.{4,}"),  # 4개 이상 이어진 마침표(과도한 줄임표)
]

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_BOUNDARY = re.compile(
    r",\s+(?=and\b|but\b|while\b|which\b|who\b|because\b)|;\s+"
)
_WHITESPACE_RUN = re.compile(r"\s+")


def remove_noise(text: str) -> str:
    """RSS 요약에 흔한 잡음("Read more...", "[+123 chars]", 과도한 줄임표)을 제거한다."""
    for pattern in _NOISE_PATTERNS:
        text = pattern.sub(" ", text)
    return _WHITESPACE_RUN.sub(" ", text).strip()


def split_into_translatable_chunks(text: str, max_words: int = MAX_SENTENCE_WORDS) -> List[str]:
    """문장 단위로 나누고, max_words를 넘는 문장은 접속사/세미콜론 경계에서 추가로 쪼갠다.

    반환값은 번역 후 공백으로 이어 붙이면 원래 순서를 유지하는 조각(chunk) 목록이다.
    쪼갤 경계를 찾지 못하면(접속사/세미콜론이 없으면) 문장을 그대로 둔다 — 억지로
    단어 수 기준으로 자르면 문맥이 끊겨 번역 품질이 오히려 나빠지기 때문이다.
    """
    if not text.strip():
        return []

    chunks: List[str] = []
    for sentence in _SENTENCE_BOUNDARY.split(text):
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(sentence.split()) <= max_words:
            chunks.append(sentence)
            continue

        parts = [part.strip() for part in _CLAUSE_BOUNDARY.split(sentence) if part.strip()]
        chunks.extend(parts if len(parts) > 1 else [sentence])

    return chunks
