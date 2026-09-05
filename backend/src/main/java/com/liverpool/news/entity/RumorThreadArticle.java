package com.liverpool.news.entity;

import jakarta.persistence.*;

/**
 * 루머 스레드 ↔ 기사 연결(1건의 기사가 그 스레드 안에서 어느 단계였는지 포함).
 * 한 기사가 여러 선수/구단을 함께 언급하면 여러 스레드에 동시에 연결될 수 있다
 * (collector/rumor_clusterer.py 참고).
 */
@Entity
@Table(name = "rumor_thread_articles")
public class RumorThreadArticle {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "rumor_thread_id", nullable = false)
    private RumorThread rumorThread;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "article_id", nullable = false)
    private Article article;

    @Enumerated(EnumType.STRING)
    @Column(name = "story_stage", nullable = false)
    private StoryStage storyStage;

    protected RumorThreadArticle() {
    }

    public RumorThreadArticle(RumorThread rumorThread, Article article, StoryStage storyStage) {
        this.rumorThread = rumorThread;
        this.article = article;
        this.storyStage = storyStage;
    }

    public Long getId() {
        return id;
    }

    public RumorThread getRumorThread() {
        return rumorThread;
    }

    public Article getArticle() {
        return article;
    }

    public StoryStage getStoryStage() {
        return storyStage;
    }
}
