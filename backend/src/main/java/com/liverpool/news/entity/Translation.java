package com.liverpool.news.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "translations")
public class Translation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne
    @JoinColumn(name = "article_id", nullable = false, unique = true)
    private Article article;

    @Column(name = "title_ko", columnDefinition = "TEXT")
    private String titleKo;

    @Column(name = "content_ko", columnDefinition = "TEXT")
    private String contentKo;

    @Column(name = "model_version")
    private String modelVersion;

    @Column(name = "translated_at")
    private LocalDateTime translatedAt;

    protected Translation() {
    }

    public Translation(Article article, String titleKo, String contentKo, String modelVersion) {
        this.article = article;
        this.titleKo = titleKo;
        this.contentKo = contentKo;
        this.modelVersion = modelVersion;
        this.translatedAt = LocalDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public Article getArticle() {
        return article;
    }

    public String getTitleKo() {
        return titleKo;
    }

    public String getContentKo() {
        return contentKo;
    }

    public String getModelVersion() {
        return modelVersion;
    }

    public LocalDateTime getTranslatedAt() {
        return translatedAt;
    }
}
