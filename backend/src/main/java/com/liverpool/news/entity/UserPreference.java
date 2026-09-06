package com.liverpool.news.entity;

import jakarta.persistence.*;

import java.util.HashSet;
import java.util.Set;

@Entity
@Table(name = "user_preferences")
public class UserPreference {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne
    @JoinColumn(name = "user_id", nullable = false, unique = true)
    private User user;

    @Column(name = "notification_trust_level", nullable = false)
    private int notificationTrustLevel;

    @ManyToMany
    @JoinTable(
            name = "user_preference_clubs",
            joinColumns = @JoinColumn(name = "user_preference_id"),
            inverseJoinColumns = @JoinColumn(name = "club_id")
    )
    private Set<Club> clubs = new HashSet<>();

    // 관심 구단(clubs) 중 대표로 지정한 하나. 관심 구단과 달리 다대일 단방향이며,
    // 관심 구단을 하나도 선택하지 않았거나 아직 최애팀을 고르지 않은 사용자는 null이다.
    @ManyToOne
    @JoinColumn(name = "favorite_club_id")
    private Club favoriteClub;

    protected UserPreference() {
    }

    public UserPreference(User user, int notificationTrustLevel, Set<Club> clubs) {
        this(user, notificationTrustLevel, clubs, null);
    }

    public UserPreference(User user, int notificationTrustLevel, Set<Club> clubs, Club favoriteClub) {
        this.user = user;
        this.notificationTrustLevel = notificationTrustLevel;
        this.clubs = clubs;
        this.favoriteClub = favoriteClub;
    }

    public Long getId() {
        return id;
    }

    public User getUser() {
        return user;
    }

    public int getNotificationTrustLevel() {
        return notificationTrustLevel;
    }

    public void setNotificationTrustLevel(int notificationTrustLevel) {
        this.notificationTrustLevel = notificationTrustLevel;
    }

    public Set<Club> getClubs() {
        return clubs;
    }

    public void setClubs(Set<Club> clubs) {
        this.clubs = clubs;
    }

    public Club getFavoriteClub() {
        return favoriteClub;
    }

    public void setFavoriteClub(Club favoriteClub) {
        this.favoriteClub = favoriteClub;
    }
}
