package com.liverpool.news.repository;

import com.liverpool.news.entity.Article;
import com.liverpool.news.entity.RumorThread;
import com.liverpool.news.entity.RumorThreadArticle;
import com.liverpool.news.entity.StoryStage;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
class RumorThreadRepositoryTest {

    @Autowired
    private RumorThreadRepository rumorThreadRepository;

    @Autowired
    private RumorThreadArticleRepository rumorThreadArticleRepository;

    @Autowired
    private ArticleRepository articleRepository;

    @Test
    void 목록은_independentSourceCount_내림차순으로_정렬된다() {
        rumorThreadRepository.save(new RumorThread("Isak", "Liverpool", StoryStage.INTEREST, 1, false));
        RumorThread mostVerified = rumorThreadRepository.save(
                new RumorThread("Wirtz", "Liverpool", StoryStage.CONFIRMED, 3, true));
        rumorThreadRepository.save(new RumorThread("Gyokeres", "Arsenal", StoryStage.NEGOTIATION, 2, true));

        List<RumorThread> result = rumorThreadRepository.findAllByOrderByIndependentSourceCountDescUpdatedAtDesc();

        assertThat(result.get(0).getId()).isEqualTo(mostVerified.getId());
        assertThat(result).extracting(RumorThread::getIndependentSourceCount)
                .containsExactly(3, 2, 1);
    }

    @Test
    void 스레드에_연결된_기사를_발행일_오름차순으로_조회한다() {
        RumorThread thread = rumorThreadRepository.save(
                new RumorThread("Isak", "Liverpool", StoryStage.CONFIRMED, 2, true));

        Article later = articleRepository.save(new Article(
                "Fabrizio Romano", "https://example.com/isak-2", "Isak here we go",
                "content", LocalDateTime.of(2026, 8, 30, 9, 0), "Liverpool", 1));
        Article earlier = articleRepository.save(new Article(
                "The Anfield Wrap", "https://example.com/isak-1", "Liverpool linked with Isak",
                "content", LocalDateTime.of(2026, 8, 28, 9, 0), "Liverpool", 2));

        rumorThreadArticleRepository.save(new RumorThreadArticle(thread, later, StoryStage.CONFIRMED));
        rumorThreadArticleRepository.save(new RumorThreadArticle(thread, earlier, StoryStage.INTEREST));

        List<RumorThreadArticle> ordered = rumorThreadArticleRepository
                .findByThreadIdOrderByArticlePublishedAtAsc(thread.getId());

        assertThat(ordered).extracting(link -> link.getArticle().getId())
                .containsExactly(earlier.getId(), later.getId());
        assertThat(rumorThreadArticleRepository.countByRumorThreadId(thread.getId())).isEqualTo(2);
    }
}
