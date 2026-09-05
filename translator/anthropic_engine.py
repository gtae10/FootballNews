"""Claude(Anthropic API) 기반 번역 엔진.

카드 등록 없이 바로 쓸 수 있는 Argos Translate로 기본 엔진을 교체하면서
(translate.py의 ENGINE 참고) 이 모듈은 비활성화됐다 — 완전히 삭제하지 않고
그대로 남겨둔 것은, 나중에 상용 API로 다시 바꾸고 싶을 때(번역 품질이 더
중요해지는 시점 등) `translate.py`의 `ENGINE = "anthropic"`으로만 바꾸면
바로 쓸 수 있게 하기 위함이다. `ANTHROPIC_API_KEY` 환경 변수가 필요하다.
"""

import json
from typing import Optional, Tuple

import anthropic

from glossary import build_glossary_prompt

MODEL = "claude-opus-5"

SYSTEM_PROMPT_TEMPLATE = """당신은 축구 기사 번역가입니다.
아래 영문 기사를 한국어로 자연스럽게 요약 번역하세요.

규칙:
- 전문을 그대로 옮기지 말고, 핵심 내용 위주로 3~5문장으로 요약합니다.
  (저작권 문제를 피하기 위해 원문을 그대로 베끼지 않습니다.)
- 사실관계(선수 이름, 수치, 일정 등)는 정확하게 유지합니다.

{glossary}

다른 설명 없이 아래 JSON 형식으로만 응답하세요:
{{"title_ko": "번역된 제목", "content_ko": "요약 번역된 본문"}}
"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(glossary=build_glossary_prompt())


def _get_client() -> anthropic.Anthropic:
    # ANTHROPIC_API_KEY 환경 변수에서 자동으로 키를 읽는다. 코드에 키를 하드코딩하지 않는다.
    return anthropic.Anthropic()


def translate(
    title_original: str,
    content_original: str,
    client: Optional[anthropic.Anthropic] = None,
) -> Tuple[str, str, str]:
    """원문 제목/본문을 Claude로 요약 번역해 (title_ko, content_ko, model_version)을 반환한다."""
    client = client or _get_client()

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=build_system_prompt(),
        messages=[
            {
                "role": "user",
                "content": f"제목: {title_original}\n\n본문:\n{content_original}",
            }
        ],
    )

    text = next((block.text for block in response.content if block.type == "text"), "")
    parsed = json.loads(text)

    return parsed["title_ko"], parsed["content_ko"], MODEL
