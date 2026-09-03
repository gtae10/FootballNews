package com.liverpool.news.dto;

import jakarta.validation.constraints.NotBlank;

public record UpdateNicknameRequest(
        @NotBlank String nickname
) {
}
