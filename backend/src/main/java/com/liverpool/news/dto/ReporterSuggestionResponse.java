package com.liverpool.news.dto;

import java.time.LocalDateTime;

public record ReporterSuggestionResponse(
        Long id,
        String twitterHandle,
        String name,
        String league,
        String memo,
        LocalDateTime createdAt
) {
}
