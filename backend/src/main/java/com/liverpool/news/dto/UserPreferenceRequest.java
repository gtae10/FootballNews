package com.liverpool.news.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

import java.util.List;

public record UserPreferenceRequest(
        @NotNull List<Long> clubIds,
        @Min(1) @Max(5) int notificationTrustLevel
) {
}
