package com.liverpool.news.controller;

import com.liverpool.news.dto.ClubResponse;
import com.liverpool.news.repository.ClubRepository;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/clubs")
public class ClubController {

    private final ClubRepository clubRepository;

    public ClubController(ClubRepository clubRepository) {
        this.clubRepository = clubRepository;
    }

    @GetMapping
    public List<ClubResponse> getClubs() {
        return clubRepository.findAllByOrderByLeagueAscNameAsc().stream()
                .map(club -> new ClubResponse(club.getId(), club.getName(), club.getLeague().name()))
                .toList();
    }
}
