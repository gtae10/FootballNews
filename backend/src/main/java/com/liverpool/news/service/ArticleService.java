package com.liverpool.news.service;

import com.liverpool.news.dto.ArticleDetailResponse;
import com.liverpool.news.dto.ArticleSummaryResponse;
import com.liverpool.news.entity.Article;
import com.liverpool.news.entity.Translation;
import com.liverpool.news.exception.ArticleNotFoundException;
import com.liverpool.news.repository.ArticleRepository;
import com.liverpool.news.repository.TranslationRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.List;
import java.util.TreeSet;

@Service
public class ArticleService {

    private final ArticleRepository articleRepository;
    private final TranslationRepository translationRepository;

    public ArticleService(ArticleRepository articleRepository,
                           TranslationRepository translationRepository) {
        this.articleRepository = articleRepository;
        this.translationRepository = translationRepository;
    }

    public Page<ArticleSummaryResponse> getArticles(Pageable pageable, String club, String keyword) {
        Page<Article> articles = articleRepository.search(normalize(club), normalize(keyword), pageable);
        return articles.map(this::toSummary);
    }

    private String normalize(String value) {
        return (value == null || value.isBlank()) ? null : value;
    }

    public List<ArticleSummaryResponse> getTopArticles(int limit) {
        LocalDate today = LocalDate.now();
        return articleRepository.findTopArticlesSince(today.atStartOfDay(), PageRequest.of(0, limit)).stream()
                .map(this::toSummary)
                .toList();
    }

    public ArticleDetailResponse getArticleDetail(Long id) {
        Article article = articleRepository.findById(id)
                .orElseThrow(() -> new ArticleNotFoundException("기사를 찾을 수 없습니다: " + id));

        Translation translation = translationRepository.findByArticleId(id)
                .orElse(null);

        return new ArticleDetailResponse(
                article.getId(),
                translation != null ? translation.getTitleKo() : null,
                article.getTitleOriginal(),
                translation != null ? translation.getContentKo() : null,
                article.getSource(),
                article.getOriginalUrl(),
                article.getPublishedAt(),
                translation != null ? translation.getTranslatedAt() : null,
                article.getSourceTier()
        );
    }

    private ArticleSummaryResponse toSummary(Article article) {
        Translation translation = translationRepository.findByArticleId(article.getId())
                .orElse(null);

        return new ArticleSummaryResponse(
                article.getId(),
                translation != null ? translation.getTitleKo() : article.getTitleOriginal(),
                article.getSource(),
                article.getPublishedAt(),
                article.getOriginalUrl(),
                List.copyOf(new TreeSet<>(article.getClubs())),
                article.getSourceTier()
        );
    }
}
