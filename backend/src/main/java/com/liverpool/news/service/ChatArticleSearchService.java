package com.liverpool.news.service;

import com.liverpool.news.entity.Article;
import com.liverpool.news.entity.RumorThread;
import com.liverpool.news.entity.RumorThreadArticle;
import com.liverpool.news.entity.Translation;
import com.liverpool.news.repository.ArticleRepository;
import com.liverpool.news.repository.RumorThreadArticleRepository;
import com.liverpool.news.repository.TranslationRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 채팅 메시지에서 뽑은 키워드로 관련 기사를 찾아 RAG 컨텍스트로 만든다
 * ({@link ChatKeywordExtractor} 참고).
 */
@Service
public class ChatArticleSearchService {

    private static final int MAX_CANDIDATES_PER_KEYWORD = 20;
    private static final int EXCERPT_MAX_LENGTH = 300;

    private final ArticleRepository articleRepository;
    private final TranslationRepository translationRepository;
    private final RumorThreadArticleRepository rumorThreadArticleRepository;
    private final int maxContextArticles;

    public ChatArticleSearchService(
            ArticleRepository articleRepository,
            TranslationRepository translationRepository,
            RumorThreadArticleRepository rumorThreadArticleRepository,
            @Value("${app.chat.max-context-articles:5}") int maxContextArticles
    ) {
        this.articleRepository = articleRepository;
        this.translationRepository = translationRepository;
        this.rumorThreadArticleRepository = rumorThreadArticleRepository;
        this.maxContextArticles = maxContextArticles;
    }

    public List<ChatContextArticle> search(String userMessage) {
        List<String> keywords = ChatKeywordExtractor.extractKeywords(userMessage);
        if (keywords.isEmpty()) {
            return List.of();
        }

        Map<Long, Article> candidates = new LinkedHashMap<>();
        Map<Long, Integer> matchCounts = new HashMap<>();
        Pageable topRecent = PageRequest.of(0, MAX_CANDIDATES_PER_KEYWORD);

        for (String keyword : keywords) {
            for (Article article : articleRepository.findByKeywordForChat(keyword, topRecent)) {
                candidates.putIfAbsent(article.getId(), article);
                matchCounts.merge(article.getId(), 1, Integer::sum);
            }
        }

        if (candidates.isEmpty()) {
            return List.of();
        }

        List<Article> ranked = candidates.values().stream()
                .sorted(Comparator
                        .comparing((Article a) -> matchCounts.get(a.getId())).reversed()
                        .thenComparing(Article::getPublishedAt, Comparator.nullsLast(Comparator.reverseOrder())))
                .limit(maxContextArticles)
                .toList();

        Map<Long, RumorThreadArticle> rumorByArticleId = rumorThreadArticleRepository
                .findByArticleIdIn(ranked.stream().map(Article::getId).toList())
                .stream()
                .collect(Collectors.toMap(rta -> rta.getArticle().getId(), rta -> rta, (a, b) -> a));

        return ranked.stream()
                .map(article -> toContextArticle(article, rumorByArticleId.get(article.getId())))
                .toList();
    }

    private ChatContextArticle toContextArticle(Article article, RumorThreadArticle rumorLink) {
        Translation translation = translationRepository.findByArticleId(article.getId()).orElse(null);
        String title = translation != null && translation.getTitleKo() != null
                ? translation.getTitleKo() : article.getTitleOriginal();
        String content = translation != null && translation.getContentKo() != null
                ? translation.getContentKo() : article.getContentOriginal();

        RumorThread thread = rumorLink != null ? rumorLink.getRumorThread() : null;

        return new ChatContextArticle(
                article.getId(),
                title,
                truncate(content),
                article.getSource(),
                article.getSourceTier(),
                article.getPublishedAt(),
                thread != null ? thread.getLatestStage().name() : null,
                thread != null ? thread.isCrossReported() : null,
                thread != null ? thread.getIndependentSourceCount() : null
        );
    }

    private String truncate(String text) {
        if (text == null) {
            return "";
        }
        return text.length() <= EXCERPT_MAX_LENGTH ? text : text.substring(0, EXCERPT_MAX_LENGTH) + "...";
    }
}
