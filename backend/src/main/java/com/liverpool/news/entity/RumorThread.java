package com.liverpool.news.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

/**
 * 같은 이적 건(선수 + 구단)으로 묶인 기사들의 스레드. collector/rumor_clusterer.py가
 * 채우고 갱신한다 (docs/DB_SCHEMA.md 참고). 백엔드는 이 테이블을 읽기만 한다.
 *
 * independentSourceCount/crossReported는 "여러 매체가 48시간 이내에 서로 독립적으로
 * 같은 이야기를 보도했다"는 뜻일 뿐, 이적이 사실로 확정됐다는 뜻이 아니다. 그 오해를
 * 피하려고 의도적으로 verified라는 이름을 쓰지 않았다 (docs/API.md 참고).
 */
@Entity
@Table(name = "rumor_threads")
public class RumorThread {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "player_name", nullable = false)
    private String playerName;

    @Column(name = "club_name", nullable = false)
    private String clubName;

    @Enumerated(EnumType.STRING)
    @Column(name = "latest_stage", nullable = false)
    private StoryStage latestStage;

    @Column(name = "independent_source_count", nullable = false)
    private Integer independentSourceCount;

    @Column(name = "cross_reported", nullable = false)
    private boolean crossReported;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    protected RumorThread() {
    }

    public RumorThread(String playerName, String clubName, StoryStage latestStage,
                        Integer independentSourceCount, boolean crossReported) {
        this.playerName = playerName;
        this.clubName = clubName;
        this.latestStage = latestStage;
        this.independentSourceCount = independentSourceCount;
        this.crossReported = crossReported;
        LocalDateTime now = LocalDateTime.now();
        this.createdAt = now;
        this.updatedAt = now;
    }

    public Long getId() {
        return id;
    }

    public String getPlayerName() {
        return playerName;
    }

    public String getClubName() {
        return clubName;
    }

    public StoryStage getLatestStage() {
        return latestStage;
    }

    public Integer getIndependentSourceCount() {
        return independentSourceCount;
    }

    public boolean isCrossReported() {
        return crossReported;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }
}
