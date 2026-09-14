package com.liverpool.news.repository;

import com.liverpool.news.entity.RumorThreadArticle;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Collection;
import java.util.List;

public interface RumorThreadArticleRepository extends JpaRepository<RumorThreadArticle, Long> {

    @Query("SELECT rta FROM RumorThreadArticle rta JOIN FETCH rta.article a "
            + "WHERE rta.rumorThread.id = :threadId ORDER BY a.publishedAt ASC")
    List<RumorThreadArticle> findByThreadIdOrderByArticlePublishedAtAsc(@Param("threadId") Long threadId);

    long countByRumorThreadId(Long threadId);

    // 채팅 RAG 컨텍스트용 — 검색된 기사가 이적 루머 스레드에 속해 있으면, 챗봇이
    // "N개 매체가 보도했고 아직 공식 발표는 아님" 같은 문구를 지어내지 않고 실제
    // independentSourceCount/crossReported/latestStage를 인용할 수 있게 함께 가져온다.
    @Query("SELECT rta FROM RumorThreadArticle rta JOIN FETCH rta.rumorThread "
            + "WHERE rta.article.id IN :articleIds")
    List<RumorThreadArticle> findByArticleIdIn(@Param("articleIds") Collection<Long> articleIds);
}
