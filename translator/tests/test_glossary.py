from glossary import apply_glossary, build_glossary_prompt, FOOTBALL_GLOSSARY


def test_build_glossary_prompt_contains_all_terms():
    prompt = build_glossary_prompt()

    for en, ko in FOOTBALL_GLOSSARY.items():
        assert en in prompt
        assert ko in prompt


def test_apply_glossary_replaces_known_terms():
    text = apply_glossary("They kept a clean sheet after a tough matchday.")

    assert "무실점" in text
    assert "경기일" in text
    assert "clean sheet" not in text.lower()


def test_apply_glossary_is_case_insensitive():
    text = apply_glossary("A great CLEAN SHEET today.")

    assert "무실점" in text


def test_apply_glossary_only_matches_whole_words():
    # "offside"의 부분 문자열인 다른 단어까지 잘못 치환되지 않아야 한다.
    text = apply_glossary("offsider mentioned nothing relevant.")

    assert "오프사이드" not in text


def test_apply_glossary_leaves_text_without_terms_unchanged():
    text = "리버풀이 승리했습니다."

    assert apply_glossary(text) == text
