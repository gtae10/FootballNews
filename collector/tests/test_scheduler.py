from unittest.mock import MagicMock, patch

import scheduler


@patch("scheduler.db.save_articles")
@patch("scheduler.db.get_engine")
@patch("scheduler.collect_from_rss")
def test_run_collection_job_collects_from_all_sources_and_saves(
    mock_collect, mock_get_engine, mock_save
):
    mock_collect.side_effect = lambda name, url, forced_club=None, source_tier=None: [
        f"article-from-{name}"
    ]
    mock_get_engine.return_value = "engine"
    mock_save.return_value = 3

    articles = scheduler.run_collection_job()

    assert mock_collect.call_count == len(scheduler.RSS_SOURCES)
    for source in scheduler.RSS_SOURCES:
        mock_collect.assert_any_call(
            source["name"],
            source["rss_url"],
            forced_club=source.get("forced_club"),
            source_tier=source.get("source_tier"),
        )

    assert articles == [f"article-from-{source['name']}" for source in scheduler.RSS_SOURCES]
    mock_save.assert_called_once_with("engine", articles)


@patch("scheduler.subprocess.run")
def test_run_translation_job_runs_translate_py_in_translator_directory(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="번역 완료: 3건", stderr="")

    scheduler.run_translation_job()

    args, kwargs = mock_run.call_args
    assert args[0] == ["python", "translate.py"]
    assert kwargs["cwd"] == scheduler._TRANSLATOR_DIR


@patch("scheduler.subprocess.run")
def test_run_translation_job_defaults_engine_to_openai_when_unset(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    with patch.dict("scheduler.os.environ", {}, clear=False):
        scheduler.os.environ.pop("TRANSLATOR_ENGINE", None)
        scheduler.run_translation_job()

    _, kwargs = mock_run.call_args
    assert kwargs["env"]["TRANSLATOR_ENGINE"] == "openai"


@patch("scheduler.subprocess.run")
def test_run_translation_job_respects_existing_translator_engine_env_var(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    with patch.dict("scheduler.os.environ", {"TRANSLATOR_ENGINE": "anthropic"}):
        scheduler.run_translation_job()

    _, kwargs = mock_run.call_args
    assert kwargs["env"]["TRANSLATOR_ENGINE"] == "anthropic"


@patch("scheduler.subprocess.run")
def test_run_translation_job_does_not_raise_when_batch_fails(mock_run):
    """번역 배치가 실패해도(네트워크 오류, API 키 누락 등) 예외를 다시 던지지 않는다 —
    수집 스케줄러 자체가 멈추면 안 되기 때문이다."""
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="OPENAI_API_KEY가 없습니다")

    scheduler.run_translation_job()  # 예외 없이 반환되면 통과


@patch("scheduler.run_translation_job")
@patch("scheduler.run_collection_job")
def test_run_collection_and_translation_job_runs_both_in_order(mock_collection, mock_translation):
    scheduler.run_collection_and_translation_job()

    mock_collection.assert_called_once()
    mock_translation.assert_called_once()
