package com.liverpool.news.repository;

import com.liverpool.news.entity.Article;
import com.liverpool.news.entity.ArticleCategory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

public interface ArticleRepository extends JpaRepository<Article, Long> {

    Optional<Article> findByOriginalUrl(String originalUrl);

    @Query("SELECT a FROM Article a LEFT JOIN Translation t ON t.article = a "
            + "WHERE (:club IS NULL OR :club MEMBER OF a.clubs) "
            + "AND (:category IS NULL OR a.category = :category) "
            + "AND (:keyword IS NULL "
            + "     OR LOWER(a.titleOriginal) LIKE LOWER(CONCAT('%', :keyword, '%')) "
            + "     OR LOWER(t.titleKo) LIKE LOWER(CONCAT('%', :keyword, '%'))) "
            + "ORDER BY a.publishedAt DESC")
    Page<Article> search(@Param("club") String club, @Param("category") ArticleCategory category,
                          @Param("keyword") String keyword, Pageable pageable);

    // "관심구단" 탭 — 사용자가 팔로우한 구단이 여러 곳이라 단일 :club MEMBER OF로는
    // 표현할 수 없어, 구단 목록 중 하나라도 겹치면 매칭되도록 JOIN a.clubs로 별도
    // 쿼리를 둔다. 한 기사가 목록 중 여러 구단을 동시에 언급하면 JOIN으로 행이
    // 중복될 수 있어 DISTINCT를 쓴다.
    @Query("SELECT DISTINCT a FROM Article a LEFT JOIN Translation t ON t.article = a "
            + "JOIN a.clubs c "
            + "WHERE c IN :clubs "
            + "AND (:category IS NULL OR a.category = :category) "
            + "AND (:keyword IS NULL "
            + "     OR LOWER(a.titleOriginal) LIKE LOWER(CONCAT('%', :keyword, '%')) "
            + "     OR LOWER(t.titleKo) LIKE LOWER(CONCAT('%', :keyword, '%'))) "
            + "ORDER BY a.publishedAt DESC")
    Page<Article> searchByClubs(@Param("clubs") List<String> clubs, @Param("category") ArticleCategory category,
                                 @Param("keyword") String keyword, Pageable pageable);

    @Query("SELECT a FROM Article a WHERE a.publishedAt >= :since "
            + "ORDER BY a.publishedAt DESC, COALESCE(a.sourceTier, 99) ASC")
    List<Article> findTopArticlesSince(@Param("since") LocalDateTime since, Pageable pageable);

    // 채팅 위젯의 RAG 컨텍스트 검색용. 위 search()는 제목만 보지만, 챗봇 질문에
    // 나오는 선수/구단명은 번역 본문(content_ko)에만 등장하는 경우가 많아 본문까지
    // 함께 본다. 키워드 하나당 한 번씩 호출해(ChatArticleSearchService) Java에서
    // 병합·스코어링한다 — 키워드가 몇 개 안 되고(질문 하나당 최대 수 개) DB도
    // 크지 않아 이 편이 다중 키워드 동적 JPQL을 만드는 것보다 간단하다.
    @Query("SELECT a FROM Article a LEFT JOIN Translation t ON t.article = a "
            + "WHERE LOWER(a.titleOriginal) LIKE LOWER(CONCAT('%', :keyword, '%')) "
            + "   OR LOWER(a.contentOriginal) LIKE LOWER(CONCAT('%', :keyword, '%')) "
            + "   OR LOWER(t.titleKo) LIKE LOWER(CONCAT('%', :keyword, '%')) "
            + "   OR LOWER(t.contentKo) LIKE LOWER(CONCAT('%', :keyword, '%')) "
            + "ORDER BY a.publishedAt DESC")
    List<Article> findByKeywordForChat(@Param("keyword") String keyword, Pageable pageable);
}
