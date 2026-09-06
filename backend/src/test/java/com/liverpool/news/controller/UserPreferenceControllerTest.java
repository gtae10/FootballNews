package com.liverpool.news.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.liverpool.news.config.SecurityConfig;
import com.liverpool.news.dto.ClubResponse;
import com.liverpool.news.dto.UserPreferenceRequest;
import com.liverpool.news.dto.UserPreferenceResponse;
import com.liverpool.news.exception.OnboardingRequiredException;
import com.liverpool.news.security.AuthenticatedUser;
import com.liverpool.news.security.JwtService;
import com.liverpool.news.service.UserPreferenceService;
import com.liverpool.news.support.SecurityTestConfig;
import jakarta.servlet.http.Cookie;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;
import java.util.Optional;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(UserPreferenceController.class)
@Import({SecurityConfig.class, SecurityTestConfig.class})
class UserPreferenceControllerTest {

    private static final Cookie VALID_COOKIE = new Cookie("access_token", "valid-token");

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private UserPreferenceService userPreferenceService;

    @Autowired
    private JwtService jwtService;

    @BeforeEach
    void setUpAuth() {
        reset(jwtService);
        when(jwtService.parse("valid-token"))
                .thenReturn(Optional.of(new AuthenticatedUser(1L, "test@example.com")));
    }

    @Test
    void 인증_없이_조회시_401을_반환한다() throws Exception {
        mockMvc.perform(get("/api/v1/users/me/preferences"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 인증_없이_저장시_401을_반환한다() throws Exception {
        UserPreferenceRequest request = new UserPreferenceRequest(List.of(1L), 3, null);

        mockMvc.perform(put("/api/v1/users/me/preferences")
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 인증된_사용자의_선호도를_조회한다() throws Exception {
        UserPreferenceResponse response = new UserPreferenceResponse(
                List.of(new ClubResponse(1L, "Liverpool", "EPL")), 3, null);
        when(userPreferenceService.getPreference(1L)).thenReturn(response);

        mockMvc.perform(get("/api/v1/users/me/preferences").cookie(VALID_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.clubs[0].name").value("Liverpool"))
                .andExpect(jsonPath("$.notificationTrustLevel").value(3));
    }

    @Test
    void 인증된_사용자가_선호도를_저장한다() throws Exception {
        UserPreferenceRequest request = new UserPreferenceRequest(List.of(1L, 2L), 4, null);
        UserPreferenceResponse response = new UserPreferenceResponse(
                List.of(new ClubResponse(1L, "Liverpool", "EPL"), new ClubResponse(2L, "Arsenal", "EPL")), 4, null);
        when(userPreferenceService.savePreference(eq(1L), any())).thenReturn(response);

        mockMvc.perform(put("/api/v1/users/me/preferences")
                        .cookie(VALID_COOKIE)
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.notificationTrustLevel").value(4))
                .andExpect(jsonPath("$.clubs.length()").value(2));

        verify(userPreferenceService).savePreference(eq(1L), any());
    }

    @Test
    void 온보딩을_완료하지_않은_사용자가_조회하면_400을_반환한다() throws Exception {
        when(userPreferenceService.getPreference(1L))
                .thenThrow(new OnboardingRequiredException("아직 온보딩을 완료하지 않은 사용자입니다: 1"));

        mockMvc.perform(get("/api/v1/users/me/preferences").cookie(VALID_COOKIE))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("아직 온보딩을 완료하지 않은 사용자입니다: 1"));
    }

    @Test
    void 신뢰도_범위를_벗어나면_400을_반환한다() throws Exception {
        UserPreferenceRequest request = new UserPreferenceRequest(List.of(1L), 9, null);

        mockMvc.perform(put("/api/v1/users/me/preferences")
                        .cookie(VALID_COOKIE)
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void favoriteClubId를_포함해_저장하면_응답에_최애팀이_담긴다() throws Exception {
        UserPreferenceRequest request = new UserPreferenceRequest(List.of(1L, 2L), 3, 1L);
        UserPreferenceResponse response = new UserPreferenceResponse(
                List.of(new ClubResponse(1L, "Liverpool", "EPL"), new ClubResponse(2L, "Arsenal", "EPL")),
                3, new ClubResponse(1L, "Liverpool", "EPL"));
        when(userPreferenceService.savePreference(eq(1L), any())).thenReturn(response);

        mockMvc.perform(put("/api/v1/users/me/preferences")
                        .cookie(VALID_COOKIE)
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.favoriteClub.name").value("Liverpool"));
    }

    @Test
    void favoriteClub이_없으면_응답의_favoriteClub은_null이다() throws Exception {
        UserPreferenceResponse response = new UserPreferenceResponse(
                List.of(new ClubResponse(1L, "Liverpool", "EPL")), 3, null);
        when(userPreferenceService.getPreference(1L)).thenReturn(response);

        mockMvc.perform(get("/api/v1/users/me/preferences").cookie(VALID_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.favoriteClub").doesNotExist());
    }

    @Test
    void 존재하지_않는_구단을_최애팀으로_지정하면_400을_반환한다() throws Exception {
        UserPreferenceRequest request = new UserPreferenceRequest(List.of(1L), 3, 999L);
        when(userPreferenceService.savePreference(eq(1L), any()))
                .thenThrow(new IllegalArgumentException("존재하지 않는 구단은 최애팀으로 지정할 수 없습니다: 999"));

        mockMvc.perform(put("/api/v1/users/me/preferences")
                        .cookie(VALID_COOKIE)
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }
}
