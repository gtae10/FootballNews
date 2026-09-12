import pytest
from unittest.mock import MagicMock, patch

import db
from translate import TranslationResult, translate_article, run_translation_batch


def _article(id, title_original="Title", content_original="Content", **overrides):
    """db.UntranslatedArticle을 만드는 헬퍼 — 우선순위 정렬용 필드는 기본값(None)으로
    두고 필요한 것만 덮어쓴다."""
    return db.UntranslatedArticle(
        id=id, title_original=title_original, content_original=content_original, **overrides
    )


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
    article = _article(1, "A", "B")
    mock_db.fetch_untranslated_articles.return_value = [article]
    mock_db.count_translated_today.return_value = 0
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
    mock_db.count_translated_today.return_value = 0
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


@pytest.mark.parametrize("blank_content", ["", "   ", None])
@patch("argos_engine.translate")
def test_translate_article_raises_without_calling_engine_when_content_is_blank(
    mock_argos_translate, blank_content
):
    """content_original이 비어 있으면(라이브 블로그 등 RSS summary 자체가 없는 경우)
    엔진을 호출하지 않고 바로 실패한다 — 본문 없이 호출하면 거부 응답이나
    제목만 보고 지어낸 요약(할루시네이션)이 저장되는 문제가 실제로 있었다."""
    with pytest.raises(ValueError):
        translate_article("Title", blank_content)

    mock_argos_translate.assert_not_called()


@patch("translate.db")
@patch("argos_engine.translate")
def test_run_translation_batch_skips_article_with_blank_content(mock_argos_translate, mock_db):
    """본문이 비어 있는 기사는 실패로 처리되어 저장되지 않고, status는 COLLECTED로
    남는다(다음 배치에서 본문이 채워지면 재시도됨) — 나머지 기사는 정상 처리."""
    blank_article = _article(1, "A", "")
    ok_article = _article(2, "C", "D")
    mock_db.fetch_untranslated_articles.return_value = [blank_article, ok_article]
    mock_db.count_translated_today.return_value = 0
    mock_db.get_engine.return_value = "engine"
    mock_argos_translate.return_value = ("제목", "요약", "argos-translate-en-ko")

    count = run_translation_batch()

    assert count == 1
    mock_db.save_translation.assert_called_once()
    _, saved_article_id, _ = mock_db.save_translation.call_args[0]
    assert saved_article_id == 2
    mock_argos_translate.assert_called_once()


@patch("translate.db")
@patch("argos_engine.translate")
def test_run_translation_batch_skips_failed_article_and_keeps_processing(
    mock_argos_translate, mock_db
):
    """한 기사의 번역이 실패해도 나머지 기사는 계속 처리되고, 실패한 기사는
    저장되지 않아 status가 COLLECTED로 남는다(다음 배치에서 재시도 대상)."""
    failing_article = _article(1, "A", "B")
    ok_article = _article(2, "C", "D")
    mock_db.fetch_untranslated_articles.return_value = [failing_article, ok_article]
    mock_db.count_translated_today.return_value = 0
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


@patch("translate.DAILY_TRANSLATION_LIMIT", 2)
@patch("translate.db")
@patch("argos_engine.translate")
def test_run_translation_batch_processes_highest_priority_first_within_daily_limit(
    mock_argos_translate, mock_db
):
    """하루 한도를 넘는 기사는 우선순위가 낮은 순서로 이월되고(COLLECTED 유지),
    한도 안에 든 기사는 우선순위가 높은 순서(tier=1 매체가 최신순보다 우선)로
    처리된다."""
    top_tier = _article(1, "Top tier", "content", source_tier=1)
    trusted_reporter = _article(2, "Trusted reporter", "content", quoted_reporter="Fabrizio Romano")
    ordinary_old = _article(3, "Ordinary old", "content")
    ordinary_new = _article(4, "Ordinary new", "content")
    # fetch_untranslated_articles가 반환하는 순서 자체는 우선순위와 무관하게 뒤섞여 있다고 가정.
    mock_db.fetch_untranslated_articles.return_value = [
        ordinary_new, ordinary_old, trusted_reporter, top_tier
    ]
    mock_db.count_translated_today.return_value = 0
    mock_db.get_engine.return_value = "engine"
    mock_argos_translate.return_value = ("제목", "요약", "argos-translate-en-ko")

    count = run_translation_batch()

    # DAILY_TRANSLATION_LIMIT=2이므로 top_tier/trusted_reporter만 처리되고
    # ordinary 기사 둘은 이번 배치에서 아예 시도되지 않아야 한다(이월).
    assert count == 2
    processed_ids = {call.args[1] for call in mock_db.save_translation.call_args_list}
    assert processed_ids == {1, 2}


@patch("translate.DAILY_TRANSLATION_LIMIT", 1)
@patch("translate.db")
@patch("argos_engine.translate")
def test_run_translation_batch_respects_already_translated_today_count(
    mock_argos_translate, mock_db
):
    """오늘 이미 한도만큼 처리했다면(다른 스케줄러 사이클에서), 이번 실행은
    추가로 아무것도 처리하지 않아야 한다 — 하루 한도는 프로세스 하나가 아니라
    하루 전체 기준이다."""
    article = _article(1, "A", "B")
    mock_db.fetch_untranslated_articles.return_value = [article]
    mock_db.count_translated_today.return_value = 1  # 이미 한도(1) 소진
    mock_db.get_engine.return_value = "engine"

    count = run_translation_batch()

    assert count == 0
    mock_argos_translate.assert_not_called()
    mock_db.save_translation.assert_not_called()


@patch("translate.CARRYOVER_WARNING_THRESHOLD", 1)
@patch("translate.DAILY_TRANSLATION_LIMIT", 1)
@patch("translate.db")
@patch("argos_engine.translate")
def test_run_translation_batch_warns_when_carryover_exceeds_threshold(
    mock_argos_translate, mock_db, capsys
):
    """이월 건수가 임계값을 넘으면 경고 로그를 남긴다."""
    mock_db.fetch_untranslated_articles.return_value = [
        _article(1, "A", "B"), _article(2, "C", "D"), _article(3, "E", "F")
    ]
    mock_db.count_translated_today.return_value = 0
    mock_db.get_engine.return_value = "engine"
    mock_argos_translate.return_value = ("제목", "요약", "argos-translate-en-ko")

    run_translation_batch()

    captured = capsys.readouterr()
    assert "[WARNING]" in captured.out
    assert "이월" in captured.out


@patch("translate.CARRYOVER_WARNING_THRESHOLD", 100)
@patch("translate.DAILY_TRANSLATION_LIMIT", 10)
@patch("translate.db")
@patch("argos_engine.translate")
def test_run_translation_batch_does_not_warn_when_carryover_within_threshold(
    mock_argos_translate, mock_db, capsys
):
    mock_db.fetch_untranslated_articles.return_value = [_article(1, "A", "B")]
    mock_db.count_translated_today.return_value = 0
    mock_db.get_engine.return_value = "engine"
    mock_argos_translate.return_value = ("제목", "요약", "argos-translate-en-ko")

    run_translation_batch()

    captured = capsys.readouterr()
    assert "[WARNING]" not in captured.out
