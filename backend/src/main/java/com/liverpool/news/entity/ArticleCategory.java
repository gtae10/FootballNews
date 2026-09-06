package com.liverpool.news.entity;

/**
 * 기사 카테고리. collector가 저장 시점(또는 소급 배치 collector/backfill_categories.py)에
 * 규칙 기반으로 분류해 채운다 — 백엔드는 이 값을 읽어 필터링만 한다
 * (collector/article_classifier.py, collector/category_keywords.py 참고).
 */
public enum ArticleCategory {
    MATCH,
    TRANSFER,
    PLAYER,
    OTHER
}
