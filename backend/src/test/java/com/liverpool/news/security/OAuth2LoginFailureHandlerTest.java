package com.liverpool.news.security;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.OAuth2Error;

import static org.assertj.core.api.Assertions.assertThat;

class OAuth2LoginFailureHandlerTest {

    private final OAuth2LoginFailureHandler handler = new OAuth2LoginFailureHandler("http://localhost:5173");

    @Test
    void 이메일_누락_예외는_email_missing_사유로_프론트_로그인_페이지로_리다이렉트한다() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpServletResponse response = new MockHttpServletResponse();
        OAuth2AuthenticationException exception = new OAuth2AuthenticationException(
                new OAuth2Error(CustomOidcUserService.EMAIL_MISSING_ERROR_CODE, "구글 계정에서 이메일 정보를 가져올 수 없습니다.", null));

        handler.onAuthenticationFailure(request, response, exception);

        assertThat(response.getRedirectedUrl()).isEqualTo("http://localhost:5173/login?error=email_missing");
    }

    @Test
    void 토큰_교환_실패_등_그_외_인증_예외는_oauth_failed_사유로_프론트_로그인_페이지로_리다이렉트한다() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpServletResponse response = new MockHttpServletResponse();
        OAuth2AuthenticationException exception = new OAuth2AuthenticationException(
                new OAuth2Error("invalid_token_response", "액세스 토큰 응답을 가져오는 중 오류가 발생했습니다.", null));

        handler.onAuthenticationFailure(request, response, exception);

        assertThat(response.getRedirectedUrl()).isEqualTo("http://localhost:5173/login?error=oauth_failed");
    }
}
