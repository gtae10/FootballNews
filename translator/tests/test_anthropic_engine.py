"""Claude(Anthropic API) 엔진 테스트. 기본 엔진은 아니지만(translate.py의 ENGINE 참고)
코드와 함께 테스트도 그대로 보존해, 나중에 다시 활성화할 때 회귀가 없는지 검증한다.
"""

import json
from unittest.mock import MagicMock

import anthropic_engine
from glossary import FOOTBALL_GLOSSARY


def _mock_response(payload: dict):
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = json.dumps(payload)

    response = MagicMock()
    response.content = [text_block]
    return response


def test_build_system_prompt_includes_all_glossary_terms():
    prompt = anthropic_engine.build_system_prompt()

    for en, ko in FOOTBALL_GLOSSARY.items():
        assert en in prompt
        assert ko in prompt


def test_translate_sends_glossary_in_system_prompt():
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        {"title_ko": "테스트 제목", "content_ko": "테스트 요약"}
    )

    anthropic_engine.translate("Test Title", "Test content", client=client)

    _, kwargs = client.messages.create.call_args
    for en, ko in FOOTBALL_GLOSSARY.items():
        assert en in kwargs["system"]
        assert ko in kwargs["system"]


def test_translate_parses_json_response_into_tuple():
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        {"title_ko": "번역된 제목", "content_ko": "번역된 요약"}
    )

    title_ko, content_ko, model_version = anthropic_engine.translate(
        "Original Title", "Original content", client=client
    )

    assert title_ko == "번역된 제목"
    assert content_ko == "번역된 요약"
    assert model_version == anthropic_engine.MODEL
