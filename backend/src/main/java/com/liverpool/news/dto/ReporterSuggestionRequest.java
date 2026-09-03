package com.liverpool.news.dto;

import jakarta.validation.constraints.NotBlank;

public record ReporterSuggestionRequest(
        @NotBlank String twitterHandle,
        String name,
        String league,
        String memo
) {
}
