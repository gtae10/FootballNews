package com.liverpool.news.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.liverpool.news.config.SecurityConfig;
import com.liverpool.news.dto.ReporterSuggestionRequest;
import com.liverpool.news.dto.ReporterSuggestionResponse;
import com.liverpool.news.security.AuthenticatedUser;
import com.liverpool.news.security.JwtService;
import com.liverpool.news.service.ReporterSuggestionService;
import com.liverpool.news.support.SecurityTestConfig;
import jakarta.servlet.http.Cookie;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ReporterSuggestionController.class)
@Import({SecurityConfig.class, SecurityTestConfig.class})
class ReporterSuggestionControllerTest {

    private static final Cookie VALID_COOKIE = new Cookie("access_token", "valid-token");

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private ReporterSuggestionService reporterSuggestionService;

    @Autowired
    private JwtService jwtService;

    @BeforeEach
    void setUpAuth() {
        reset(jwtService);
        when(jwtService.parse("valid-token"))
                .thenReturn(Optional.of(new AuthenticatedUser(1L, "test@example.com")));
    }

    @Test
    void 인증_없이_제보_생성시_401을_반환한다() throws Exception {
        ReporterSuggestionRequest request = new ReporterSuggestionRequest("@some_reporter", null, null, null);

        mockMvc.perform(post("/api/v1/reporter-suggestions")
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 인증_없이_내_제보_목록_조회시_401을_반환한다() throws Exception {
        mockMvc.perform(get("/api/v1/reporter-suggestions/me"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 인증된_사용자가_기자_제보를_생성한다() throws Exception {
        ReporterSuggestionRequest request = new ReporterSuggestionRequest(
                "@some_reporter", "김기자", "EPL", "믿을만한 소식통");
        ReporterSuggestionResponse response = new ReporterSuggestionResponse(
                1L, "@some_reporter", "김기자", "EPL", "믿을만한 소식통", LocalDateTime.now());
        when(reporterSuggestionService.create(eq(1L), any())).thenReturn(response);

        mockMvc.perform(post("/api/v1/reporter-suggestions")
                        .cookie(VALID_COOKIE)
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.twitterHandle").value("@some_reporter"))
                .andExpect(jsonPath("$.league").value("EPL"));
    }

    @Test
    void 트위터_핸들이_비어있으면_400을_반환한다() throws Exception {
        ReporterSuggestionRequest request = new ReporterSuggestionRequest("", null, null, null);

        mockMvc.perform(post("/api/v1/reporter-suggestions")
                        .cookie(VALID_COOKIE)
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void 인증된_사용자가_자신의_제보_목록을_조회한다() throws Exception {
        when(reporterSuggestionService.listMine(1L)).thenReturn(List.of(
                new ReporterSuggestionResponse(1L, "@a", null, null, null, LocalDateTime.now()),
                new ReporterSuggestionResponse(2L, "@b", null, null, null, LocalDateTime.now())
        ));

        mockMvc.perform(get("/api/v1/reporter-suggestions/me").cookie(VALID_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2));
    }
}
