package com.liverpool.news.exception;

/**
 * OpenAI API 호출 실패(인증 오류, rate limit, 빈 응답 등)를 나타낸다.
 * translator/openai_engine.py의 TranslationError와 같은 역할이다.
 */
public class ChatServiceException extends RuntimeException {

    public ChatServiceException(String message) {
        super(message);
    }

    public ChatServiceException(String message, Throwable cause) {
        super(message, cause);
    }
}
