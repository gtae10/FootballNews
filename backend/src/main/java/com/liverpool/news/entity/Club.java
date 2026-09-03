package com.liverpool.news.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "clubs", uniqueConstraints = @UniqueConstraint(columnNames = {"name", "league"}))
public class Club {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private League league;

    protected Club() {
    }

    public Club(String name, League league) {
        this.name = name;
        this.league = league;
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public League getLeague() {
        return league;
    }
}
