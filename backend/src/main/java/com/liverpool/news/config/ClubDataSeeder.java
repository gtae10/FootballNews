package com.liverpool.news.config;

import com.liverpool.news.entity.Club;
import com.liverpool.news.entity.League;
import com.liverpool.news.repository.ClubRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class ClubDataSeeder implements CommandLineRunner {

    private static final Map<League, String[]> CLUBS_BY_LEAGUE = Map.of(
            League.EPL, new String[]{
                    "Liverpool", "Manchester United", "Manchester City", "Arsenal", "Chelsea",
                    "Tottenham Hotspur", "Newcastle United", "Aston Villa", "West Ham United", "Everton"
            },
            League.LA_LIGA, new String[]{
                    "Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla", "Real Sociedad",
                    "Real Betis", "Villarreal", "Valencia", "Athletic Bilbao", "Girona"
            },
            League.BUNDESLIGA, new String[]{
                    "Bayern Munich", "Borussia Dortmund", "RB Leipzig", "Bayer Leverkusen", "Eintracht Frankfurt",
                    "VfB Stuttgart", "Borussia Monchengladbach", "Wolfsburg", "Union Berlin", "Freiburg"
            },
            League.SERIE_A, new String[]{
                    "Juventus", "Inter Milan", "AC Milan", "Napoli", "AS Roma",
                    "Lazio", "Atalanta", "Fiorentina", "Torino", "Bologna"
            },
            League.LIGUE_1, new String[]{
                    "Paris Saint-Germain", "Marseille", "Monaco", "Lyon", "Lille",
                    "Nice", "Rennes", "Lens", "Strasbourg", "Toulouse"
            }
    );

    private final ClubRepository clubRepository;

    public ClubDataSeeder(ClubRepository clubRepository) {
        this.clubRepository = clubRepository;
    }

    @Override
    public void run(String... args) {
        CLUBS_BY_LEAGUE.forEach((league, names) -> {
            for (String name : names) {
                if (!clubRepository.existsByNameAndLeague(name, league)) {
                    clubRepository.save(new Club(name, league));
                }
            }
        });
    }
}
