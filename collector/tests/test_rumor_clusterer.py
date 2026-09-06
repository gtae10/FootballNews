from datetime import datetime, timedelta

from sqlalchemy import create_engine, text

from rumor_clusterer import cluster_article, detect_story_stage


def _make_engine():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    published_at TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE rumor_threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT,
                    club_name TEXT,
                    latest_stage TEXT,
                    independent_source_count INTEGER,
                    cross_reported INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE rumor_thread_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rumor_thread_id INTEGER,
                    article_id INTEGER,
                    story_stage TEXT
                )
                """
            )
        )
    return engine


def _insert_article(connection, source: str, published_at: datetime) -> int:
    result = connection.execute(
        text("INSERT INTO articles (source, published_at) VALUES (:source, :published_at)"),
        {"source": source, "published_at": published_at},
    )
    return result.lastrowid


def _thread_row(connection, thread_id: int):
    return connection.execute(
        text("SELECT * FROM rumor_threads WHERE id = :id"), {"id": thread_id}
    ).first()


def _all_threads(connection):
    return connection.execute(text("SELECT * FROM rumor_threads")).all()


BASE_TIME = datetime(2026, 8, 28, 9, 0)


def test_cluster_article_creates_new_thread_for_first_article():
    engine = _make_engine()
    with engine.begin() as connection:
        article_id = _insert_article(connection, "The Anfield Wrap", BASE_TIME)

        thread_ids = cluster_article(
            connection, article_id, BASE_TIME, ["Alexander Isak"], ["Liverpool"], "INTEREST"
        )

        assert len(thread_ids) == 1
        thread = _thread_row(connection, thread_ids[0])
        assert thread.player_name == "Alexander Isak"
        assert thread.club_name == "Liverpool"
        assert thread.latest_stage == "INTEREST"


def test_cluster_article_joins_existing_thread_when_same_player_and_club_within_window():
    engine = _make_engine()
    with engine.begin() as connection:
        first_id = _insert_article(connection, "The Anfield Wrap", BASE_TIME)
        first_thread_ids = cluster_article(
            connection, first_id, BASE_TIME, ["Isak"], ["Liverpool"], "INTEREST"
        )

        second_time = BASE_TIME + timedelta(days=2)
        second_id = _insert_article(connection, "Fabrizio Romano", second_time)
        second_thread_ids = cluster_article(
            connection, second_id, second_time, ["Isak"], ["Liverpool"], "CONFIRMED"
        )

        assert second_thread_ids == first_thread_ids
        assert len(_all_threads(connection)) == 1


def test_cluster_article_creates_separate_thread_for_different_club():
    """같은 선수라도 구단이 다르면 다른 이적 건이므로 별도 스레드로 분리된다."""
    engine = _make_engine()
    with engine.begin() as connection:
        first_id = _insert_article(connection, "The Anfield Wrap", BASE_TIME)
        cluster_article(connection, first_id, BASE_TIME, ["Isak"], ["Liverpool"], "INTEREST")

        second_id = _insert_article(connection, "Sky Sports Football", BASE_TIME)
        cluster_article(connection, second_id, BASE_TIME, ["Isak"], ["Arsenal"], "INTEREST")

        threads = _all_threads(connection)
        assert len(threads) == 2
        assert {t.club_name for t in threads} == {"Liverpool", "Arsenal"}


def test_cluster_article_joins_thread_just_inside_cluster_window():
    """경계 케이스: 14일 이내(13일차)면 같은 스레드로 합류한다."""
    engine = _make_engine()
    with engine.begin() as connection:
        first_id = _insert_article(connection, "The Anfield Wrap", BASE_TIME)
        cluster_article(connection, first_id, BASE_TIME, ["Isak"], ["Liverpool"], "INTEREST")

        later = BASE_TIME + timedelta(days=13)
        second_id = _insert_article(connection, "Sky Sports Football", later)
        cluster_article(connection, second_id, later, ["Isak"], ["Liverpool"], "NEGOTIATION")

        assert len(_all_threads(connection)) == 1


def test_cluster_article_creates_new_thread_when_outside_cluster_window():
    """경계 케이스: 14일을 넘기면(15일차) 별개의 새 건으로 취급해 새 스레드를 만든다."""
    engine = _make_engine()
    with engine.begin() as connection:
        first_id = _insert_article(connection, "The Anfield Wrap", BASE_TIME)
        cluster_article(connection, first_id, BASE_TIME, ["Isak"], ["Liverpool"], "INTEREST")

        later = BASE_TIME + timedelta(days=15)
        second_id = _insert_article(connection, "Sky Sports Football", later)
        cluster_article(connection, second_id, later, ["Isak"], ["Liverpool"], "INTEREST")

        assert len(_all_threads(connection)) == 2


def test_cluster_article_latest_stage_reflects_most_advanced_seen():
    engine = _make_engine()
    with engine.begin() as connection:
        first_id = _insert_article(connection, "The Anfield Wrap", BASE_TIME)
        thread_ids = cluster_article(
            connection, first_id, BASE_TIME, ["Isak"], ["Liverpool"], "CONFIRMED"
        )

        later = BASE_TIME + timedelta(days=1)
        second_id = _insert_article(connection, "Sky Sports Football", later)
        cluster_article(connection, second_id, later, ["Isak"], ["Liverpool"], "INTEREST")

        thread = _thread_row(connection, thread_ids[0])
        assert thread.latest_stage == "CONFIRMED"  # INTEREST가 나중에 와도 단계가 뒤로 가지 않는다


def test_cross_verification_flags_thread_when_two_distinct_sources_within_48h():
    engine = _make_engine()
    with engine.begin() as connection:
        first_id = _insert_article(connection, "The Anfield Wrap", BASE_TIME)
        thread_ids = cluster_article(
            connection, first_id, BASE_TIME, ["Isak"], ["Liverpool"], "INTEREST"
        )

        confirmed_time = BASE_TIME + timedelta(hours=30)
        second_id = _insert_article(connection, "Fabrizio Romano", confirmed_time)
        cluster_article(
            connection, second_id, confirmed_time, ["Isak"], ["Liverpool"], "CONFIRMED"
        )

        thread = _thread_row(connection, thread_ids[0])
        assert thread.independent_source_count == 2
        assert thread.cross_reported == 1


def test_cross_verification_does_not_count_same_source_twice():
    engine = _make_engine()
    with engine.begin() as connection:
        first_id = _insert_article(connection, "The Anfield Wrap", BASE_TIME)
        thread_ids = cluster_article(
            connection, first_id, BASE_TIME, ["Isak"], ["Liverpool"], "INTEREST"
        )

        later = BASE_TIME + timedelta(hours=10)
        second_id = _insert_article(connection, "The Anfield Wrap", later)
        cluster_article(connection, second_id, later, ["Isak"], ["Liverpool"], "INTEREST")

        thread = _thread_row(connection, thread_ids[0])
        assert thread.independent_source_count == 1
        assert thread.cross_reported == 0


def test_cross_verification_ignores_report_outside_48h_window():
    engine = _make_engine()
    with engine.begin() as connection:
        first_id = _insert_article(connection, "The Anfield Wrap", BASE_TIME)
        thread_ids = cluster_article(
            connection, first_id, BASE_TIME, ["Isak"], ["Liverpool"], "INTEREST"
        )

        late = BASE_TIME + timedelta(hours=72)
        second_id = _insert_article(connection, "Fabrizio Romano", late)
        cluster_article(connection, second_id, late, ["Isak"], ["Liverpool"], "CONFIRMED")

        thread = _thread_row(connection, thread_ids[0])
        assert thread.independent_source_count == 1
        assert thread.cross_reported == 0


def test_detect_story_stage_matches_official_keyword():
    assert detect_story_stage("Isak signs for Liverpool", "The deal is completed.") == "OFFICIAL"


def test_detect_story_stage_matches_confirmed_keyword():
    assert detect_story_stage("Isak undergoes medical", "") == "CONFIRMED"


def test_detect_story_stage_matches_negotiation_keyword():
    assert detect_story_stage("Liverpool submit offer for Isak", "") == "NEGOTIATION"


def test_detect_story_stage_matches_interest_keyword():
    assert detect_story_stage("Liverpool linked with Isak", "") == "INTEREST"


def test_detect_story_stage_returns_unknown_when_no_keyword_matches():
    assert detect_story_stage("Isak scores twice for Newcastle", "A dominant display.") == "UNKNOWN"


def test_detect_story_stage_prioritizes_more_advanced_stage_when_multiple_present():
    """배경 설명에 초기 단계 단어("linked")가 섞여 있어도 더 진전된 신호를 우선한다."""
    title = "Isak completes move after being linked with Liverpool for months"
    assert detect_story_stage(title, "") == "OFFICIAL"


# 2026-09-06 카테고리 분류 키워드 보강 시 실제 DB 샘플에서 찾은 단계 키워드 추가분.


def test_detect_story_stage_matches_target_keyword():
    assert detect_story_stage("Report: Euro giants prepare for exit of Liverpool target", "") == "INTEREST"


def test_detect_story_stage_matches_eyeing_keyword():
    assert detect_story_stage("Liverpool eyeing move for Brazilian winger", "") == "INTEREST"


def test_detect_story_stage_matches_on_radar_keyword():
    assert detect_story_stage("Striker on radar as Liverpool weigh up options", "") == "INTEREST"


def test_detect_story_stage_matches_on_the_radar_keyword():
    """"on radar"만 있으면 실제로 가장 흔한 "on THE radar" 표현을 못 잡는다 — 별도로 검증한다."""
    assert detect_story_stage("Trent Alexander-Arnold on the radar for Liverpool return", "") == "INTEREST"


def test_detect_story_stage_matches_talks_keyword():
    assert detect_story_stage("Liverpool open talks to sign teenage prospect", "") == "NEGOTIATION"


def test_detect_story_stage_matches_edging_closer_keyword():
    assert detect_story_stage("Liverpool's deal for winger is edging closer", "") == "NEGOTIATION"


def test_detect_story_stage_matches_swoop_keyword():
    assert detect_story_stage("Liverpool set for swoop for Bundesliga star", "") == "NEGOTIATION"


def test_detect_story_stage_matches_confirms_move_keyword():
    assert detect_story_stage("Club confirms move for long-term target", "") == "OFFICIAL"


def test_detect_story_stage_matches_verbal_agreement_keyword():
    assert detect_story_stage("Player reaches verbal agreement over move", "") == "CONFIRMED"


def test_detect_story_stage_matches_personal_terms_keyword():
    assert detect_story_stage("Liverpool agree personal terms with target", "") == "CONFIRMED"


# 2026-09-06 재분류 결과를 다시 표본 검토해 찾은 2차 보강분.


def test_detect_story_stage_matches_green_light_keyword():
    assert detect_story_stage("Liverpool given green light to sign wonderkid", "") == "NEGOTIATION"


def test_detect_story_stage_matches_set_to_sign_keyword():
    assert detect_story_stage("Journalist confirms Liverpool are set to sign wonderkid", "") == "NEGOTIATION"


def test_detect_story_stage_matches_deal_off_keyword():
    assert detect_story_stage("Report - Deal off: Liverpool collapse agreement", "") == "NEGOTIATION"


def test_detect_story_stage_matches_close_to_joining_keyword():
    assert detect_story_stage("Winger close to joining Liverpool in January", "") == "NEGOTIATION"


def test_detect_story_stage_matches_transfer_deadline_keyword():
    assert detect_story_stage("Gary Neville urges Iraola to act before transfer deadline", "") == "INTEREST"
