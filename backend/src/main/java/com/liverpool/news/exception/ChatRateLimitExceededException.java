package com.liverpool.news.exception;

public class ChatRateLimitExceededException extends RuntimeException {

    public ChatRateLimitExceededException(String message) {
        super(message);
    }
}
