package com.liverpool.news.entity;

/**
 * 이적 루머 기사 하나의 진행 단계. INTEREST < NEGOTIATION < CONFIRMED < OFFICIAL 순으로
 * 진전되며, 선언 순서 자체가 진전도를 나타낸다({@link #ordinal()}로 비교, collector/
 * rumor_clusterer.py의 _STAGE_ORDER와 동일한 순서를 유지해야 한다).
 */
public enum StoryStage {
    UNKNOWN,
    INTEREST,
    NEGOTIATION,
    CONFIRMED,
    OFFICIAL
}
