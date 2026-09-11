"""GPT(OpenAI API) 기반 번역 엔진.

anthropic_engine.py/argos_engine.py와 나란히 존재하는 세 번째 선택지다
(translate.py의 ENGINE 참고). `translate.py`의 `ENGINE`(또는 `TRANSLATOR_ENGINE`
환경 변수)을 `"openai"`로 설정하면 쓸 수 있다. `OPENAI_API_KEY` 환경 변수가
필요하다.

모델은 번역/요약처럼 상대적으로 단순한 작업이라는 점을 감안해 비용 효율적인
`gpt-5-mini`를 기본값으로 쓴다(2026-09 기준 OpenAI 가격표에서 `gpt-5-nano`가
더 저렴하지만, 축구 기사 요약 번역에는 지시 이행/JSON 출력 안정성이 더
중요하다고 판단해 한 단계 위인 mini를 골랐다).
"""

import json
from typing import Optional, Tuple

import openai
from openai import OpenAI

from glossary import build_glossary_prompt

MODEL = "gpt-5-mini"

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


class TranslationError(Exception):
    """OpenAI 번역 실패(인증/rate limit/빈 응답/JSON 파싱 실패 등)를 나타낸다.

    translate.py의 run_translation_batch()가 이 예외를 잡아 해당 기사의
    status를 COLLECTED로 유지하고 다음 배치에서 재시도하도록 한다.
    """


def build_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(glossary=build_glossary_prompt())


def _get_client() -> OpenAI:
    # OPENAI_API_KEY 환경 변수에서 자동으로 키를 읽는다. 코드에 키를 하드코딩하지 않는다.
    return OpenAI()


def translate(
    title_original: str,
    content_original: str,
    client: Optional[OpenAI] = None,
) -> Tuple[str, str, str]:
    """원문 제목/본문을 GPT로 요약 번역해 (title_ko, content_ko, model_version)을 반환한다.

    인증 실패, rate limit, 빈 응답, JSON 파싱 실패는 모두 TranslationError로
    통일해서 던진다 — 호출부(translate.py)가 예외 종류를 구분할 필요 없이
    "이 기사는 이번 배치에서 실패했다"로만 처리하면 되게 하기 위함이다.
    """
    client = client or _get_client()

    try:
        response = client.chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": build_system_prompt()},
                {
                    "role": "user",
                    "content": f"제목: {title_original}\n\n본문:\n{content_original}",
                },
            ],
        )
    except openai.OpenAIError as exc:
        raise TranslationError(f"OpenAI API 호출 실패: {exc}") from exc

    if not response.choices:
        raise TranslationError("OpenAI 응답에 choices가 없음")

    text = response.choices[0].message.content
    if not text or not text.strip():
        raise TranslationError("OpenAI 응답 본문이 비어 있음")

    try:
        parsed = json.loads(text)
        title_ko = parsed["title_ko"]
        content_ko = parsed["content_ko"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise TranslationError(f"OpenAI 응답 JSON 파싱 실패: {exc}") from exc

    return title_ko, content_ko, MODEL
