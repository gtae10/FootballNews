package com.liverpool.news.dto;

import java.time.LocalDateTime;

public record RumorThreadArticleResponse(
        Long id,
        String source,
        String titleKo,
        String titleOriginal,
        String originalUrl,
        LocalDateTime publishedAt,
        String storyStage
) {
}
