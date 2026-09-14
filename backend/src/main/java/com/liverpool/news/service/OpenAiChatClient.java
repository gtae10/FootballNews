package com.liverpool.news.service;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.liverpool.news.exception.ChatServiceException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.util.List;

/**
 * OpenAI Chat Completions API를 호출하는 얇은 클라이언트. translator/openai_engine.py와
 * 같은 역할을 백엔드(Java)에서 수행한다 — collector/translator가 Python openai SDK를
 * 쓰는 것과 달리, 백엔드엔 별도 OpenAI SDK를 새로 들이지 않고 Spring 6.1(Boot 3.3)에
 * 이미 포함된 {@link RestClient}로 REST 호출 몇 줄로 충분하다.
 */
@Component
public class OpenAiChatClient {

    private final RestClient restClient;
    private final String apiKey;
    private final String model;
    private final int maxTokens;

    public OpenAiChatClient(
            @Value("${app.openai.api-key:}") String apiKey,
            @Value("${app.chat.model:gpt-5-mini}") String model,
            @Value("${app.chat.max-tokens:500}") int maxTokens
    ) {
        this.apiKey = apiKey;
        this.model = model;
        this.maxTokens = maxTokens;
        this.restClient = RestClient.builder()
                .baseUrl("https://api.openai.com/v1")
                .build();
    }

    public String chat(List<Message> messages) {
        if (apiKey == null || apiKey.isBlank()) {
            throw new ChatServiceException("OPENAI_API_KEY가 설정되지 않았습니다.");
        }

        ChatCompletionResponse response;
        try {
            response = restClient.post()
                    .uri("/chat/completions")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + apiKey)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(new ChatCompletionRequest(model, messages, maxTokens))
                    .retrieve()
                    .body(ChatCompletionResponse.class);
        } catch (RestClientException e) {
            throw new ChatServiceException("OpenAI API 호출 실패: " + e.getMessage(), e);
        }

        if (response == null || response.choices() == null || response.choices().isEmpty()) {
            throw new ChatServiceException("OpenAI 응답에 choices가 없습니다.");
        }

        String content = response.choices().get(0).message().content();
        if (content == null || content.isBlank()) {
            throw new ChatServiceException("OpenAI 응답 본문이 비어 있습니다.");
        }
        return content.trim();
    }

    public record Message(String role, String content) {
    }

    private record ChatCompletionRequest(
            String model,
            List<Message> messages,
            @JsonProperty("max_completion_tokens") int maxCompletionTokens
    ) {
    }

    private record ChatCompletionResponse(List<Choice> choices) {
        private record Choice(Message message) {
        }
    }
}
