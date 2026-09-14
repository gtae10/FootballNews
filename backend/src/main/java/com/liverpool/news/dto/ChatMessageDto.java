package com.liverpool.news.dto;

/**
 * 클라이언트가 들고 있는 이전 대화 턴 하나. 서버는 대화 이력을 저장하지 않으므로,
 * 매 요청마다 프론트가 직전 턴들을 함께 보낸다({@code role}은 "user" 또는 "assistant").
 */
public record ChatMessageDto(String role, String content) {
}
