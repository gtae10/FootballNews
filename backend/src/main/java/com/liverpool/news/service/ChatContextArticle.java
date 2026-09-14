package com.liverpool.news.service;

import java.time.LocalDateTime;

/**
 * RAG 프롬프트에 넣을 기사 컨텍스트 한 건. API로 노출되는 값이 아니라 서비스 내부에서만
 * 쓰이므로 dto가 아니라 service 패키지에 둔다.
 */
public record ChatContextArticle(
        Long id,
        String title,
        String excerpt,
        String source,
        Integer sourceTier,
        LocalDateTime publishedAt,
        String rumorStage,
        Boolean crossReported,
        Integer independentSourceCount
) {
}
