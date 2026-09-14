package com.liverpool.news.service;

import com.liverpool.news.dto.ChatMessageDto;
import com.liverpool.news.dto.ChatRequest;
import com.liverpool.news.dto.ChatResponse;
import com.liverpool.news.entity.ChatFeedback;
import com.liverpool.news.exception.ChatRateLimitExceededException;
import com.liverpool.news.repository.ChatFeedbackRepository;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;

/**
 * "433" 뉴스 채팅 위젯의 RAG 오케스트레이션. 사용자 메시지 → 키워드 추출 →
 * 관련 기사 검색({@link ChatArticleSearchService}) → 시스템 프롬프트 + 컨텍스트 +
 * 대화 이력을 묶어 OpenAI 호출({@link OpenAiChatClient}) → 검토용 로그 저장
 * ({@link ChatFeedbackRepository}) 순서로 진행한다.
 *
 * 대화 이력 자체는 서버에 저장하지 않는다 — 클라이언트가 매 요청마다 이전 턴을
 * 함께 보낸다({@link ChatRequest#history()}). {@link ChatFeedbackRepository}는
 * 그와 별개로 "이번 턴의 질문/답변"만 검토용으로 남기는 로그다.
 */
@Service
public class ChatService {

    // 프론트가 이미 길이를 제한해 보내지만, 백엔드도 방어적으로 다시 자른다 —
    // 클라이언트를 신뢰하지 않는다.
    private static final int MAX_HISTORY_TURNS = 10;
    private static final int MAX_HISTORY_CONTENT_LENGTH = 300;

    private static final String ARTICLE_TAG = "[저장된 기사 기반]";
    private static final String GENERAL_KNOWLEDGE_TAG = "[AI 일반 지식";

    private static final String SYSTEM_PROMPT = """
            당신은 해외축구 뉴스 앱 "433"의 채팅 도우미입니다. 433은 해외축구(5대 리그) \
            뉴스를 RSS/크롤링으로 수집해 한국어로 요약 번역하고, 각 기사에 출처 신뢰도 \
            등급과 이적설 진행 단계를 함께 보여주는 서비스입니다.

            [신뢰도 등급 — 숫자가 낮을수록 신뢰도가 높습니다]
            - T1 공식 발표: 구단/선수 공식 채널 발표
            - T2 검증된 매체: Sky Sports, BBC 등 대형/공식 매체
            - T3 유력 기자: Fabrizio Romano 등 신뢰도 높은 기자가 인용된 기사
            - T4 지역 매체: 지역 매체 보도
            - T5 루머: 그 외 출처, 아직 근거가 약한 소문 수준

            [이적설 진행 단계]
            UNKNOWN(단계 불명) < INTEREST(관심/링크설) < NEGOTIATION(협상 중) \
            < CONFIRMED(다수 매체가 합의 보도, 공식 발표는 아직 아님) < OFFICIAL(구단 공식 발표)

            [교차검증]
            같은 이적 건을 48시간 이내에 서로 다른 매체 여러 곳이 독립적으로 보도하면 \
            "교차보도"로 표시됩니다. 이는 "여러 매체가 같은 이야기를 하고 있다"는 뜻일 \
            뿐, "이적이 사실로 확정됐다"는 뜻이 절대 아닙니다.

            [답변 규칙]
            1. 433 자체(신뢰도 등급, 이적설 단계, 교차검증의 의미)에 대한 질문은 위 설명을 \
               바탕으로 자유롭게 답하세요.
            2. 특정 기사/이적설/선수/구단 소식에 대한 질문이고 이번 메시지에 함께 제공되는 \
               "[검색된 기사]" 목록에 실제로 질문과 관련된 기사가 있으면, 반드시 그 \
               목록에 근거해서만 답하세요. 목록에 없는 내용을 지어내지 마세요. 답변 맨 \
               앞에 "[저장된 기사 기반]" 표시를 붙이고, 며칠/몇 시간 전 기사인지, 어느 \
               매체 출처인지, 신뢰도 등급이 무엇인지를 항상 함께 언급하세요.
               주의: "[검색된 기사]" 목록은 키워드로 기계적으로 찾은 것이라 목록에 \
               기사가 있어도 실제로는 질문과 무관할 수 있습니다. 목록의 기사들이 질문과 \
               관련이 없다면 그 기사들을 근거로 쓰지 말고, 대신 3번 규칙(관련 기사 \
               없음)을 따르세요.
            3. "[검색된 기사]"가 비어 있거나, "관련된 기사를 찾지 못했습니다"로 \
               표시되거나, 목록에 기사가 있어도 질문과 실제로 관련이 없으면, 저장된 \
               기사를 근거로 쓰지 말고 대신 당신의 일반 지식으로 답하세요. 이때는 \
               반드시 다음을 지키세요:
               - 답변 맨 앞에 "[AI 일반 지식 — 최신 정보 아닐 수 있음]" 표시를 붙이세요.
               - "최근 이적했다/영입했다/방출됐다/부상당했다"처럼 시점이 중요한 사실은 \
                 확실하지 않으면 절대 확정적으로 말하지 마세요. "제가 알기로는 ~였는데, \
                 최근 변동이 있었을 수 있어 확실친 않습니다" 같은 식으로 불확실성을 \
                 명시하세요.
               - 반대로 역대 기록, 규칙, 일반적인 배경지식(예: 챔피언스리그가 무엇인지, \
                 역대 발롱도르 수상자)처럼 시점과 무관한 질문에는 비교적 자신 있게 \
                 답해도 되지만, 그래도 "[AI 일반 지식]" 표시는 그대로 유지하세요.
               - 답변 끝에 "최신 이적 소식이나 특정 시점 정보는 이 앱에 수집된 기사를 \
                 확인하시는 게 정확합니다" 같은 안내를 한 줄 덧붙이세요.
            4. "[저장된 기사 기반]"과 "[AI 일반 지식]" 두 종류를 절대 한 답변 안에서 \
               표시 없이 섞지 마세요. 2번 또는 3번에 해당하는 답변은 예외 없이 항상 \
               두 표시 중 하나로 시작해야 합니다.
            5. 확인되지 않은 이적설을 확정된 사실처럼 말하지 마세요. "이적이 확정됐다" \
               대신 "N개 매체가 보도했고 아직 공식 발표는 아닙니다" 같은 식으로, 이 \
               서비스의 신뢰도 원칙을 그대로 지키세요.
            6. 사용자가 "이 선수 진짜 이적하나요?" 같은 확답을 요구해도 확정 답변을 \
               피하고, 대신 신뢰도 등급/이적설 단계/교차검증 여부를 안내해 사용자가 \
               스스로 판단하도록 도우세요.
            7. 사용자의 의견이나 피드백은 편하게 받고 정중하게 감사를 표하세요.
            8. 한국어로, 간결하게 답하세요.
            """;

    private final ChatArticleSearchService chatArticleSearchService;
    private final OpenAiChatClient openAiChatClient;
    private final ChatFeedbackRepository chatFeedbackRepository;
    private final ChatRateLimiter chatRateLimiter;

    public ChatService(
            ChatArticleSearchService chatArticleSearchService,
            OpenAiChatClient openAiChatClient,
            ChatFeedbackRepository chatFeedbackRepository,
            ChatRateLimiter chatRateLimiter
    ) {
        this.chatArticleSearchService = chatArticleSearchService;
        this.openAiChatClient = openAiChatClient;
        this.chatFeedbackRepository = chatFeedbackRepository;
        this.chatRateLimiter = chatRateLimiter;
    }

    public ChatResponse chat(String clientKey, ChatRequest request) {
        if (!chatRateLimiter.tryAcquire(clientKey)) {
            throw new ChatRateLimitExceededException("메시지를 너무 많이 보냈습니다. 잠시 후 다시 시도해주세요.");
        }

        List<ChatContextArticle> contextArticles = chatArticleSearchService.search(request.message());

        List<OpenAiChatClient.Message> messages = new ArrayList<>();
        messages.add(new OpenAiChatClient.Message("system", SYSTEM_PROMPT));
        messages.addAll(buildHistoryMessages(request.history()));
        messages.add(new OpenAiChatClient.Message("user", buildUserTurn(request.message(), contextArticles)));

        String reply = openAiChatClient.chat(messages);

        chatFeedbackRepository.save(new ChatFeedback(request.message(), reply, contextArticles.size()));

        return new ChatResponse(reply, contextArticles.size(), detectSourceType(reply, contextArticles));
    }

    /**
     * 프론트 태그(초록 "저장된 기사 기반" vs 회색 "AI 일반 지식")를 어떤 신호로 결정할지가
     * 중요하다. matchedArticleCount만 보면 안 된다 — 키워드 검색은 기계적이라 관련 없는
     * 기사가 몇 건 걸려도, 모델이 그걸 무시하고 일반 지식으로 답할 수 있다(실제로 라이브
     * 테스트에서 "1966년 월드컵 우승팀" 질문에 현재 진행 중인 월드컵 예선 기사가 엉뚱하게
     * 걸렸는데, 모델은 그 기사를 무시하고 정답을 냈다). 그래서 모델이 답변 맨 앞에 실제로
     * 붙인 표시를 최우선으로 신뢰하고, 모델이 규칙을 안 지켜 표시가 없을 때만 검색 결과
     * 유무로 보수적으로 추정한다.
     */
    private String detectSourceType(String reply, List<ChatContextArticle> contextArticles) {
        String trimmed = reply == null ? "" : reply.stripLeading();
        if (trimmed.startsWith(ARTICLE_TAG)) {
            return "ARTICLE";
        }
        if (trimmed.startsWith(GENERAL_KNOWLEDGE_TAG)) {
            return "GENERAL_KNOWLEDGE";
        }
        return contextArticles.isEmpty() ? "GENERAL_KNOWLEDGE" : "ARTICLE";
    }

    private List<OpenAiChatClient.Message> buildHistoryMessages(List<ChatMessageDto> history) {
        if (history == null || history.isEmpty()) {
            return List.of();
        }
        int fromIndex = Math.max(0, history.size() - MAX_HISTORY_TURNS);
        List<OpenAiChatClient.Message> result = new ArrayList<>();
        for (ChatMessageDto turn : history.subList(fromIndex, history.size())) {
            String role = "assistant".equals(turn.role()) ? "assistant" : "user";
            String content = turn.content() == null ? "" : turn.content();
            if (content.length() > MAX_HISTORY_CONTENT_LENGTH) {
                content = content.substring(0, MAX_HISTORY_CONTENT_LENGTH);
            }
            result.add(new OpenAiChatClient.Message(role, content));
        }
        return result;
    }

    private String buildUserTurn(String userMessage, List<ChatContextArticle> contextArticles) {
        StringBuilder sb = new StringBuilder();
        sb.append("[검색된 기사]\n");
        if (contextArticles.isEmpty()) {
            sb.append("관련된 기사를 찾지 못했습니다.\n");
        } else {
            for (ChatContextArticle article : contextArticles) {
                sb.append("- [").append(tierLabel(article.sourceTier())).append("] ")
                        .append(article.source()).append(" · ")
                        .append(timeAgo(article.publishedAt())).append(" · ")
                        .append(article.title()).append('\n')
                        .append("  ").append(article.excerpt()).append('\n');
                if (article.rumorStage() != null) {
                    sb.append("  (이적설 단계: ").append(article.rumorStage());
                    if (Boolean.TRUE.equals(article.crossReported())) {
                        sb.append(", ").append(article.independentSourceCount()).append("개 매체 교차보도");
                    }
                    sb.append(")\n");
                }
            }
        }
        sb.append("\n[사용자 질문]\n").append(userMessage);
        return sb.toString();
    }

    private String tierLabel(Integer sourceTier) {
        int tier = sourceTier == null ? 5 : Math.min(Math.max(sourceTier, 1), 5);
        return switch (tier) {
            case 1 -> "T1 공식 발표";
            case 2 -> "T2 검증된 매체";
            case 3 -> "T3 유력 기자";
            case 4 -> "T4 지역 매체";
            default -> "T5 루머";
        };
    }

    private String timeAgo(LocalDateTime publishedAt) {
        if (publishedAt == null) {
            return "발행일 미상";
        }
        long minutes = Duration.between(publishedAt, LocalDateTime.now()).toMinutes();
        if (minutes < 1) {
            return "방금";
        }
        if (minutes < 60) {
            return minutes + "분 전";
        }
        if (minutes < 1440) {
            return (minutes / 60) + "시간 전";
        }
        long days = ChronoUnit.DAYS.between(publishedAt.toLocalDate(), LocalDateTime.now().toLocalDate());
        return days + "일 전";
    }
}
