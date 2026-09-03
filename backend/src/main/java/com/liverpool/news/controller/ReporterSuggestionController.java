package com.liverpool.news.controller;

import com.liverpool.news.dto.ReporterSuggestionRequest;
import com.liverpool.news.dto.ReporterSuggestionResponse;
import com.liverpool.news.security.AuthenticatedUser;
import com.liverpool.news.service.ReporterSuggestionService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/reporter-suggestions")
public class ReporterSuggestionController {

    private final ReporterSuggestionService reporterSuggestionService;

    public ReporterSuggestionController(ReporterSuggestionService reporterSuggestionService) {
        this.reporterSuggestionService = reporterSuggestionService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ReporterSuggestionResponse create(@AuthenticationPrincipal AuthenticatedUser user,
                                              @Valid @RequestBody ReporterSuggestionRequest request) {
        return reporterSuggestionService.create(user.id(), request);
    }

    @GetMapping("/me")
    public List<ReporterSuggestionResponse> listMine(@AuthenticationPrincipal AuthenticatedUser user) {
        return reporterSuggestionService.listMine(user.id());
    }
}
