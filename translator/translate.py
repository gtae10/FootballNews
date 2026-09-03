"""수집된 원문 기사를 LLM으로 번역하는 메인 로직."""

import json
from dataclasses import dataclass
from typing import Optional

import anthropic

import db
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


@dataclass
class TranslationResult:
    title_ko: str
    content_ko: str
    model_version: str


def build_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(glossary=build_glossary_prompt())


def _get_client() -> anthropic.Anthropic:
    # ANTHROPIC_API_KEY 환경 변수에서 자동으로 키를 읽는다. 코드에 키를 하드코딩하지 않는다.
    return anthropic.Anthropic()


def translate_article(
    title_original: str,
    content_original: str,
    client: Optional[anthropic.Anthropic] = None,
) -> TranslationResult:
    """원문 제목/본문을 받아 한국어 요약 번역 결과를 반환한다."""
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

    return TranslationResult(
        title_ko=parsed["title_ko"],
        content_ko=parsed["content_ko"],
        model_version=MODEL,
    )


def run_translation_batch() -> int:
    """DB에서 미번역 기사(status=COLLECTED)를 조회해 순차적으로 번역하고 저장한다.

    반환값은 번역해 저장한 기사 수다.
    """
    engine = db.get_engine()
    client = _get_client()

    articles = db.fetch_untranslated_articles(engine)
    translated_count = 0
    for article in articles:
        result = translate_article(article.title_original, article.content_original, client=client)
        db.save_translation(engine, article.id, result)
        translated_count += 1

    print(f"번역 완료: {translated_count}건")
    return translated_count


if __name__ == "__main__":
    run_translation_batch()
