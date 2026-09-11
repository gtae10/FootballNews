package com.liverpool.news.repository;

import com.liverpool.news.entity.Article;
import com.liverpool.news.entity.ArticleCategory;
import com.liverpool.news.entity.Translation;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;

import java.time.LocalDateTime;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

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

        Page<Article> byTranslatedTitle = articleRepository.search(null, null, "유니폼", PageRequest.of(0, 10));
        assertThat(byTranslatedTitle.getContent()).containsExactly(translated);

        Page<Article> byOriginalTitle = articleRepository.search(null, null, "hat-trick", PageRequest.of(0, 10));
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

        Page<Article> result = articleRepository.search("Liverpool", null, "kit", PageRequest.of(0, 10));

        assertThat(result.getContent()).containsExactly(match);
    }

    @Test
    void 매칭되는_기사가_없으면_빈_페이지를_반환한다() {
        articleRepository.save(new Article(
                "Liverpool FC 공식", "https://example.com/1", "Liverpool unveil new kit",
                "content", LocalDateTime.now(), "Liverpool", 1));

        Page<Article> result = articleRepository.search(null, null, "존재하지않는검색어", PageRequest.of(0, 10));

        assertThat(result.getContent()).isEmpty();
    }

    @Test
    void category로_기사_목록을_필터링한다() {
        Article matchArticle = articleRepository.save(new Article(
                "Sky Sports Football", "https://example.com/match", "Liverpool 3-1 Arsenal: match report",
                "content", LocalDateTime.now(), Set.of("Liverpool", "Arsenal"), 1, null, null,
                ArticleCategory.MATCH));
        articleRepository.save(new Article(
                "The Anfield Wrap", "https://example.com/transfer", "Liverpool sign new striker",
                "content", LocalDateTime.now(), Set.of("Liverpool"), 2, null, null,
                ArticleCategory.TRANSFER));

        Page<Article> result = articleRepository.search(null, ArticleCategory.MATCH, null, PageRequest.of(0, 10));

        assertThat(result.getContent()).containsExactly(matchArticle);
    }

    @Test
    void category가_null인_기사도_category_필터를_주지_않으면_함께_반환된다() {
        articleRepository.save(new Article(
                "Sky Sports Football", "https://example.com/uncategorized", "Uncategorized article",
                "content", LocalDateTime.now(), "Liverpool", 1));

        Page<Article> result = articleRepository.search(null, null, null, PageRequest.of(0, 10));

        assertThat(result.getContent()).hasSize(1);
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

    @Test
    void searchByClubs는_목록_중_하나라도_겹치는_기사를_모두_반환한다() {
        Article liverpoolArticle = articleRepository.save(new Article(
                "Liverpool FC 공식", "https://example.com/liverpool-only", "Liverpool news",
                "content", LocalDateTime.now(), "Liverpool", 1));
        Article arsenalArticle = articleRepository.save(new Article(
                "Arsenal News", "https://example.com/arsenal-only", "Arsenal news",
                "content", LocalDateTime.now(), "Arsenal", 1));
        articleRepository.save(new Article(
                "Chelsea News", "https://example.com/chelsea-only", "Chelsea news",
                "content", LocalDateTime.now(), "Chelsea", 1));

        Page<Article> result = articleRepository.searchByClubs(
                List.of("Liverpool", "Arsenal"), null, null, PageRequest.of(0, 10));

        assertThat(result.getContent()).containsExactlyInAnyOrder(liverpoolArticle, arsenalArticle);
    }

    @Test
    void searchByClubs는_한_기사가_목록_속_여러_구단을_동시에_언급해도_한_번만_반환한다() {
        Article transferArticle = articleRepository.save(new Article(
                "Sky Sports Football", "https://example.com/multi-club", "Liverpool and Arsenal chase target",
                "content", LocalDateTime.now(), Set.of("Liverpool", "Arsenal"), 1, null, null));

        Page<Article> result = articleRepository.searchByClubs(
                List.of("Liverpool", "Arsenal"), null, null, PageRequest.of(0, 10));

        assertThat(result.getContent()).containsExactly(transferArticle);
    }

    @Test
    void searchByClubs는_category_필터도_함께_적용한다() {
        Article matchArticle = articleRepository.save(new Article(
                "Sky Sports Football", "https://example.com/clubs-match", "Liverpool 2-1 win",
                "content", LocalDateTime.now(), Set.of("Liverpool"), 1, null, null, ArticleCategory.MATCH));
        articleRepository.save(new Article(
                "The Anfield Wrap", "https://example.com/clubs-transfer", "Liverpool sign striker",
                "content", LocalDateTime.now(), Set.of("Liverpool"), 2, null, null, ArticleCategory.TRANSFER));

        Page<Article> result = articleRepository.searchByClubs(
                List.of("Liverpool"), ArticleCategory.MATCH, null, PageRequest.of(0, 10));

        assertThat(result.getContent()).containsExactly(matchArticle);
    }

    @Test
    void 본문_크롤링_이미지는_원문에_실린_순서_그대로_저장되고_없으면_빈_리스트다() {
        Article withImages = articleRepository.save(new Article(
                "Liverpool FC 공식", "https://example.com/with-body-images", "Liverpool unveil new kit",
                "content", LocalDateTime.now(), new HashSet<>(), 1, null, "https://example.com/thumb.jpg"));
        withImages.getImages().add("https://example.com/body1.jpg");
        withImages.getImages().add("https://example.com/body2.jpg");
        articleRepository.save(withImages);

        Article withoutImages = articleRepository.save(new Article(
                "Liverpool FC 공식", "https://example.com/without-body-images", "Liverpool sign striker",
                "content", LocalDateTime.now(), "Liverpool", 1));

        Article reloadedWithImages = articleRepository.findById(withImages.getId()).orElseThrow();
        Article reloadedWithoutImages = articleRepository.findById(withoutImages.getId()).orElseThrow();

        assertThat(reloadedWithImages.getImages())
                .containsExactly("https://example.com/body1.jpg", "https://example.com/body2.jpg");
        assertThat(reloadedWithoutImages.getImages()).isEmpty();
    }
}
