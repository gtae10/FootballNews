from player_extractor import build_excluded_names, extract_player_candidates

CLUB_ALIAS_MAP = {
    "Liverpool": ["Liverpool"],
    "Manchester United": ["Man United", "Man Utd", "Manchester United", "MUFC"],
    "Newcastle United": ["Newcastle", "Newcastle United"],
}
REPORTER_ALIASES = ["Fabrizio Romano", "Romano", "Paul Joyce"]


def _excluded():
    return build_excluded_names(CLUB_ALIAS_MAP, REPORTER_ALIASES)


def test_extract_player_candidates_finds_single_word_name():
    result = extract_player_candidates("Liverpool step up interest in Isak", _excluded())

    assert result == ["Isak"]


def test_extract_player_candidates_finds_two_word_name():
    result = extract_player_candidates(
        "Liverpool make contact over Alexander Isak transfer", _excluded()
    )

    assert result == ["Alexander Isak"]


def test_extract_player_candidates_prefers_longer_candidate_over_substring():
    result = extract_player_candidates(
        "Alexander Isak wanted by Liverpool this summer", _excluded()
    )

    assert result == ["Alexander Isak"]
    assert "Isak" not in result


def test_extract_player_candidates_excludes_known_club_names():
    result = extract_player_candidates(
        "Manchester United and Newcastle United both chase the striker", _excluded()
    )

    assert result == []


def test_extract_player_candidates_excludes_reporter_names():
    result = extract_player_candidates("Fabrizio Romano reports on the deal", _excluded())

    assert result == []


def test_extract_player_candidates_excludes_competition_names():
    result = extract_player_candidates("Premier League confirms new fixture list", _excluded())

    assert result == []


def test_extract_player_candidates_strips_leading_stopword():
    result = extract_player_candidates("The Isak transfer saga continues", _excluded())

    assert result == ["Isak"]


def test_extract_player_candidates_returns_empty_when_no_capitalized_name():
    result = extract_player_candidates("club confirms new deal today", _excluded())

    assert result == []


def test_build_excluded_names_combines_club_aliases_and_reporters():
    excluded = _excluded()

    assert "Man Utd" in excluded
    assert "Fabrizio Romano" in excluded
