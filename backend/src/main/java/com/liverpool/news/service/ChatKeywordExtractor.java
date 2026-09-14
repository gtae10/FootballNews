package com.liverpool.news.service;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * 사용자의 채팅 메시지(한국어)에서 기사 검색에 쓸 키워드 후보를 뽑는다.
 * collector/player_extractor.py처럼 완벽한 개체명 인식이 아니라 규칙 기반
 * 휴리스틱이다 — 형태소 분석기 없이, 조사로 보이는 흔한 어미를 잘라내고
 * 질문에 흔히 쓰이는 일반 단어를 스톱워드로 제외하는 수준이다. 구단/선수명이
 * 아닌 단어가 섞여 들어와도(오탐) 실제 기사 본문과 매칭이 안 되면 그냥
 * 결과가 없을 뿐이라 크게 해롭지 않다.
 */
public final class ChatKeywordExtractor {

    private static final Pattern SPLIT_PATTERN = Pattern.compile("[\\s,.!?~\"'()\\[\\]:;/\\\\]+");

    // 길이가 긴 것부터 검사해야 "에서"를 "에"보다 먼저 잘라낼 수 있다.
    private static final List<String> PARTICLE_SUFFIXES = List.of(
            "에서는", "에게서", "이라는", "라는",
            "으로는", "에서", "에게", "한테", "처럼", "부터", "까지", "이랑", "이나", "이며",
            "으로", "이라", "라고", "이고",
            "은", "는", "이", "가", "을", "를", "의", "와", "과", "도", "만", "랑", "나", "에", "로"
    );

    private static final Set<String> STOPWORDS = Set.of(
            "이번", "최근", "요즘", "지금", "오늘", "어제", "내일",
            "어떻게", "무엇", "뭐", "뭔가", "누구", "어디", "언제", "왜", "얼마나",
            "진짜", "정말", "혹시", "그냥", "좀",
            "알려줘", "알려주세요", "궁금해요", "궁금합니다", "있나요", "했나요", "인가요", "됐나요",
            "뭐예요", "인가", "해줘", "주세요", "싶어요", "싶습니다",
            "소식", "기사", "뉴스", "관련", "대해", "대한", "관해"
    );

    private static final int MIN_KEYWORD_LENGTH = 2;
    private static final int MAX_KEYWORDS = 8;

    private ChatKeywordExtractor() {
    }

    public static List<String> extractKeywords(String message) {
        if (message == null || message.isBlank()) {
            return List.of();
        }

        Set<String> keywords = new LinkedHashSet<>();
        for (String token : SPLIT_PATTERN.split(message)) {
            String stripped = stripParticle(token);
            if (stripped.length() >= MIN_KEYWORD_LENGTH && !STOPWORDS.contains(stripped)) {
                keywords.add(stripped);
            }
            if (keywords.size() >= MAX_KEYWORDS) {
                break;
            }
        }
        return List.copyOf(keywords);
    }

    private static String stripParticle(String token) {
        for (String suffix : PARTICLE_SUFFIXES) {
            if (token.length() > suffix.length() + 1 && token.endsWith(suffix)) {
                return token.substring(0, token.length() - suffix.length());
            }
        }
        return token;
    }
}
