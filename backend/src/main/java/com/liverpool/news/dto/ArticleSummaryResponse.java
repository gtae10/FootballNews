package com.liverpool.news.dto;

import java.time.LocalDateTime;
import java.util.List;

public record ArticleSummaryResponse(
        Long id,
        String titleKo,
        String source,
        LocalDateTime publishedAt,
        String originalUrl,
        List<String> clubs,
        Integer sourceTier,
        String imageUrl,
        String category
) {
}
