from reporter_detector import detect_quoted_reporter, resolve_source_tier


def test_detect_quoted_reporter_matches_name_near_quote_verb():
    title = "Fabrizio Romano reports Liverpool have agreed a fee"
    content = "The move is close, per the journalist."

    result = detect_quoted_reporter(title, content)

    assert result is not None
    assert result["name"] == "Fabrizio Romano"
    assert result["tier"] == 1


def test_detect_quoted_reporter_matches_alias():
    title = "Romano says the deal is done"
    content = ""

    result = detect_quoted_reporter(title, content)

    assert result["name"] == "Fabrizio Romano"


def test_detect_quoted_reporter_ignores_name_without_quote_verb_nearby():
    title = "Fabrizio Romano attended the match as a spectator"
    content = "No transfer news was discussed in this unrelated paragraph. " * 5

    result = detect_quoted_reporter(title, content)

    assert result is None


def test_detect_quoted_reporter_returns_none_when_no_reporter_mentioned():
    result = detect_quoted_reporter("Liverpool win 3-0", "A comfortable victory at Anfield.")

    assert result is None


def test_detect_quoted_reporter_picks_lowest_tier_when_multiple_matched():
    title = "Paul Joyce reports the deal, IndyKaila claims it happened first"
    content = ""

    result = detect_quoted_reporter(title, content)

    assert result["name"] == "Paul Joyce"
    assert result["tier"] == 1


def test_resolve_source_tier_upgrades_when_detected_tier_is_lower():
    detected = {"name": "Fabrizio Romano", "tier": 1}

    assert resolve_source_tier(3, detected) == 1


def test_resolve_source_tier_does_not_downgrade_when_existing_tier_is_already_better():
    detected = {"name": "IndyKaila", "tier": 2}

    assert resolve_source_tier(1, detected) == 1


def test_resolve_source_tier_uses_detected_tier_when_existing_is_none():
    detected = {"name": "IndyKaila", "tier": 2}

    assert resolve_source_tier(None, detected) == 2


def test_resolve_source_tier_returns_existing_tier_when_nothing_detected():
    assert resolve_source_tier(3, None) == 3
