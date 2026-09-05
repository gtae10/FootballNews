from unittest.mock import patch

import pytest

import argos_engine


def test_is_model_installed_returns_false_when_language_pair_missing():
    with patch("argos_engine.argostranslate.translate.get_installed_languages", return_value=[]):
        assert argos_engine.is_model_installed() is False


def test_is_model_installed_returns_true_when_en_to_ko_available():
    ko_lang = type("Lang", (), {"code": "ko"})()
    translation = type("Translation", (), {"to_lang": ko_lang})()
    en_lang = type("Lang", (), {"code": "en", "translations_from": [translation]})()

    with patch("argos_engine.argostranslate.translate.get_installed_languages", return_value=[en_lang]):
        assert argos_engine.is_model_installed() is True


@patch("argos_engine.is_model_installed", return_value=False)
def test_translate_raises_clear_error_when_model_not_installed(mock_installed):
    with pytest.raises(RuntimeError, match="setup_argos_model.py"):
        argos_engine.translate("Title", "Content")


@patch("argos_engine.argostranslate.translate.translate")
@patch("argos_engine.is_model_installed", return_value=True)
def test_translate_returns_title_and_content_translated_via_argos(mock_installed, mock_translate):
    mock_translate.side_effect = ["번역된 제목", "번역된 본문"]

    title_ko, content_ko, model_version = argos_engine.translate("Title", "Content")

    assert title_ko == "번역된 제목"
    assert content_ko == "번역된 본문"
    assert model_version == argos_engine.MODEL_VERSION
    mock_translate.assert_any_call("Title", "en", "ko")
    mock_translate.assert_any_call("Content", "en", "ko")
