package com.liverpool.news.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

/**
 * 채팅 위젯에서 오간 질문/답변을 검토용으로 남겨두는 로그. 로그인이 없어 사용자를
 * 구분하지 않고, 실시간 대화 자체는 서버에 영구 저장하지 않는다(클라이언트 state만).
 * 이 테이블은 그와 별개로 "나중에 검토용"으로만 쓴다.
 */
@Entity
@Table(name = "chat_feedback")
public class ChatFeedback {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_message", nullable = false, columnDefinition = "TEXT")
    private String userMessage;

    @Column(name = "bot_response", nullable = false, columnDefinition = "TEXT")
    private String botResponse;

    // RAG 검색으로 컨텍스트에 넣은 기사 수. 0이면 "관련 기사를 찾지 못했습니다"로
    // 답했을 가능성이 높다는 뜻이라 — 검토 시 이 값으로 빠르게 걸러볼 수 있다.
    @Column(name = "matched_article_count", nullable = false)
    private int matchedArticleCount;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    protected ChatFeedback() {
    }

    public ChatFeedback(String userMessage, String botResponse, int matchedArticleCount) {
        this.userMessage = userMessage;
        this.botResponse = botResponse;
        this.matchedArticleCount = matchedArticleCount;
        this.createdAt = LocalDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public String getUserMessage() {
        return userMessage;
    }

    public String getBotResponse() {
        return botResponse;
    }

    public int getMatchedArticleCount() {
        return matchedArticleCount;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
}
