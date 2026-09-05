package com.liverpool.news.controller;

import com.liverpool.news.config.SecurityConfig;
import com.liverpool.news.dto.RumorThreadArticleResponse;
import com.liverpool.news.dto.RumorThreadDetailResponse;
import com.liverpool.news.dto.RumorThreadSummaryResponse;
import com.liverpool.news.exception.RumorThreadNotFoundException;
import com.liverpool.news.service.RumorThreadService;
import com.liverpool.news.support.SecurityTestConfig;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDateTime;
import java.util.List;

import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(RumorThreadController.class)
@Import({SecurityConfig.class, SecurityTestConfig.class})
class RumorThreadControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private RumorThreadService rumorThreadService;

    private RumorThreadSummaryResponse summary(long id, String playerName, int independentSourceCount, boolean crossReported) {
        return new RumorThreadSummaryResponse(
                id, playerName, "Liverpool", "INTEREST", independentSourceCount, crossReported,
                3L, LocalDateTime.of(2026, 8, 28, 9, 0), LocalDateTime.of(2026, 8, 30, 9, 0)
        );
    }

    @Test
    void 루머_스레드_목록_조회시_200_응답과_목록을_반환한다() throws Exception {
        when(rumorThreadService.getThreads(isNull()))
                .thenReturn(List.of(summary(1L, "Alexander Isak", 2, true)));

        mockMvc.perform(get("/api/v1/rumor-threads"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].playerName").value("Alexander Isak"))
                .andExpect(jsonPath("$[0].independentSourceCount").value(2))
                .andExpect(jsonPath("$[0].crossReported").value(true));
    }

    @Test
    void sort_파라미터를_서비스로_그대로_전달한다() throws Exception {
        when(rumorThreadService.getThreads(eq("latest")))
                .thenReturn(List.of(summary(1L, "Isak", 1, false)));

        mockMvc.perform(get("/api/v1/rumor-threads").param("sort", "latest"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].playerName").value("Isak"));
    }

    @Test
    void 루머_스레드_상세_조회시_기사_타임라인을_포함해_반환한다() throws Exception {
        RumorThreadArticleResponse article = new RumorThreadArticleResponse(
                10L, "The Anfield Wrap", null, "Liverpool make contact over Isak",
                "https://example.com/1", LocalDateTime.of(2026, 8, 28, 9, 0), "INTEREST"
        );
        RumorThreadDetailResponse detail = new RumorThreadDetailResponse(
                1L, "Alexander Isak", "Liverpool", "CONFIRMED", 2, true,
                LocalDateTime.of(2026, 8, 28, 9, 0), LocalDateTime.of(2026, 8, 30, 9, 0),
                List.of(article)
        );
        when(rumorThreadService.getThreadDetail(1L)).thenReturn(detail);

        mockMvc.perform(get("/api/v1/rumor-threads/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.playerName").value("Alexander Isak"))
                .andExpect(jsonPath("$.articles[0].storyStage").value("INTEREST"));
    }

    @Test
    void 존재하지_않는_루머_스레드_조회시_404를_반환한다() throws Exception {
        when(rumorThreadService.getThreadDetail(anyLong()))
                .thenThrow(new RumorThreadNotFoundException("루머 스레드를 찾을 수 없습니다: 999999"));

        mockMvc.perform(get("/api/v1/rumor-threads/999999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message").value("루머 스레드를 찾을 수 없습니다: 999999"));
    }
}
