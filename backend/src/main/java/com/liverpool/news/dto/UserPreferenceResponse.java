package com.liverpool.news.dto;

import java.util.List;

public record UserPreferenceResponse(
        List<ClubResponse> clubs,
        int notificationTrustLevel,
        ClubResponse favoriteClub
) {
}
