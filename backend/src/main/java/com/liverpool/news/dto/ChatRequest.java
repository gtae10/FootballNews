package com.liverpool.news.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.util.List;

public record ChatRequest(
        @NotBlank(message = "메시지를 입력해주세요.")
        @Size(max = 300, message = "메시지는 300자 이내로 입력해주세요.")
        String message,
        List<ChatMessageDto> history
) {
}
