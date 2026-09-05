package com.liverpool.news.controller;

import com.liverpool.news.dto.RumorThreadDetailResponse;
import com.liverpool.news.dto.RumorThreadSummaryResponse;
import com.liverpool.news.service.RumorThreadService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/rumor-threads")
public class RumorThreadController {

    private final RumorThreadService rumorThreadService;

    public RumorThreadController(RumorThreadService rumorThreadService) {
        this.rumorThreadService = rumorThreadService;
    }

    @GetMapping
    public List<RumorThreadSummaryResponse> getRumorThreads(
            @RequestParam(required = false) String sort
    ) {
        return rumorThreadService.getThreads(sort);
    }

    @GetMapping("/{id}")
    public RumorThreadDetailResponse getRumorThreadDetail(@PathVariable Long id) {
        return rumorThreadService.getThreadDetail(id);
    }
}
