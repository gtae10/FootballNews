package com.liverpool.news.controller;

import com.liverpool.news.config.SecurityConfig;
import com.liverpool.news.dto.UserResponse;
import com.liverpool.news.security.AuthenticatedUser;
import com.liverpool.news.security.JwtService;
import com.liverpool.news.service.AuthService;
import com.liverpool.news.support.SecurityTestConfig;
import jakarta.servlet.http.Cookie;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Optional;

import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(AuthController.class)
@Import({SecurityConfig.class, SecurityTestConfig.class})
class AuthControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private AuthService authService;

    @Autowired
    private JwtService jwtService;

    @BeforeEach
    void resetJwtServiceMock() {
        reset(jwtService);
    }

    @Test
    void 인증_없이_보호된_API_접근시_401을_반환한다() throws Exception {
        mockMvc.perform(get("/api/v1/auth/me"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 잘못된_토큰으로_접근시_401을_반환한다() throws Exception {
        when(jwtService.parse("invalid-token")).thenReturn(Optional.empty());

        mockMvc.perform(get("/api/v1/auth/me").cookie(new Cookie("access_token", "invalid-token")))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 유효한_토큰으로_접근시_현재_사용자_정보를_반환한다() throws Exception {
        when(jwtService.parse("valid-token"))
                .thenReturn(Optional.of(new AuthenticatedUser(1L, "test@example.com")));
        when(authService.getCurrentUser(1L))
                .thenReturn(new UserResponse(1L, "test@example.com", null, false));

        mockMvc.perform(get("/api/v1/auth/me").cookie(new Cookie("access_token", "valid-token")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(1))
                .andExpect(jsonPath("$.email").value("test@example.com"))
                .andExpect(jsonPath("$.onboarded").value(false));
    }

    @Test
    void 로그아웃시_쿠키를_만료시키고_200을_반환한다() throws Exception {
        when(jwtService.parse("valid-token"))
                .thenReturn(Optional.of(new AuthenticatedUser(1L, "test@example.com")));

        mockMvc.perform(post("/api/v1/auth/logout").cookie(new Cookie("access_token", "valid-token")))
                .andExpect(status().isOk())
                .andExpect(result -> {
                    Cookie cookie = result.getResponse().getCookie("access_token");
                    org.junit.jupiter.api.Assertions.assertNotNull(cookie);
                    org.junit.jupiter.api.Assertions.assertEquals(0, cookie.getMaxAge());
                });
    }
}
