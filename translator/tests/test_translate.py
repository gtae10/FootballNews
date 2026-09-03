import json
from unittest.mock import MagicMock, patch

import translate
from glossary import FOOTBALL_GLOSSARY
from translate import TranslationResult, translate_article, run_translation_batch


def _mock_response(payload: dict):
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = json.dumps(payload)

    response = MagicMock()
    response.content = [text_block]
    return response


def test_build_system_prompt_includes_all_glossary_terms():
    prompt = translate.build_system_prompt()

    for en, ko in FOOTBALL_GLOSSARY.items():
        assert en in prompt
        assert ko in prompt


def test_translate_article_sends_glossary_in_system_prompt():
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        {"title_ko": "테스트 제목", "content_ko": "테스트 요약"}
    )

    translate_article("Test Title", "Test content", client=client)

    _, kwargs = client.messages.create.call_args
    for en, ko in FOOTBALL_GLOSSARY.items():
        assert en in kwargs["system"]
        assert ko in kwargs["system"]


def test_translate_article_parses_json_response_into_result():
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        {"title_ko": "번역된 제목", "content_ko": "번역된 요약"}
    )

    result = translate_article("Original Title", "Original content", client=client)

    assert isinstance(result, TranslationResult)
    assert result.title_ko == "번역된 제목"
    assert result.content_ko == "번역된 요약"
    assert result.model_version == translate.MODEL


@patch("translate.db")
@patch("translate._get_client")
@patch("translate.translate_article")
def test_run_translation_batch_translates_and_saves_each_untranslated_article(
    mock_translate_article, mock_get_client, mock_db
):
    article = MagicMock(id=1, title_original="A", content_original="B")
    mock_db.fetch_untranslated_articles.return_value = [article]
    mock_db.get_engine.return_value = "engine"
    mock_get_client.return_value = "client"
    mock_translate_article.return_value = TranslationResult("제목", "요약", translate.MODEL)

    count = run_translation_batch()

    assert count == 1
    mock_translate_article.assert_called_once_with("A", "B", client="client")
    mock_db.save_translation.assert_called_once_with(
        "engine", 1, mock_translate_article.return_value
    )


@patch("translate.db")
@patch("translate._get_client")
@patch("translate.translate_article")
def test_run_translation_batch_returns_zero_when_nothing_to_translate(
    mock_translate_article, mock_get_client, mock_db
):
    mock_db.fetch_untranslated_articles.return_value = []
    mock_db.get_engine.return_value = "engine"

    count = run_translation_batch()

    assert count == 0
    mock_translate_article.assert_not_called()
    mock_db.save_translation.assert_not_called()
