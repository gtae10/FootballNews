from club_matcher import build_alias_map, detect_clubs

CLUBS = [
    {"id": 1, "name": "Liverpool", "league": "EPL"},
    {"id": 4, "name": "Manchester United", "league": "EPL"},
    {"id": 31, "name": "Nice", "league": "LIGUE_1"},
]


def test_build_alias_map_includes_official_name_and_known_aliases():
    alias_map = build_alias_map(CLUBS)

    assert "Liverpool" in alias_map["Liverpool"]
    assert "Man United" in alias_map["Manchester United"]
    assert "MUFC" in alias_map["Manchester United"]


def test_detect_clubs_matches_single_club_by_official_name():
    alias_map = build_alias_map(CLUBS)

    result = detect_clubs("Liverpool are closing in on a new signing.", alias_map)

    assert result == ["Liverpool"]


def test_detect_clubs_matches_alias():
    alias_map = build_alias_map(CLUBS)

    result = detect_clubs("Man United have made an approach for the striker.", alias_map)

    assert result == ["Manchester United"]


def test_detect_clubs_matches_multiple_clubs_mentioned_together():
    alias_map = build_alias_map(CLUBS)

    result = detect_clubs(
        "Liverpool reignite interest as Manchester United also enter the race.", alias_map
    )

    assert result == ["Liverpool", "Manchester United"]


def test_detect_clubs_returns_empty_list_when_no_club_mentioned():
    alias_map = build_alias_map(CLUBS)

    result = detect_clubs("The Premier League announces a new broadcast deal.", alias_map)

    assert result == []


def test_detect_clubs_is_case_sensitive_to_avoid_common_word_false_positives():
    """구단명이 흔한 영어 단어와 겹치는 경우(Nice) 소문자 사용은 매칭하지 않는다."""
    alias_map = build_alias_map(CLUBS)

    assert detect_clubs("It would be nice to sign a new striker.", alias_map) == []
    assert detect_clubs("Nice are chasing a new striker.", alias_map) == ["Nice"]
