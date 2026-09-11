from unittest.mock import MagicMock, patch

from translate import TranslationResult, translate_article, run_translation_batch


@patch("argos_engine.translate")
def test_translate_article_uses_argos_engine_by_default(mock_argos_translate):
    mock_argos_translate.return_value = ("번역된 제목", "번역된 요약", "argos-translate-en-ko")

    result = translate_article("Title", "Content")

    assert isinstance(result, TranslationResult)
    assert result.title_ko == "번역된 제목"
    assert result.content_ko == "번역된 요약"
    assert result.model_version == "argos-translate-en-ko"


@patch("argos_engine.translate")
def test_translate_article_cleans_html_before_calling_engine(mock_argos_translate):
    mock_argos_translate.return_value = ("t", "c", "argos-translate-en-ko")

    translate_article("Title", "<p>Content &#8217;s here.</p>")

    _, content_arg = mock_argos_translate.call_args[0]
    assert "<p>" not in content_arg
    assert "&#8217;" not in content_arg
    assert "’s here." in content_arg


@patch("argos_engine.translate")
def test_translate_article_applies_glossary_postprocessing(mock_argos_translate):
    mock_argos_translate.return_value = (
        "clean sheet title",
        "We kept a clean sheet on matchday.",
        "argos-translate-en-ko",
    )

    result = translate_article("Title", "Content")

    assert "무실점" in result.title_ko
    assert "무실점" in result.content_ko
    assert "경기일" in result.content_ko


@patch("translate.db")
@patch("argos_engine.translate")
def test_run_translation_batch_translates_and_saves_each_untranslated_article(
    mock_argos_translate, mock_db
):
    article = MagicMock(id=1, title_original="A", content_original="B")
    mock_db.fetch_untranslated_articles.return_value = [article]
    mock_db.get_engine.return_value = "engine"
    mock_argos_translate.return_value = ("제목", "요약", "argos-translate-en-ko")

    count = run_translation_batch()

    assert count == 1
    mock_db.save_translation.assert_called_once()
    saved_engine, saved_article_id, saved_result = mock_db.save_translation.call_args[0]
    assert saved_engine == "engine"
    assert saved_article_id == 1
    assert saved_result.title_ko == "제목"
    assert saved_result.content_ko == "요약"


@patch("translate.db")
@patch("argos_engine.translate")
def test_run_translation_batch_returns_zero_when_nothing_to_translate(
    mock_argos_translate, mock_db
):
    mock_db.fetch_untranslated_articles.return_value = []
    mock_db.get_engine.return_value = "engine"

    count = run_translation_batch()

    assert count == 0
    mock_argos_translate.assert_not_called()
    mock_db.save_translation.assert_not_called()


@patch("translate.ENGINE", "openai")
@patch("openai_engine.translate")
def test_translate_article_uses_openai_engine_when_selected(mock_openai_translate):
    mock_openai_translate.return_value = ("번역된 제목", "번역된 요약", "gpt-5-mini")

    result = translate_article("Title", "Content")

    assert result.title_ko == "번역된 제목"
    assert result.content_ko == "번역된 요약"
    assert result.model_version == "gpt-5-mini"
    mock_openai_translate.assert_called_once()


@patch("translate.db")
@patch("argos_engine.translate")
def test_run_translation_batch_skips_failed_article_and_keeps_processing(
    mock_argos_translate, mock_db
):
    """한 기사의 번역이 실패해도 나머지 기사는 계속 처리되고, 실패한 기사는
    저장되지 않아 status가 COLLECTED로 남는다(다음 배치에서 재시도 대상)."""
    failing_article = MagicMock(id=1, title_original="A", content_original="B")
    ok_article = MagicMock(id=2, title_original="C", content_original="D")
    mock_db.fetch_untranslated_articles.return_value = [failing_article, ok_article]
    mock_db.get_engine.return_value = "engine"
    mock_argos_translate.side_effect = [
        Exception("일시적인 오류"),
        ("제목", "요약", "argos-translate-en-ko"),
    ]

    count = run_translation_batch()

    assert count == 1
    mock_db.save_translation.assert_called_once()
    _, saved_article_id, _ = mock_db.save_translation.call_args[0]
    assert saved_article_id == 2
