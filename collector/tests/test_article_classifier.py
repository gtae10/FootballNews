from article_classifier import classify_category


def test_classify_returns_transfer_when_already_clustered_regardless_of_keywords():
    """rumor_thread에 이미 묶인 기사는 최우선으로 TRANSFER — 경기 키워드가 섞여 있어도
    (예: 배경 설명에 "match" 언급) 클러스터링 신호를 우선한다."""
    title = "Liverpool set to complete Isak transfer before next match"
    content = "The move is expected to be announced this week."
    assert classify_category(title, content, is_transfer_clustered=True) == "TRANSFER"


def test_classify_match_report_as_match():
    title = "Match report: Liverpool 3-1 Arsenal"
    content = "Goals from Salah and Nunez sealed the win at Anfield."
    assert classify_category(title, content, is_transfer_clustered=False) == "MATCH"


def test_classify_score_pattern_in_title_as_match():
    title = "Liverpool 2-0 Chelsea: player ratings"
    content = "A dominant display from the hosts."
    assert classify_category(title, content, is_transfer_clustered=False) == "MATCH"


def test_classify_highlights_as_match():
    title = "Watch: Liverpool vs Newcastle highlights"
    content = "All the goals from a thrilling encounter."
    assert classify_category(title, content, is_transfer_clustered=False) == "MATCH"


def test_classify_injury_news_as_player():
    title = "Salah ruled out for three weeks with hamstring injury"
    content = "The forward will miss the upcoming fixtures."
    assert classify_category(title, content, is_transfer_clustered=False) == "PLAYER"


def test_classify_award_news_as_player():
    title = "Van Dijk named Premier League player of the month"
    content = "The defender picked up the award after a string of clean sheets."
    assert classify_category(title, content, is_transfer_clustered=False) == "PLAYER"


def test_classify_contract_extension_as_player():
    title = "Alexander-Arnold signs new contract extension with Liverpool"
    content = "The full-back has committed his future to the club."
    assert classify_category(title, content, is_transfer_clustered=False) == "PLAYER"


def test_classify_unclustered_transfer_keyword_as_transfer():
    """이적 키워드는 있지만(예: 구단 미태깅으로) 아직 rumor_thread에 묶이지 않은 단발성
    기사도 TRANSFER로 분류된다."""
    title = "Liverpool linked with surprise move for Serie A striker"
    content = "Reports in Italy suggest interest from Merseyside."
    assert classify_category(title, content, is_transfer_clustered=False) == "TRANSFER"


def test_classify_falls_back_to_other_when_nothing_matches():
    title = "Premier League announces new broadcast deal"
    content = "The league-wide announcement does not mention any specific club or player."
    assert classify_category(title, content, is_transfer_clustered=False) == "OTHER"


def test_classify_match_keyword_takes_priority_over_player_keyword_when_both_present():
    """MATCH가 PLAYER보다 먼저 검사되므로, 두 키워드가 함께 있으면 MATCH로 분류된다
    (예: 경기 리포트에 부상 소식이 곁들여진 경우)."""
    title = "Match report: Liverpool win despite Salah injury scare"
    content = "The winger was withdrawn as a precaution after full time."
    assert classify_category(title, content, is_transfer_clustered=False) == "MATCH"


# 2026-09-06 실제 DB(370건)에 소급 적용했을 때 OTHER가 78%(289건)로 나와 표본을 훑어
# 보강한 키워드들. 아래 테스트는 그 표본에서 실제로 나왔던 제목 패턴을 그대로 쓴다.


def test_classify_preview_as_match():
    title = "Liverpool vs Newcastle preview"
    content = "Everything you need to know ahead of kick-off."
    assert classify_category(title, content, is_transfer_clustered=False) == "MATCH"


def test_classify_predicted_lineup_as_match():
    title = "Predicted lineup: Liverpool vs Newcastle"
    content = "How Arne Slot could set his side up this weekend."
    assert classify_category(title, content, is_transfer_clustered=False) == "MATCH"


def test_classify_matchday_squad_as_match():
    title = "Andoni Iraola explains why Chiesa and Elliott didn't make Liverpool matchday squad"
    content = "The pair were left out of the squad entirely."
    assert classify_category(title, content, is_transfer_clustered=False) == "MATCH"


def test_classify_how_to_watch_as_match():
    title = "How to watch Liverpool vs Newcastle: TV channel and kick-off time"
    content = "Everything you need to follow the game."
    assert classify_category(title, content, is_transfer_clustered=False) == "MATCH"


def test_classify_reaction_as_match():
    title = "Champions League Reaction"
    content = "The panel breaks down last night's game."
    assert classify_category(title, content, is_transfer_clustered=False) == "MATCH"


def test_classify_returns_to_training_as_player():
    title = "Salah returns to training ahead of Newcastle clash"
    content = "The forward has recovered from his hamstring issue."
    assert classify_category(title, content, is_transfer_clustered=False) == "PLAYER"


def test_classify_man_of_the_match_as_player():
    title = "Virgil van Dijk named man of the match"
    content = "The defender was outstanding at the back."
    assert classify_category(title, content, is_transfer_clustered=False) == "PLAYER"


def test_classify_transfer_target_keyword_as_transfer():
    title = "Report: Euro giants prepare for exit of 'incredible' Liverpool target"
    content = "The player is seen as a long-standing transfer target."
    assert classify_category(title, content, is_transfer_clustered=False) == "TRANSFER"


def test_classify_confirms_move_as_transfer():
    title = "He's coming to Liverpool, unexpected person confirms move for superstar"
    content = "The move has now been confirmed by a club insider."
    assert classify_category(title, content, is_transfer_clustered=False) == "TRANSFER"
