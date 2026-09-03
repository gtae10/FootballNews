package com.liverpool.news.repository;

import com.liverpool.news.entity.ReporterSuggestion;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ReporterSuggestionRepository extends JpaRepository<ReporterSuggestion, Long> {

    List<ReporterSuggestion> findAllByUserIdOrderByCreatedAtDesc(Long userId);

    void deleteAllByUserId(Long userId);
}
