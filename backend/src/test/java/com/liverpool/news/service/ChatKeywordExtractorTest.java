package com.liverpool.news.service;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class ChatKeywordExtractorTest {

    @Test
    void 조사를_제거하고_키워드_후보를_뽑는다() {
        List<String> keywords = ChatKeywordExtractor.extractKeywords("리버풀이 이번에 누구 영입했어요?");

        assertThat(keywords).contains("리버풀");
        assertThat(keywords).doesNotContain("이번에", "누구");
    }

    @Test
    void 흔한_질문_스톱워드는_제외한다() {
        List<String> keywords = ChatKeywordExtractor.extractKeywords("최근 이적 소식 알려주세요");

        assertThat(keywords).doesNotContain("최근", "소식", "알려주세요");
    }

    @Test
    void 빈_문자열이면_빈_목록을_반환한다() {
        assertThat(ChatKeywordExtractor.extractKeywords("")).isEmpty();
        assertThat(ChatKeywordExtractor.extractKeywords(null)).isEmpty();
        assertThat(ChatKeywordExtractor.extractKeywords("   ")).isEmpty();
    }

    @Test
    void 선수명과_구단명은_조사가_붙어도_원형이_추출된다() {
        List<String> keywords = ChatKeywordExtractor.extractKeywords("살라가 첼시로 이적하나요?");

        assertThat(keywords).contains("살라", "첼시");
    }

    @Test
    void 키워드_개수는_최대_8개로_제한된다() {
        List<String> keywords = ChatKeywordExtractor.extractKeywords(
                "가나다 라마바 사아자 차카타 파하거 너더러 머버서 어저처 커터퍼 허고노");

        assertThat(keywords).hasSizeLessThanOrEqualTo(8);
    }
}
