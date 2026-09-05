package com.liverpool.news.repository;

import com.liverpool.news.entity.RumorThreadArticle;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface RumorThreadArticleRepository extends JpaRepository<RumorThreadArticle, Long> {

    @Query("SELECT rta FROM RumorThreadArticle rta JOIN FETCH rta.article a "
            + "WHERE rta.rumorThread.id = :threadId ORDER BY a.publishedAt ASC")
    List<RumorThreadArticle> findByThreadIdOrderByArticlePublishedAtAsc(@Param("threadId") Long threadId);

    long countByRumorThreadId(Long threadId);
}
