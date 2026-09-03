from unittest.mock import patch

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
