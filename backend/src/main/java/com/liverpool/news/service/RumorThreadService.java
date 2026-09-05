package com.liverpool.news.service;

import com.liverpool.news.dto.RumorThreadArticleResponse;
import com.liverpool.news.dto.RumorThreadDetailResponse;
import com.liverpool.news.dto.RumorThreadSummaryResponse;
import com.liverpool.news.entity.Article;
import com.liverpool.news.entity.RumorThread;
import com.liverpool.news.entity.RumorThreadArticle;
import com.liverpool.news.entity.Translation;
import com.liverpool.news.exception.RumorThreadNotFoundException;
import com.liverpool.news.repository.RumorThreadArticleRepository;
import com.liverpool.news.repository.RumorThreadRepository;
import com.liverpool.news.repository.TranslationRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class RumorThreadService {

    private final RumorThreadRepository rumorThreadRepository;
    private final RumorThreadArticleRepository rumorThreadArticleRepository;
    private final TranslationRepository translationRepository;

    public RumorThreadService(RumorThreadRepository rumorThreadRepository,
                               RumorThreadArticleRepository rumorThreadArticleRepository,
                               TranslationRepository translationRepository) {
        this.rumorThreadRepository = rumorThreadRepository;
        this.rumorThreadArticleRepository = rumorThreadArticleRepository;
        this.translationRepository = translationRepository;
    }

    public List<RumorThreadSummaryResponse> getThreads(String sort) {
        List<RumorThread> threads = "latest".equals(sort)
                ? rumorThreadRepository.findAllByOrderByUpdatedAtDesc()
                : rumorThreadRepository.findAllByOrderByIndependentSourceCountDescUpdatedAtDesc();
        return threads.stream().map(this::toSummary).toList();
    }

    public RumorThreadDetailResponse getThreadDetail(Long id) {
        RumorThread thread = rumorThreadRepository.findById(id)
                .orElseThrow(() -> new RumorThreadNotFoundException("루머 스레드를 찾을 수 없습니다: " + id));

        List<RumorThreadArticleResponse> articles = rumorThreadArticleRepository
                .findByThreadIdOrderByArticlePublishedAtAsc(id).stream()
                .map(this::toArticleResponse)
                .toList();

        return new RumorThreadDetailResponse(
                thread.getId(),
                thread.getPlayerName(),
                thread.getClubName(),
                thread.getLatestStage().name(),
                thread.getIndependentSourceCount(),
                thread.isCrossReported(),
                thread.getCreatedAt(),
                thread.getUpdatedAt(),
                articles
        );
    }

    private RumorThreadSummaryResponse toSummary(RumorThread thread) {
        long articleCount = rumorThreadArticleRepository.countByRumorThreadId(thread.getId());
        return new RumorThreadSummaryResponse(
                thread.getId(),
                thread.getPlayerName(),
                thread.getClubName(),
                thread.getLatestStage().name(),
                thread.getIndependentSourceCount(),
                thread.isCrossReported(),
                articleCount,
                thread.getCreatedAt(),
                thread.getUpdatedAt()
        );
    }

    private RumorThreadArticleResponse toArticleResponse(RumorThreadArticle link) {
        Article article = link.getArticle();
        Translation translation = translationRepository.findByArticleId(article.getId()).orElse(null);

        return new RumorThreadArticleResponse(
                article.getId(),
                article.getSource(),
                translation != null ? translation.getTitleKo() : null,
                article.getTitleOriginal(),
                article.getOriginalUrl(),
                article.getPublishedAt(),
                link.getStoryStage().name()
        );
    }
}
