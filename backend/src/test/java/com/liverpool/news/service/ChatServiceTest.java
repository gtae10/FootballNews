package com.liverpool.news.service;

import com.liverpool.news.dto.ChatMessageDto;
import com.liverpool.news.dto.ChatRequest;
import com.liverpool.news.dto.ChatResponse;
import com.liverpool.news.entity.ChatFeedback;
import com.liverpool.news.exception.ChatRateLimitExceededException;
import com.liverpool.news.repository.ChatFeedbackRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ChatServiceTest {

    @Mock
    private ChatArticleSearchService chatArticleSearchService;
    @Mock
    private OpenAiChatClient openAiChatClient;
    @Mock
    private ChatFeedbackRepository chatFeedbackRepository;
    @Mock
    private ChatRateLimiter chatRateLimiter;

    private ChatService service;

    @BeforeEach
    void setUp() {
        service = new ChatService(chatArticleSearchService, openAiChatClient, chatFeedbackRepository, chatRateLimiter);
        lenient().when(chatRateLimiter.tryAcquire(anyString())).thenReturn(true);
    }

    @Test
    void 관련_기사를_찾으면_컨텍스트에_담아_LLM에_전달하고_답변을_저장한다() {
        ChatContextArticle article = new ChatContextArticle(
                1L, "리버풀 새 미드필더 영입", "리버풀이 미드필더를 영입했다.", "Sky Sports Football", 1,
                LocalDateTime.now().minusHours(3), null, null, null);
        when(chatArticleSearchService.search("리버풀 누구 영입했어요?")).thenReturn(List.of(article));
        when(openAiChatClient.chat(any())).thenReturn("[저장된 기사 기반]\n리버풀은 최근 미드필더를 영입했습니다.");

        ChatResponse response = service.chat("1.2.3.4", new ChatRequest("리버풀 누구 영입했어요?", null));

        assertThat(response.reply()).isEqualTo("[저장된 기사 기반]\n리버풀은 최근 미드필더를 영입했습니다.");
        assertThat(response.matchedArticleCount()).isEqualTo(1);
        assertThat(response.sourceType()).isEqualTo("ARTICLE");

        ArgumentCaptor<List<OpenAiChatClient.Message>> messagesCaptor = ArgumentCaptor.forClass(List.class);
        verify(openAiChatClient).chat(messagesCaptor.capture());
        String userTurn = messagesCaptor.getValue().get(messagesCaptor.getValue().size() - 1).content();
        assertThat(userTurn).contains("리버풀 새 미드필더 영입");
        assertThat(userTurn).contains("Sky Sports Football");
        assertThat(userTurn).contains("T1 공식 발표");

        ArgumentCaptor<ChatFeedback> feedbackCaptor = ArgumentCaptor.forClass(ChatFeedback.class);
        verify(chatFeedbackRepository).save(feedbackCaptor.capture());
        assertThat(feedbackCaptor.getValue().getMatchedArticleCount()).isEqualTo(1);
    }

    @Test
    void 관련_기사가_없으면_컨텍스트가_비었다고_명시해_지어내지_않게_한다() {
        when(chatArticleSearchService.search(anyString())).thenReturn(List.of());
        when(openAiChatClient.chat(any())).thenReturn("[AI 일반 지식 — 최신 정보 아닐 수 있음]\n관련된 기사를 찾지 못했습니다.");

        ChatResponse response = service.chat("1.2.3.4", new ChatRequest("펩 과르디올라가 리버풀 감독 되나요?", null));

        assertThat(response.matchedArticleCount()).isZero();
        assertThat(response.sourceType()).isEqualTo("GENERAL_KNOWLEDGE");

        ArgumentCaptor<List<OpenAiChatClient.Message>> messagesCaptor = ArgumentCaptor.forClass(List.class);
        verify(openAiChatClient).chat(messagesCaptor.capture());
        String userTurn = messagesCaptor.getValue().get(messagesCaptor.getValue().size() - 1).content();
        assertThat(userTurn).contains("관련된 기사를 찾지 못했습니다.");
    }

    @Test
    void 시스템_프롬프트가_저장된_기사와_AI_일반지식_표시_규칙을_모두_포함한다() {
        when(chatArticleSearchService.search(anyString())).thenReturn(List.of());
        when(openAiChatClient.chat(any())).thenReturn("답변");

        service.chat("1.2.3.4", new ChatRequest("발롱도르가 뭐야?", null));

        ArgumentCaptor<List<OpenAiChatClient.Message>> messagesCaptor = ArgumentCaptor.forClass(List.class);
        verify(openAiChatClient).chat(messagesCaptor.capture());
        String systemPrompt = messagesCaptor.getValue().get(0).content();

        assertThat(systemPrompt).contains("[저장된 기사 기반]");
        assertThat(systemPrompt).contains("[AI 일반 지식 — 최신 정보 아닐 수 있음]");
        assertThat(systemPrompt).contains("확실친 않습니다");
    }

    @Test
    void 모델이_표시를_안_붙이면_검색된_기사_유무로_출처_종류를_추정한다() {
        // 라이브 테스트에서 실제로 발견된 사례: 키워드 검색이 질문과 무관한 기사를
        // 몇 건 걸러냈는데, 모델이 그 기사들을 무시하고 일반 지식으로 답하면서도
        // 규칙을 안 지켜 [AI 일반 지식] 표시를 안 붙인 경우가 있었다. 이때
        // matchedArticleCount만 보고 추정하면 실제로는 일반 지식 답변인데
        // "저장된 기사 기반"으로 잘못 표시될 수 있다는 한계가 있다 — 그래도 표시가
        // 아예 없을 때의 보수적 fallback으로만 쓰인다.
        ChatContextArticle irrelevant = new ChatContextArticle(
                1L, "무관한 기사", "무관한 내용", "Sky Sports Football", 1, LocalDateTime.now(), null, null, null);
        when(chatArticleSearchService.search(anyString())).thenReturn(List.of(irrelevant));
        when(openAiChatClient.chat(any())).thenReturn("표시 없이 그냥 답변만 온 경우");

        ChatResponse response = service.chat("1.2.3.4", new ChatRequest("질문", null));

        assertThat(response.sourceType()).isEqualTo("ARTICLE");
    }

    @Test
    void 이전_대화_이력을_함께_전달한다() {
        when(chatArticleSearchService.search(anyString())).thenReturn(List.of());
        when(openAiChatClient.chat(any())).thenReturn("답변");

        service.chat("1.2.3.4", new ChatRequest("추가 질문",
                List.of(new ChatMessageDto("user", "첫 질문"), new ChatMessageDto("assistant", "첫 답변"))));

        ArgumentCaptor<List<OpenAiChatClient.Message>> messagesCaptor = ArgumentCaptor.forClass(List.class);
        verify(openAiChatClient).chat(messagesCaptor.capture());
        List<OpenAiChatClient.Message> messages = messagesCaptor.getValue();

        assertThat(messages.get(0).role()).isEqualTo("system");
        assertThat(messages.get(1).content()).isEqualTo("첫 질문");
        assertThat(messages.get(2).content()).isEqualTo("첫 답변");
    }

    @Test
    void 요청_한도를_넘으면_예외를_던지고_LLM을_호출하지_않는다() {
        when(chatRateLimiter.tryAcquire("1.2.3.4")).thenReturn(false);

        assertThatThrownBy(() -> service.chat("1.2.3.4", new ChatRequest("질문", null)))
                .isInstanceOf(ChatRateLimitExceededException.class);

        verify(openAiChatClient, never()).chat(any());
    }
}
