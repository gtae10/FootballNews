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

    protected UserPreference() {
    }

    public UserPreference(User user, int notificationTrustLevel, Set<Club> clubs) {
        this.user = user;
        this.notificationTrustLevel = notificationTrustLevel;
        this.clubs = clubs;
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
}
