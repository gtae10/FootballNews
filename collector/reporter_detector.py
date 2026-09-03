"""기사 본문에서 유명 기자/계정의 인용을 감지하는 모듈.

trusted_reporters.py에 등록된 이름이 언급되고, 그 주변에 인용 동사
(reports/says/according to/claims 등)가 함께 있어야 매칭으로 인정한다.
이름만 우연히 등장한 경우(오탐)를 줄이기 위한 최소한의 안전장치다.
"""

import re
from typing import Optional

from trusted_reporters import TRUSTED_REPORTERS

QUOTE_VERBS = [
    "reports",
    "reported",
    "report",
    "says",
    "said",
    "according to",
    "claims",
    "claimed",
]

_CONTEXT_WINDOW = 60  # 이름 앞뒤로 이 글자 수 안에 인용 동사가 있는지 확인


def detect_quoted_reporter(title: str, content: str) -> Optional[dict]:
    """title/content에서 인용된 기자/계정 중 가장 신뢰도가 높은(tier가 낮은) 하나를 반환한다.

    여러 명이 감지되면 tier가 가장 낮은(=가장 신뢰도 높은) 한 명만 반환한다.
    감지된 사람이 없으면 None.
    """
    text_lower = f"{title}\n{content}".lower()

    matched = [reporter for reporter in TRUSTED_REPORTERS if _is_quoted(reporter, text_lower)]
    if not matched:
        return None

    return min(matched, key=lambda reporter: reporter["tier"])


def resolve_source_tier(existing_tier: Optional[int], detected: Optional[dict]) -> Optional[int]:
    """감지된 기자의 tier가 기존 source_tier보다 신뢰도가 높을 때만(숫자가 작을 때만) 반영한다.

    existing_tier가 None(미정)이면 감지된 기자의 tier를 그대로 사용한다.
    감지된 기자가 없으면 existing_tier를 그대로 반환한다.
    """
    if detected is None:
        return existing_tier
    if existing_tier is None or detected["tier"] < existing_tier:
        return detected["tier"]
    return existing_tier


def _is_quoted(reporter: dict, text_lower: str) -> bool:
    for alias in reporter["aliases"]:
        pattern = r"\b" + re.escape(alias.lower()) + r"\b"
        for match in re.finditer(pattern, text_lower):
            start = max(0, match.start() - _CONTEXT_WINDOW)
            end = min(len(text_lower), match.end() + _CONTEXT_WINDOW)
            window = text_lower[start:end]
            if any(verb in window for verb in QUOTE_VERBS):
                return True
    return False
