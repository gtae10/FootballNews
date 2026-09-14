package com.liverpool.news.controller;

import com.liverpool.news.config.SecurityConfig;
import com.liverpool.news.dto.ChatResponse;
import com.liverpool.news.exception.ChatRateLimitExceededException;
import com.liverpool.news.exception.ChatServiceException;
import com.liverpool.news.service.ChatService;
import com.liverpool.news.support.SecurityTestConfig;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ChatController.class)
@Import({SecurityConfig.class, SecurityTestConfig.class})
class ChatControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ChatService chatService;

    @Test
    void 정상_메시지는_200과_답변을_반환한다() throws Exception {
        when(chatService.chat(anyString(), any()))
                .thenReturn(new ChatResponse("안녕하세요! 433입니다.", 0, "GENERAL_KNOWLEDGE"));

        mockMvc.perform(post("/api/v1/chat")
                        .contentType("application/json")
                        .content("{\"message\": \"안녕하세요\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.reply").value("안녕하세요! 433입니다."));
    }

    @Test
    void 빈_메시지는_400을_반환한다() throws Exception {
        mockMvc.perform(post("/api/v1/chat")
                        .contentType("application/json")
                        .content("{\"message\": \"\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void 너무_긴_메시지는_400을_반환한다() throws Exception {
        String tooLong = "가".repeat(301);

        mockMvc.perform(post("/api/v1/chat")
                        .contentType("application/json")
                        .content("{\"message\": \"" + tooLong + "\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void 요청_한도_초과시_429를_반환한다() throws Exception {
        when(chatService.chat(anyString(), any()))
                .thenThrow(new ChatRateLimitExceededException("메시지를 너무 많이 보냈습니다. 잠시 후 다시 시도해주세요."));

        mockMvc.perform(post("/api/v1/chat")
                        .contentType("application/json")
                        .content("{\"message\": \"질문\"}"))
                .andExpect(status().isTooManyRequests());
    }

    @Test
    void 채팅_서비스_실패시_503을_반환한다() throws Exception {
        when(chatService.chat(anyString(), any()))
                .thenThrow(new ChatServiceException("OpenAI API 호출 실패"));

        mockMvc.perform(post("/api/v1/chat")
                        .contentType("application/json")
                        .content("{\"message\": \"질문\"}"))
                .andExpect(status().isServiceUnavailable());
    }
}
