from glossary import build_glossary_prompt, FOOTBALL_GLOSSARY


def test_build_glossary_prompt_contains_all_terms():
    prompt = build_glossary_prompt()

    for en, ko in FOOTBALL_GLOSSARY.items():
        assert en in prompt
        assert ko in prompt
