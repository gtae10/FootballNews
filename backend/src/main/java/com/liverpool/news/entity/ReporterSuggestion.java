package com.liverpool.news.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "reporter_suggestions")
public class ReporterSuggestion {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "twitter_handle", nullable = false)
    private String twitterHandle;

    @Column
    private String name;

    @Enumerated(EnumType.STRING)
    private League league;

    @Column(columnDefinition = "TEXT")
    private String memo;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    protected ReporterSuggestion() {
    }

    public ReporterSuggestion(User user, String twitterHandle, String name, League league, String memo) {
        this.user = user;
        this.twitterHandle = twitterHandle;
        this.name = name;
        this.league = league;
        this.memo = memo;
        this.createdAt = LocalDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public User getUser() {
        return user;
    }

    public String getTwitterHandle() {
        return twitterHandle;
    }

    public String getName() {
        return name;
    }

    public League getLeague() {
        return league;
    }

    public String getMemo() {
        return memo;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
}
