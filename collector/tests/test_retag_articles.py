from sqlalchemy import create_engine, text

from retag_articles import (
    UNTAGGED_LABEL,
    retag_all_articles_for_new_aliases,
    retag_untagged_articles,
)


def _make_engine():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    original_url TEXT UNIQUE,
                    title_original TEXT,
                    content_original TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE article_clubs (
                    article_id INTEGER,
                    club_name TEXT,
                    PRIMARY KEY (article_id, club_name)
                )
                """
            )
        )
    return engine


def _insert_article(engine, source, title, content):
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO articles (source, original_url, title_original, content_original)
                VALUES (:source, :url, :title, :content)
                """
            ),
            {
                "source": source,
                "url": f"https://example.com/{title}",
                "title": title,
                "content": content,
            },
        )
        return result.lastrowid


_ALIAS_MAP = {"Liverpool": ["Liverpool"], "Arsenal": ["Arsenal"]}


def _club_names(engine, article_id):
    with engine.begin() as connection:
        rows = connection.execute(
            text("SELECT club_name FROM article_clubs WHERE article_id = :id ORDER BY club_name"),
            {"id": article_id},
        ).all()
    return [row.club_name for row in rows]


def test_retags_article_from_content_when_untagged():
    engine = _make_engine()
    article_id = _insert_article(
        engine, "Sky Sports Football", "Liverpool sign new midfielder", "Liverpool completed the deal."
    )

    counts = retag_untagged_articles(engine, _ALIAS_MAP)

    assert _club_names(engine, article_id) == ["Liverpool"]
    assert counts["Liverpool"] == 1


def test_applies_forced_club_for_liverpool_fan_sites_even_without_club_mention():
    engine = _make_engine()
    article_id = _insert_article(
        engine, "Anfield Watch", "Big news from the club today", "The Reds are set for a busy window."
    )

    counts = retag_untagged_articles(engine, _ALIAS_MAP)

    assert _club_names(engine, article_id) == ["Liverpool"]
    assert counts["Liverpool"] == 1


def test_detects_multiple_clubs_from_content():
    engine = _make_engine()
    article_id = _insert_article(
        engine,
        "Sky Sports Football",
        "Liverpool reignite interest in Arsenal target",
        "Liverpool and Arsenal are both chasing the same midfielder.",
    )

    retag_untagged_articles(engine, _ALIAS_MAP)

    assert _club_names(engine, article_id) == ["Arsenal", "Liverpool"]


def test_counts_articles_with_no_detected_club_as_untagged():
    engine = _make_engine()
    _insert_article(
        engine, "Football365", "Premier League announces new broadcast deal", "No specific club mentioned."
    )

    counts = retag_untagged_articles(engine, _ALIAS_MAP)

    assert counts[UNTAGGED_LABEL] == 1


def test_does_not_touch_articles_that_already_have_tags():
    engine = _make_engine()
    article_id = _insert_article(
        engine, "Sky Sports Football", "Liverpool sign new midfielder", "Liverpool completed the deal."
    )
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO article_clubs (article_id, club_name) VALUES (:id, 'Chelsea')"),
            {"id": article_id},
        )

    counts = retag_untagged_articles(engine, _ALIAS_MAP)

    assert _club_names(engine, article_id) == ["Chelsea"]
    assert counts == {}


def test_retag_all_adds_missing_club_to_article_that_already_has_a_different_tag():
    """새 별칭 도입 후 전체 재태깅은, 이미 다른 구단이 태깅된 기사에도 새로
    인식되는 구단을 추가로 붙인다(retag_untagged_articles와의 핵심 차이)."""
    engine = _make_engine()
    article_id = _insert_article(
        engine,
        "Football365",
        "Champions League power ranking",
        "Roma, Betis, Fenerbahce are this week's dark horses.",
    )
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO article_clubs (article_id, club_name) VALUES (:id, 'AS Roma')"),
            {"id": article_id},
        )
    alias_map = {**_ALIAS_MAP, "AS Roma": ["AS Roma", "Roma"], "Real Betis": ["Real Betis", "Betis"]}

    counts = retag_all_articles_for_new_aliases(engine, alias_map)

    assert _club_names(engine, article_id) == ["AS Roma", "Real Betis"]
    assert counts == {"Real Betis": 1}


def test_retag_all_is_idempotent_when_run_again():
    engine = _make_engine()
    article_id = _insert_article(
        engine, "Sky Sports Football", "Liverpool sign new midfielder", "Liverpool completed the deal."
    )

    retag_all_articles_for_new_aliases(engine, _ALIAS_MAP)
    counts = retag_all_articles_for_new_aliases(engine, _ALIAS_MAP)

    assert _club_names(engine, article_id) == ["Liverpool"]
    assert counts == {}
