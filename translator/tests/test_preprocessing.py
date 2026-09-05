from preprocessing import remove_noise, split_into_translatable_chunks


def test_remove_noise_strips_read_more():
    assert remove_noise("Big news today. Read more...") == "Big news today."


def test_remove_noise_strips_read_more_case_insensitively():
    assert "READ MORE" not in remove_noise("Big news. READ MORE...")


def test_remove_noise_strips_truncation_char_count_marker():
    assert remove_noise("Liverpool sign new star [+1234 chars]") == "Liverpool sign new star"


def test_remove_noise_collapses_excessive_ellipsis():
    result = remove_noise("The transfer saga continues....")
    assert "...." not in result


def test_remove_noise_collapses_whitespace():
    assert remove_noise("Hello   world  \n  today") == "Hello world today"


def test_remove_noise_leaves_clean_text_unchanged():
    assert remove_noise("Liverpool won the match.") == "Liverpool won the match."


def test_split_keeps_short_sentence_as_single_chunk():
    text = "Liverpool won the match."
    assert split_into_translatable_chunks(text) == ["Liverpool won the match."]


def test_split_keeps_each_short_sentence_separate():
    text = "Liverpool won. Arsenal lost."
    assert split_into_translatable_chunks(text) == ["Liverpool won.", "Arsenal lost."]


def test_split_breaks_long_sentence_at_conjunction():
    long_sentence = (
        "Liverpool have completed the signing of a new striker after weeks of "
        "negotiation with the selling club, and the player is expected to make "
        "his debut this weekend against a tough opponent in the league."
    )
    assert len(long_sentence.split()) > 20

    chunks = split_into_translatable_chunks(long_sentence, max_words=20)

    assert len(chunks) == 2
    assert chunks[0].endswith("selling club")
    assert chunks[1].startswith("and the player")


def test_split_leaves_long_sentence_whole_when_no_boundary_found():
    long_sentence = " ".join(["word"] * 45) + "."
    chunks = split_into_translatable_chunks(long_sentence)

    assert chunks == [long_sentence]


def test_split_returns_empty_list_for_empty_text():
    assert split_into_translatable_chunks("") == []
