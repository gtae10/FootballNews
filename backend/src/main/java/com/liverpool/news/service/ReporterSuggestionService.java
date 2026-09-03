package com.liverpool.news.service;

import com.liverpool.news.dto.ReporterSuggestionRequest;
import com.liverpool.news.dto.ReporterSuggestionResponse;
import com.liverpool.news.entity.League;
import com.liverpool.news.entity.ReporterSuggestion;
import com.liverpool.news.entity.User;
import com.liverpool.news.exception.UserNotFoundException;
import com.liverpool.news.repository.ReporterSuggestionRepository;
import com.liverpool.news.repository.UserRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ReporterSuggestionService {

    private final ReporterSuggestionRepository reporterSuggestionRepository;
    private final UserRepository userRepository;

    public ReporterSuggestionService(ReporterSuggestionRepository reporterSuggestionRepository,
                                      UserRepository userRepository) {
        this.reporterSuggestionRepository = reporterSuggestionRepository;
        this.userRepository = userRepository;
    }

    public ReporterSuggestionResponse create(Long userId, ReporterSuggestionRequest request) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new UserNotFoundException("사용자를 찾을 수 없습니다: " + userId));

        ReporterSuggestion suggestion = new ReporterSuggestion(
                user,
                request.twitterHandle(),
                request.name(),
                parseLeague(request.league()),
                request.memo()
        );

        return toResponse(reporterSuggestionRepository.save(suggestion));
    }

    public List<ReporterSuggestionResponse> listMine(Long userId) {
        return reporterSuggestionRepository.findAllByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(this::toResponse)
                .toList();
    }

    private League parseLeague(String league) {
        if (league == null || league.isBlank()) {
            return null;
        }
        try {
            return League.valueOf(league.trim().toUpperCase());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    private ReporterSuggestionResponse toResponse(ReporterSuggestion suggestion) {
        return new ReporterSuggestionResponse(
                suggestion.getId(),
                suggestion.getTwitterHandle(),
                suggestion.getName(),
                suggestion.getLeague() != null ? suggestion.getLeague().name() : null,
                suggestion.getMemo(),
                suggestion.getCreatedAt()
        );
    }
}
