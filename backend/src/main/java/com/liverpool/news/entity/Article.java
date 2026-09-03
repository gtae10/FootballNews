package com.liverpool.news.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.HashSet;
import java.util.Set;

@Entity
@Table(name = "articles")
public class Article {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String source;

    @Column(name = "original_url", nullable = false, unique = true)
    private String originalUrl;

    @Column(name = "title_original", columnDefinition = "TEXT")
    private String titleOriginal;

    @Column(name = "content_original", columnDefinition = "TEXT")
    private String contentOriginal;

    @Column(name = "published_at")
    private LocalDateTime publishedAt;

    @Column(name = "collected_at")
    private LocalDateTime collectedAt;

    @Enumerated(EnumType.STRING)
    private ArticleStatus status;

    // 기사 하나가 여러 구단을 언급할 수 있어(예: 이적 기사) club 단일 문자열 컬럼 대신
    // 별도 조인 테이블(article_clubs)에 다중 값으로 저장한다 (docs/DB_SCHEMA.md 참고).
    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "article_clubs", joinColumns = @JoinColumn(name = "article_id"))
    @Column(name = "club_name")
    private Set<String> clubs = new HashSet<>();

    @Column(name = "source_tier")
    private Integer sourceTier;

    @Column(name = "quoted_reporter")
    private String quotedReporter;

    protected Article() {
    }

    public Article(String source, String originalUrl, String titleOriginal,
                    String contentOriginal, LocalDateTime publishedAt) {
        this(source, originalUrl, titleOriginal, contentOriginal, publishedAt, new HashSet<>(), null, null);
    }

    public Article(String source, String originalUrl, String titleOriginal,
                    String contentOriginal, LocalDateTime publishedAt,
                    String club, Integer sourceTier) {
        this(source, originalUrl, titleOriginal, contentOriginal, publishedAt,
                club == null ? new HashSet<>() : new HashSet<>(Set.of(club)), sourceTier, null);
    }

    public Article(String source, String originalUrl, String titleOriginal,
                    String contentOriginal, LocalDateTime publishedAt,
                    Set<String> clubs, Integer sourceTier, String quotedReporter) {
        this.source = source;
        this.originalUrl = originalUrl;
        this.titleOriginal = titleOriginal;
        this.contentOriginal = contentOriginal;
        this.publishedAt = publishedAt;
        this.collectedAt = LocalDateTime.now();
        this.status = ArticleStatus.COLLECTED;
        this.clubs = clubs == null ? new HashSet<>() : clubs;
        this.sourceTier = sourceTier;
        this.quotedReporter = quotedReporter;
    }

    public Long getId() {
        return id;
    }

    public String getSource() {
        return source;
    }

    public String getOriginalUrl() {
        return originalUrl;
    }

    public String getTitleOriginal() {
        return titleOriginal;
    }

    public String getContentOriginal() {
        return contentOriginal;
    }

    public LocalDateTime getPublishedAt() {
        return publishedAt;
    }

    public LocalDateTime getCollectedAt() {
        return collectedAt;
    }

    public ArticleStatus getStatus() {
        return status;
    }

    public void setStatus(ArticleStatus status) {
        this.status = status;
    }

    public Set<String> getClubs() {
        return clubs;
    }

    public Integer getSourceTier() {
        return sourceTier;
    }

    public String getQuotedReporter() {
        return quotedReporter;
    }

    public enum ArticleStatus {
        COLLECTED, TRANSLATED, PUBLISHED
    }
}
