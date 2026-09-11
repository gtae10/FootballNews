"""GPT(OpenAI API) 엔진 테스트. 기본 엔진은 아니지만(translate.py의 ENGINE 참고)
코드와 함께 테스트도 그대로 보존해, 나중에 다시 활성화할 때 회귀가 없는지
검증한다. 실제 API를 호출하지 않고 client를 mock으로 주입해 배관만 검증한다.
"""

import json
from unittest.mock import MagicMock

import openai
import pytest

import openai_engine
from glossary import FOOTBALL_GLOSSARY
from openai_engine import TranslationError


def _mock_response(payload: dict):
    message = MagicMock()
    message.content = json.dumps(payload)

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


def test_build_system_prompt_includes_all_glossary_terms():
    prompt = openai_engine.build_system_prompt()

    for en, ko in FOOTBALL_GLOSSARY.items():
        assert en in prompt
        assert ko in prompt


def test_translate_sends_glossary_in_system_prompt():
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_response(
        {"title_ko": "테스트 제목", "content_ko": "테스트 요약"}
    )

    openai_engine.translate("Test Title", "Test content", client=client)

    _, kwargs = client.chat.completions.create.call_args
    system_message = next(m["content"] for m in kwargs["messages"] if m["role"] == "system")
    for en, ko in FOOTBALL_GLOSSARY.items():
        assert en in system_message
        assert ko in system_message


def test_translate_parses_json_response_into_tuple():
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_response(
        {"title_ko": "번역된 제목", "content_ko": "번역된 요약"}
    )

    title_ko, content_ko, model_version = openai_engine.translate(
        "Original Title", "Original content", client=client
    )

    assert title_ko == "번역된 제목"
    assert content_ko == "번역된 요약"
    assert model_version == openai_engine.MODEL


def test_translate_raises_translation_error_on_authentication_failure():
    client = MagicMock()
    client.chat.completions.create.side_effect = openai.AuthenticationError(
        "invalid api key", response=MagicMock(), body=None
    )

    with pytest.raises(TranslationError):
        openai_engine.translate("Title", "Content", client=client)


def test_translate_raises_translation_error_on_rate_limit():
    client = MagicMock()
    client.chat.completions.create.side_effect = openai.RateLimitError(
        "rate limited", response=MagicMock(), body=None
    )

    with pytest.raises(TranslationError):
        openai_engine.translate("Title", "Content", client=client)


def test_translate_raises_translation_error_on_empty_response():
    client = MagicMock()
    message = MagicMock()
    message.content = ""
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    client.chat.completions.create.return_value = response

    with pytest.raises(TranslationError):
        openai_engine.translate("Title", "Content", client=client)


def test_translate_raises_translation_error_on_no_choices():
    client = MagicMock()
    response = MagicMock()
    response.choices = []
    client.chat.completions.create.return_value = response

    with pytest.raises(TranslationError):
        openai_engine.translate("Title", "Content", client=client)


def test_translate_raises_translation_error_on_invalid_json():
    client = MagicMock()
    message = MagicMock()
    message.content = "이건 JSON이 아님"
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    client.chat.completions.create.return_value = response

    with pytest.raises(TranslationError):
        openai_engine.translate("Title", "Content", client=client)


def test_translate_raises_translation_error_on_missing_keys():
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_response({"unexpected": "shape"})

    with pytest.raises(TranslationError):
        openai_engine.translate("Title", "Content", client=client)
