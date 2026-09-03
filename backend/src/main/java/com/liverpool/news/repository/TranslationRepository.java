package com.liverpool.news.repository;

import com.liverpool.news.entity.Translation;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface TranslationRepository extends JpaRepository<Translation, Long> {

    Optional<Translation> findByArticleId(Long articleId);
}
