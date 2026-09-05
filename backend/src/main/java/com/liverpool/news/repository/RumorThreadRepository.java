package com.liverpool.news.repository;

import com.liverpool.news.entity.RumorThread;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface RumorThreadRepository extends JpaRepository<RumorThread, Long> {

    List<RumorThread> findAllByOrderByIndependentSourceCountDescUpdatedAtDesc();

    List<RumorThread> findAllByOrderByUpdatedAtDesc();
}
