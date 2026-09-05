package com.liverpool.news.dto;

import java.time.LocalDateTime;
import java.util.List;

public record RumorThreadDetailResponse(
        Long id,
        String playerName,
        String clubName,
        String latestStage,
        Integer independentSourceCount,
        boolean crossReported,
        LocalDateTime createdAt,
        LocalDateTime updatedAt,
        List<RumorThreadArticleResponse> articles
) {
}
