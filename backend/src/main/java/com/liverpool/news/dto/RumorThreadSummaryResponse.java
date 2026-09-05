package com.liverpool.news.dto;

import java.time.LocalDateTime;

public record RumorThreadSummaryResponse(
        Long id,
        String playerName,
        String clubName,
        String latestStage,
        Integer independentSourceCount,
        boolean crossReported,
        long articleCount,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {
}
