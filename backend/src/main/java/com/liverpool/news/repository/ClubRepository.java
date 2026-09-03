package com.liverpool.news.repository;

import com.liverpool.news.entity.Club;
import com.liverpool.news.entity.League;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ClubRepository extends JpaRepository<Club, Long> {

    List<Club> findAllByOrderByLeagueAscNameAsc();

    boolean existsByNameAndLeague(String name, League league);
}
