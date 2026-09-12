"""수집된 원문 기사를 번역하는 메인 로직 (엔진 선택 + 우선순위 큐 + DB 배치 처리).

기본 엔진은 Argos Translate(오프라인, 무료, 카드 등록 불필요, argos_engine.py)다.
Claude(Anthropic API) 기반 엔진(anthropic_engine.py)과 GPT(OpenAI API) 기반
엔진(openai_engine.py)도 그대로 선택지로 보존해뒀다 — 번역 품질이 더
중요해지면 아래 ENGINE 값(또는 TRANSLATOR_ENGINE 환경 변수)을 "anthropic" 또는
"openai"로 바꾸기만 하면 된다(각각 ANTHROPIC_API_KEY / OPENAI_API_KEY 환경
변수가 필요하다).

DAILY_TRANSLATION_LIMIT(하루 처리 상한)과 우선순위 정렬(priority.py)은
run_translation_batch()를 참고 — 한도를 넘긴 기사는 버려지지 않고 다음
배치로 자연스럽게 이월된다.
"""

import os
from dataclasses import dataclass

import db
from glossary import apply_glossary
from html_cleanup import clean_for_translation
from postprocessing import clean_translation_output
from preprocessing import remove_noise
from priority import sort_by_priority

# "argos"(기본, 오프라인/무료) | "anthropic"(Claude API, 유료) | "openai"(GPT API, 유료)
ENGINE = os.environ.get("TRANSLATOR_ENGINE", "argos")

# 하루(UTC 기준)에 처리할 번역 건수 상한. 유료 엔진(openai/anthropic) API 비용이
# 무한정 늘어나는 것을 막기 위함이다. 한도를 넘긴 기사는 COLLECTED 상태로 남아
# priority.py의 우선순위대로 다음날(또는 다음 배치)에 이어서 처리된다 — 버려지지
# 않는다. scheduler.py가 30분마다 새 프로세스로 이 스크립트를 실행하므로, 이번
# 실행에서 쓸 수 있는 몫은 db.count_translated_today()로 매번 다시 계산한다.
DAILY_TRANSLATION_LIMIT = int(os.environ.get("DAILY_TRANSLATION_LIMIT", "300"))

# 이월(오늘 처리 못하고 COLLECTED로 남은) 건수가 이 값을 넘으면 경고 로그를 남긴다 —
# DAILY_TRANSLATION_LIMIT이 실제 유입량을 못 따라가고 있다는 신호로 볼 수 있다.
CARRYOVER_WARNING_THRESHOLD = int(os.environ.get("CARRYOVER_WARNING_THRESHOLD", "500"))


@dataclass
class TranslationResult:
    title_ko: str
    content_ko: str
    model_version: str


def _prepare_input(raw_text: str) -> str:
    """HTML 정리 + RSS 잡음 제거를 순서대로 적용한다 (엔진 공통 전처리)."""
    return remove_noise(clean_for_translation(raw_text))


def translate_article(title_original: str, content_original: str) -> TranslationResult:
    """원문 제목/본문을 번역하고, 전처리(HTML/잡음 제거) + 용어집/문장 후처리를 적용해 반환한다.

    content_original이 비어 있으면(RSS summary 자체가 없었던 라이브 블로그 등)
    LLM을 호출하지 않고 바로 실패시킨다 — 본문 없이 호출하면 엔진이 정직하게
    거부하거나, 제목만 보고 그럴듯한 내용을 지어내는(할루시네이션) 경우가 실제로
    확인됐다. run_translation_batch()가 이 예외를 기존 실패 처리 경로로 그대로
    잡아 status를 COLLECTED로 유지한다(본문이 나중에 채워지면 재시도 대상).
    """
    if not content_original or not content_original.strip():
        raise ValueError("content_original이 비어 있어 번역을 건너뜀 (본문 없음)")

    clean_title = _prepare_input(title_original)
    clean_content = _prepare_input(content_original)

    if ENGINE == "anthropic":
        import anthropic_engine

        title_ko, content_ko, model_version = anthropic_engine.translate(clean_title, clean_content)
    elif ENGINE == "openai":
        import openai_engine

        title_ko, content_ko, model_version = openai_engine.translate(clean_title, clean_content)
    else:
        import argos_engine

        title_ko, content_ko, model_version = argos_engine.translate(clean_title, clean_content)

    return TranslationResult(
        title_ko=clean_translation_output(apply_glossary(title_ko)),
        content_ko=clean_translation_output(apply_glossary(content_ko)),
        model_version=model_version,
    )


def run_translation_batch() -> int:
    """DB에서 미번역 기사(status=COLLECTED)를 우선순위대로 조회해 하루 한도까지 번역하고 저장한다.

    처리 순서는 priority.sort_by_priority()를 따른다(대형 매체/신뢰 기자 인용 >
    교차 검증된 이적 루머 > 최신순). DAILY_TRANSLATION_LIMIT을 넘는 기사는 이번
    실행에서 아예 시도하지 않고 COLLECTED 상태 그대로 둔다 — 다음 배치(보통
    다음날)에 우선순위대로 다시 앞에서부터 처리된다.

    한도 안에서 시도한 기사도 번역이 실패하면(인증 에러, rate limit, 빈 응답 등)
    배치 전체를 중단하지 않는다 — 실패한 기사는 status를 COLLECTED로 그대로 두고
    나머지는 계속 처리한다.

    반환값은 번역해 저장한 기사 수다(실패하거나 한도 초과로 이월된 기사는 포함하지 않는다).
    """
    engine = db.get_engine()

    articles = sort_by_priority(db.fetch_untranslated_articles(engine))
    already_translated_today = db.count_translated_today(engine)
    remaining_quota = max(0, DAILY_TRANSLATION_LIMIT - already_translated_today)
    to_process = articles[:remaining_quota]

    translated_count = 0
    for article in to_process:
        try:
            result = translate_article(article.title_original, article.content_original)
        except Exception as exc:
            print(
                f"번역 실패 (기사 id={article.id}, 엔진={ENGINE}): {exc} "
                "— status는 COLLECTED로 유지, 다음 배치에서 재시도됨"
            )
            continue

        db.save_translation(engine, article.id, result)
        translated_count += 1

    carried_over_count = len(articles) - translated_count
    print(f"오늘 처리: {translated_count}건, 이월: {carried_over_count}건 (엔진: {ENGINE})")
    if carried_over_count > CARRYOVER_WARNING_THRESHOLD:
        print(
            f"[WARNING] 이월 건수({carried_over_count}건)가 임계값"
            f"({CARRYOVER_WARNING_THRESHOLD}건)을 초과했습니다 — "
            "DAILY_TRANSLATION_LIMIT 상향 검토 필요"
        )

    return translated_count


if __name__ == "__main__":
    run_translation_batch()
