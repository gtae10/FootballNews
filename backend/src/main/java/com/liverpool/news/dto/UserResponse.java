package com.liverpool.news.dto;

public record UserResponse(
        Long id,
        String email,
        String nickname,
        boolean onboarded
) {
}
