package com.liverpool.news.dto;

import java.time.LocalDateTime;

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
        String imageUrl
) {
}
