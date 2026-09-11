package com.liverpool.news.dto;

import java.time.LocalDateTime;
import java.util.List;

public record ArticleDetailResponse(
        Long id,
        String titleKo,
        String titleOriginal,
        String contentKo,
        String source,
        String originalUrl,
        LocalDateTime publishedAt,
        LocalDateTime translatedAt,
        Integer sourceTier,
        String imageUrl,
        String category,
        List<String> images
) {
}
