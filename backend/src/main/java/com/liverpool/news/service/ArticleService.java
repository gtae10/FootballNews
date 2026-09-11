package com.liverpool.news.service;

import com.liverpool.news.dto.ArticleDetailResponse;
import com.liverpool.news.dto.ArticleSummaryResponse;
import com.liverpool.news.entity.Article;
import com.liverpool.news.entity.ArticleCategory;
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

    public Page<ArticleSummaryResponse> getArticles(
            Pageable pageable, String club, List<String> clubs, String keyword, String category) {
        List<String> normalizedClubs = normalizeList(clubs);
        Page<Article> articles = normalizedClubs != null
                ? articleRepository.searchByClubs(
                        normalizedClubs, parseCategory(category), normalize(keyword), pageable)
                : articleRepository.search(
                        normalize(club), parseCategory(category), normalize(keyword), pageable);
        return articles.map(this::toSummary);
    }

    private String normalize(String value) {
        return (value == null || value.isBlank()) ? null : value;
    }

    // "관심구단 전체" 탭에서 넘어오는 구단 목록. 비어 있으면(관심 구단을 아직 하나도
    // 선택하지 않은 사용자 등) club 단일 필터 경로로 자연스럽게 폴백하도록 null을
    // 반환한다 — 그렇지 않으면 빈 IN 목록 때문에 결과가 무조건 0건이 된다.
    private List<String> normalizeList(List<String> values) {
        if (values == null || values.isEmpty()) {
            return null;
        }
        return values;
    }

    private ArticleCategory parseCategory(String category) {
        String normalized = normalize(category);
        if (normalized == null) {
            return null;
        }
        try {
            return ArticleCategory.valueOf(normalized.toUpperCase());
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("알 수 없는 카테고리입니다: " + category);
        }
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
                article.getSourceTier(),
                article.getImageUrl(),
                article.getCategory() != null ? article.getCategory().name() : null,
                article.getImages()
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
                article.getSourceTier(),
                article.getImageUrl(),
                article.getCategory() != null ? article.getCategory().name() : null
        );
    }
}
