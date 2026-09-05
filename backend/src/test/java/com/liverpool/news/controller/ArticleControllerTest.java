package com.liverpool.news.controller;

import com.liverpool.news.config.SecurityConfig;
import com.liverpool.news.dto.ArticleSummaryResponse;
import com.liverpool.news.exception.ArticleNotFoundException;
import com.liverpool.news.service.ArticleService;
import com.liverpool.news.support.SecurityTestConfig;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.data.domain.PageImpl;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDateTime;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.when;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

@WebMvcTest(ArticleController.class)
@Import({SecurityConfig.class, SecurityTestConfig.class})
class ArticleControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ArticleService articleService;

    private ArticleSummaryResponse summary(long id, String titleKo, int sourceTier) {
        return new ArticleSummaryResponse(
                id, titleKo, "Liverpool FC 공식",
                LocalDateTime.of(2026, 8, 30, 10, 0),
                "https://example.com/article/" + id,
                List.of("Liverpool"), sourceTier, null
        );
    }

    @Test
    void 기사_목록_조회시_200_응답과_기사_목록을_반환한다() throws Exception {
        when(articleService.getArticles(any(), isNull(), isNull()))
                .thenReturn(new PageImpl<>(List.of(summary(1L, "리버풀, 다음 시즌 새 유니폼 공개", 1))));

        mockMvc.perform(get("/api/v1/articles"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content[0].id").value(1))
                .andExpect(jsonPath("$.content[0].titleKo").value("리버풀, 다음 시즌 새 유니폼 공개"));
    }

    @Test
    void club_파라미터로_기사_목록을_필터링한다() throws Exception {
        when(articleService.getArticles(any(), eq("Liverpool"), isNull()))
                .thenReturn(new PageImpl<>(List.of(summary(1L, "필터링된 기사", 1))));

        mockMvc.perform(get("/api/v1/articles").param("club", "Liverpool"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content[0].titleKo").value("필터링된 기사"));
    }

    @Test
    void keyword_파라미터로_기사_목록을_필터링한다() throws Exception {
        when(articleService.getArticles(any(), isNull(), eq("유니폼")))
                .thenReturn(new PageImpl<>(List.of(summary(1L, "리버풀, 다음 시즌 새 유니폼 공개", 1))));

        mockMvc.perform(get("/api/v1/articles").param("keyword", "유니폼"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content[0].titleKo").value("리버풀, 다음 시즌 새 유니폼 공개"));
    }

    @Test
    void club과_keyword를_함께_넘기면_둘_다_서비스로_전달된다() throws Exception {
        when(articleService.getArticles(any(), eq("Liverpool"), eq("유니폼")))
                .thenReturn(new PageImpl<>(List.of(summary(1L, "리버풀, 다음 시즌 새 유니폼 공개", 1))));

        mockMvc.perform(get("/api/v1/articles").param("club", "Liverpool").param("keyword", "유니폼"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content[0].titleKo").value("리버풀, 다음 시즌 새 유니폼 공개"));
    }

    @Test
    void 오늘의_주요_소식은_발행시각과_신뢰도순으로_반환된다() throws Exception {
        when(articleService.getTopArticles(anyInt()))
                .thenReturn(List.of(
                        summary(1L, "1순위 기사", 1),
                        summary(2L, "2순위 기사", 2)
                ));

        mockMvc.perform(get("/api/v1/articles/top").param("limit", "5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].titleKo").value("1순위 기사"))
                .andExpect(jsonPath("$[1].titleKo").value("2순위 기사"));
    }

    @Test
    void 존재하지_않는_기사_조회시_404를_반환한다() throws Exception {
        when(articleService.getArticleDetail(anyLong()))
                .thenThrow(new ArticleNotFoundException("기사를 찾을 수 없습니다: 999999"));

        mockMvc.perform(get("/api/v1/articles/999999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message").value("기사를 찾을 수 없습니다: 999999"));
    }
}
