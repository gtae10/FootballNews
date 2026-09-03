package com.liverpool.news.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.liverpool.news.config.SecurityConfig;
import com.liverpool.news.dto.UpdateNicknameRequest;
import com.liverpool.news.dto.UserResponse;
import com.liverpool.news.security.AuthenticatedUser;
import com.liverpool.news.security.JwtService;
import com.liverpool.news.service.UserService;
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
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(UserController.class)
@Import({SecurityConfig.class, SecurityTestConfig.class})
class UserControllerTest {

    private static final Cookie VALID_COOKIE = new Cookie("access_token", "valid-token");

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private UserService userService;

    @Autowired
    private JwtService jwtService;

    @BeforeEach
    void setUpAuth() {
        reset(jwtService);
        when(jwtService.parse("valid-token"))
                .thenReturn(Optional.of(new AuthenticatedUser(1L, "test@example.com")));
    }

    @Test
    void 인증_없이_닉네임_변경시_401을_반환한다() throws Exception {
        UpdateNicknameRequest request = new UpdateNicknameRequest("리버풀팬");

        mockMvc.perform(patch("/api/v1/users/me/nickname")
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 인증_없이_탈퇴시_401을_반환한다() throws Exception {
        mockMvc.perform(delete("/api/v1/users/me"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 인증된_사용자가_닉네임을_변경한다() throws Exception {
        UpdateNicknameRequest request = new UpdateNicknameRequest("리버풀팬");
        when(userService.updateNickname(1L, "리버풀팬"))
                .thenReturn(new UserResponse(1L, "test@example.com", "리버풀팬", true));

        mockMvc.perform(patch("/api/v1/users/me/nickname")
                        .cookie(VALID_COOKIE)
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.nickname").value("리버풀팬"));
    }

    @Test
    void 닉네임이_비어있으면_400을_반환한다() throws Exception {
        UpdateNicknameRequest request = new UpdateNicknameRequest("");

        mockMvc.perform(patch("/api/v1/users/me/nickname")
                        .cookie(VALID_COOKIE)
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void 인증된_사용자가_계정을_탈퇴하면_204와_함께_인증_쿠키를_만료시킨다() throws Exception {
        mockMvc.perform(delete("/api/v1/users/me").cookie(VALID_COOKIE))
                .andExpect(status().isNoContent())
                .andExpect(result -> {
                    Cookie cookie = result.getResponse().getCookie("access_token");
                    org.junit.jupiter.api.Assertions.assertNotNull(cookie);
                    org.junit.jupiter.api.Assertions.assertEquals(0, cookie.getMaxAge());
                });

        verify(userService).deleteAccount(1L);
    }
}
