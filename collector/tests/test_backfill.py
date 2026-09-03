import sys
from unittest.mock import patch

import pytest

import backfill


@patch("backfill.db.save_articles")
@patch("backfill.db.get_engine")
@patch("backfill.collect_from_rss")
def test_run_backfill_collects_from_all_sources_with_max_pages_and_saves(
    mock_collect, mock_get_engine, mock_save
):
    mock_collect.side_effect = lambda name, url, forced_club=None, source_tier=None, max_pages=1, delay_seconds=0: [
        f"article-from-{name}"
    ]
    mock_get_engine.return_value = "engine"
    mock_save.return_value = 7

    saved_count = backfill.run_backfill(max_pages=10)

    assert mock_collect.call_count == len(backfill.RSS_SOURCES)
    for source in backfill.RSS_SOURCES:
        mock_collect.assert_any_call(
            source["name"],
            source["rss_url"],
            forced_club=source.get("forced_club"),
            source_tier=source.get("source_tier"),
            max_pages=10,
            delay_seconds=backfill.REQUEST_DELAY_SECONDS,
        )

    expected_articles = [f"article-from-{source['name']}" for source in backfill.RSS_SOURCES]
    mock_save.assert_called_once_with("engine", expected_articles)
    assert saved_count == 7


@patch("backfill.time.sleep")
@patch("backfill.db.save_articles")
@patch("backfill.db.get_engine")
@patch("backfill.collect_from_rss")
def test_run_backfill_sleeps_between_sources_but_not_after_the_last_one(
    mock_collect, mock_get_engine, mock_save, mock_sleep
):
    mock_collect.return_value = []
    mock_save.return_value = 0

    backfill.run_backfill()

    assert mock_sleep.call_count == len(backfill.RSS_SOURCES) - 1
    mock_sleep.assert_called_with(backfill.REQUEST_DELAY_SECONDS)


@patch("backfill.run_backfill")
def test_main_parses_pages_argument_and_calls_run_backfill(mock_run_backfill, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["backfill.py", "--pages", "8"])

    backfill.main()

    mock_run_backfill.assert_called_once_with(max_pages=8)


@patch("backfill.run_backfill")
def test_main_uses_default_pages_when_not_specified(mock_run_backfill, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["backfill.py"])

    backfill.main()

    mock_run_backfill.assert_called_once_with(max_pages=backfill.DEFAULT_BACKFILL_PAGES)


def test_main_rejects_non_positive_pages(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["backfill.py", "--pages", "0"])

    with pytest.raises(SystemExit):
        backfill.main()
