"""수집된 원문 기사를 번역하는 메인 로직 (엔진 선택 + DB 배치 처리).

기본 엔진은 Argos Translate(오프라인, 무료, 카드 등록 불필요, argos_engine.py)다.
Claude(Anthropic API) 기반 엔진은 anthropic_engine.py에 그대로 보존해뒀다 —
번역 품질이 더 중요해지면 아래 ENGINE 값을 "anthropic"으로 바꾸기만 하면 된다
(이 경우 ANTHROPIC_API_KEY 환경 변수가 필요하다).
"""

from dataclasses import dataclass

import db
from glossary import apply_glossary
from html_cleanup import clean_for_translation
from postprocessing import clean_translation_output
from preprocessing import remove_noise

ENGINE = "argos"  # "argos"(기본, 오프라인/무료) | "anthropic"(Claude API, 유료)


@dataclass
class TranslationResult:
    title_ko: str
    content_ko: str
    model_version: str


def _prepare_input(raw_text: str) -> str:
    """HTML 정리 + RSS 잡음 제거를 순서대로 적용한다 (엔진 공통 전처리)."""
    return remove_noise(clean_for_translation(raw_text))


def translate_article(title_original: str, content_original: str) -> TranslationResult:
    """원문 제목/본문을 번역하고, 전처리(HTML/잡음 제거) + 용어집/문장 후처리를 적용해 반환한다."""
    clean_title = _prepare_input(title_original)
    clean_content = _prepare_input(content_original)

    if ENGINE == "anthropic":
        import anthropic_engine

        title_ko, content_ko, model_version = anthropic_engine.translate(clean_title, clean_content)
    else:
        import argos_engine

        title_ko, content_ko, model_version = argos_engine.translate(clean_title, clean_content)

    return TranslationResult(
        title_ko=clean_translation_output(apply_glossary(title_ko)),
        content_ko=clean_translation_output(apply_glossary(content_ko)),
        model_version=model_version,
    )


def run_translation_batch() -> int:
    """DB에서 미번역 기사(status=COLLECTED)를 조회해 순차적으로 번역하고 저장한다.

    반환값은 번역해 저장한 기사 수다.
    """
    engine = db.get_engine()

    articles = db.fetch_untranslated_articles(engine)
    translated_count = 0
    for article in articles:
        result = translate_article(article.title_original, article.content_original)
        db.save_translation(engine, article.id, result)
        translated_count += 1

    print(f"번역 완료: {translated_count}건 (엔진: {ENGINE})")
    return translated_count


if __name__ == "__main__":
    run_translation_batch()
