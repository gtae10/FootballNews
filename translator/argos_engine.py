"""Argos Translate(오프라인 오픈소스 NMT) 기반 번역 엔진.

파파고/구글/DeepL은 전부 카드(결제 수단) 등록이 있어야 API 키를 받을 수 있어서,
카드 등록 없이 바로 쓸 수 있는 대안으로 도입했다. `pip install`로 설치하고
언어 모델을 최초 1회만 내려받으면(`setup_argos_model.py`) 이후로는 완전히
오프라인·무료로 번역한다.

품질에 대한 솔직한 트레이드오프: Claude/GPT 같은 LLM 기반 번역(anthropic_engine.py,
openai_engine.py)에 비해 문장이 직역투이고, 축구 특유의 관용구·약어는 어색하게
옮겨지거나 아예 번역되지 않고 영문 그대로 남는 경우가 있다. 후자는
glossary.apply_glossary()로 일부 보정한다. 번역 품질이 더 중요해지면
translate.py의 ENGINE 값만 바꿔 anthropic_engine.py/openai_engine.py(또는
그때 새로 붙일 파파고/DeepL 엔진)로 교체할 수 있도록 이 모듈은 "제목/본문
문자열을 받아 번역 결과 문자열을 반환"하는 좁은 인터페이스만 제공한다.
"""

from typing import Tuple

import argostranslate.package
import argostranslate.translate

from preprocessing import split_into_translatable_chunks

FROM_CODE = "en"
TO_CODE = "ko"
MODEL_VERSION = "argos-translate-en-ko"


def is_model_installed() -> bool:
    """en->ko 번역 모델이 이미 설치돼 있는지 확인한다."""
    installed_languages = argostranslate.translate.get_installed_languages()
    from_lang = next((lang for lang in installed_languages if lang.code == FROM_CODE), None)
    if from_lang is None:
        return False
    return any(t.to_lang.code == TO_CODE for t in from_lang.translations_from)


def _translate_text(text: str) -> str:
    """문장이 길면 접속사/구두점 경계에서 쪼갠 뒤 조각별로 번역해 다시 합친다.

    Argos Translate 같은 문장 단위 NMT는 짧은 문장에서 정확도가 높다는 전제다
    (translator/README.md 참고). 짧은 텍스트는 쪼갤 게 없어 원문 그대로 한 번에
    번역된다.
    """
    chunks = split_into_translatable_chunks(text)
    if not chunks:
        return ""
    translated_chunks = [argostranslate.translate.translate(chunk, FROM_CODE, TO_CODE) for chunk in chunks]
    return " ".join(translated_chunks)


def translate(title_original: str, content_original: str) -> Tuple[str, str, str]:
    """원문 제목/본문을 Argos Translate로 번역해 (title_ko, content_ko, model_version)을 반환한다.

    Claude 엔진과 달리 요약하지 않고 문장 단위 직역에 가깝게 번역한다 — Argos
    Translate 자체가 요약 기능을 제공하지 않기 때문이다(저작권 관련 유의사항은
    docs/LEGAL_NOTES.md 참고. 원문 전문을 그대로 베끼지 않는다는 원칙은 지키되,
    이 프로젝트는 RSS 요약(summary)만 수집하므로 번역 대상 자체가 이미 짧다).
    """
    if not is_model_installed():
        raise RuntimeError(
            f"Argos Translate {FROM_CODE}->{TO_CODE} 모델이 설치되어 있지 않습니다. "
            "먼저 `python setup_argos_model.py`를 실행하세요."
        )

    title_ko = _translate_text(title_original)
    content_ko = _translate_text(content_original)

    return title_ko, content_ko, MODEL_VERSION
