from postprocessing import clean_translation_output


def test_removes_duplicate_particle():
    assert clean_translation_output("리버풀이 이 승리했다") == "리버풀이 승리했다"


def test_fixes_space_before_adjective_ending_in():
    # 실제 Argos Translate 출력에서 관찰된 패턴: "긍정적 인 반응"
    assert clean_translation_output("긍정적 인 반응을 얻었다") == "긍정적인 반응을 얻었다"


def test_fixes_space_before_adjective_ending_da():
    assert clean_translation_output("그는 자랑스럽 다고 말했다") == "그는 자랑스럽다고 말했다"


def test_removes_space_before_punctuation():
    assert clean_translation_output("경기가 끝났다 .") == "경기가 끝났다."


def test_collapses_multiple_spaces():
    assert clean_translation_output("리버풀이    승리했다") == "리버풀이 승리했다"


def test_leaves_clean_text_unchanged():
    text = "리버풀이 승리했습니다."
    assert clean_translation_output(text) == text
