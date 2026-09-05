from glossary import apply_glossary, build_glossary_prompt, FOOTBALL_GLOSSARY, KOREAN_MISTRANSLATION_FIXES


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


def test_apply_glossary_translates_position_terms_left_in_english():
    # 실제 Argos Translate 출력에서 관찰된 사례: "23세의 Midfielder"
    text = apply_glossary("23세의 Midfielder는 매우 행복했다")

    assert "미드필더" in text
    assert "Midfielder" not in text


def test_apply_glossary_fixes_known_korean_mistranslation():
    # Argos가 "transfer window"를 "전송 창"으로 잘못 옮기는 것이 실제로 관찰됐다
    # ("전송"은 데이터 전송이라는 뜻이라 이적과 무관하다).
    text = apply_glossary("리버풀 전송 창 verdict")

    assert "이적 시장" in text
    assert "전송 창" not in text


def test_korean_mistranslation_fixes_contains_transfer_window_case():
    assert "전송 창" in KOREAN_MISTRANSLATION_FIXES
