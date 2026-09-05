package com.liverpool.news.repository;

import com.liverpool.news.entity.Article;
import com.liverpool.news.entity.Translation;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;

import java.time.LocalDateTime;
import java.util.HashSet;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
class ArticleRepositoryTest {

    @Autowired
    private ArticleRepository articleRepository;

    @Autowired
    private TranslationRepository translationRepository;

    @Test
    void keyword는_titleKo와_titleOriginal_중_하나만_일치해도_매칭된다() {
        Article translated = articleRepository.save(new Article(
                "Liverpool FC 공식", "https://example.com/1", "Liverpool unveil new kit",
                "content", LocalDateTime.now(), "Liverpool", 1));
        translationRepository.save(new Translation(translated, "리버풀 새 유니폼 공개", "본문", "v1"));

        Article untranslated = articleRepository.save(new Article(
                "BBC Sport", "https://example.com/2", "Salah scores hat-trick",
                "content", LocalDateTime.now(), "Liverpool", 2));

        articleRepository.save(new Article(
                "Arsenal News", "https://example.com/3", "Arsenal sign new striker",
                "content", LocalDateTime.now(), "Arsenal", 1));

        Page<Article> byTranslatedTitle = articleRepository.search(null, "유니폼", PageRequest.of(0, 10));
        assertThat(byTranslatedTitle.getContent()).containsExactly(translated);

        Page<Article> byOriginalTitle = articleRepository.search(null, "hat-trick", PageRequest.of(0, 10));
        assertThat(byOriginalTitle.getContent()).containsExactly(untranslated);
    }

    @Test
    void club과_keyword를_함께_주면_AND_조건으로_필터링한다() {
        Article match = articleRepository.save(new Article(
                "Liverpool FC 공식", "https://example.com/1", "Liverpool unveil new kit",
                "content", LocalDateTime.now(), "Liverpool", 1));
        articleRepository.save(new Article(
                "Arsenal News", "https://example.com/2", "Arsenal unveil new kit",
                "content", LocalDateTime.now(), "Arsenal", 1));

        Page<Article> result = articleRepository.search("Liverpool", "kit", PageRequest.of(0, 10));

        assertThat(result.getContent()).containsExactly(match);
    }

    @Test
    void 매칭되는_기사가_없으면_빈_페이지를_반환한다() {
        articleRepository.save(new Article(
                "Liverpool FC 공식", "https://example.com/1", "Liverpool unveil new kit",
                "content", LocalDateTime.now(), "Liverpool", 1));

        Page<Article> result = articleRepository.search(null, "존재하지않는검색어", PageRequest.of(0, 10));

        assertThat(result.getContent()).isEmpty();
    }

    @Test
    void imageUrl이_있으면_그대로_저장되고_없으면_null로_유지된다() {
        Article withImage = articleRepository.save(new Article(
                "Liverpool FC 공식", "https://example.com/with-image", "Liverpool unveil new kit",
                "content", LocalDateTime.now(), new HashSet<>(), 1, null, "https://example.com/thumb.jpg"));
        Article withoutImage = articleRepository.save(new Article(
                "Liverpool FC 공식", "https://example.com/without-image", "Liverpool sign striker",
                "content", LocalDateTime.now(), "Liverpool", 1));

        Article reloadedWithImage = articleRepository.findById(withImage.getId()).orElseThrow();
        Article reloadedWithoutImage = articleRepository.findById(withoutImage.getId()).orElseThrow();

        assertThat(reloadedWithImage.getImageUrl()).isEqualTo("https://example.com/thumb.jpg");
        assertThat(reloadedWithoutImage.getImageUrl()).isNull();
    }
}
