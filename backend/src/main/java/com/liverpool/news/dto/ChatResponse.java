package com.liverpool.news.dto;

public record ChatResponse(String reply, int matchedArticleCount, String sourceType) {
}
