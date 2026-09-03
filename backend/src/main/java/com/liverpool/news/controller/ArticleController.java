package com.liverpool.news.controller;

import com.liverpool.news.dto.ArticleDetailResponse;
import com.liverpool.news.dto.ArticleSummaryResponse;
import com.liverpool.news.service.ArticleService;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/articles")
public class ArticleController {

    private final ArticleService articleService;

    public ArticleController(ArticleService articleService) {
        this.articleService = articleService;
    }

    @GetMapping
    public Page<ArticleSummaryResponse> getArticles(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String club,
            @RequestParam(required = false) String keyword
    ) {
        Pageable pageable = PageRequest.of(page, size);
        return articleService.getArticles(pageable, club, keyword);
    }

    @GetMapping("/top")
    public List<ArticleSummaryResponse> getTopArticles(
            @RequestParam(defaultValue = "10") int limit
    ) {
        return articleService.getTopArticles(limit);
    }

    @GetMapping("/{id}")
    public ArticleDetailResponse getArticleDetail(@PathVariable Long id) {
        return articleService.getArticleDetail(id);
    }
}
