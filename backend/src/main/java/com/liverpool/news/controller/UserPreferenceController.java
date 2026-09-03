package com.liverpool.news.controller;

import com.liverpool.news.dto.UserPreferenceRequest;
import com.liverpool.news.dto.UserPreferenceResponse;
import com.liverpool.news.security.AuthenticatedUser;
import com.liverpool.news.service.UserPreferenceService;
import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/users/me/preferences")
public class UserPreferenceController {

    private final UserPreferenceService userPreferenceService;

    public UserPreferenceController(UserPreferenceService userPreferenceService) {
        this.userPreferenceService = userPreferenceService;
    }

    @GetMapping
    public UserPreferenceResponse getPreference(@AuthenticationPrincipal AuthenticatedUser user) {
        return userPreferenceService.getPreference(user.id());
    }

    @PutMapping
    public UserPreferenceResponse savePreference(@AuthenticationPrincipal AuthenticatedUser user,
                                                  @Valid @RequestBody UserPreferenceRequest request) {
        return userPreferenceService.savePreference(user.id(), request);
    }
}
