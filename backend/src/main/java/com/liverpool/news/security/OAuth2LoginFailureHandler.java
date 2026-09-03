package com.liverpool.news.security;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.web.authentication.AuthenticationFailureHandler;
import org.springframework.stereotype.Component;
import org.springframework.web.util.UriComponentsBuilder;

import java.io.IOException;

/**
 * 기본 실패 핸들러(SimpleUrlAuthenticationFailureHandler)는 이 백엔드에 존재하지 않는
 * "/login?error"로 리다이렉트한다. 정적 리소스도 컨트롤러도 없는 경로라 브라우저가 그대로
 * 백엔드(8080)에 멈춰 서고, NoResourceFoundException이 GlobalExceptionHandler의 500
 * catch-all("서버 오류가 발생했습니다.")로 처리되어 실제 인증 실패 사유와 무관한 메시지가 노출된다.
 * 프론트(SPA)는 5173에만 떠 있으므로, 로그인 실패도 성공 때(OAuth2LoginSuccessHandler)와
 * 마찬가지로 프론트로 돌려보내되 사유 코드를 함께 실어 보낸다.
 */
@Component
public class OAuth2LoginFailureHandler implements AuthenticationFailureHandler {

    private static final Logger log = LoggerFactory.getLogger(OAuth2LoginFailureHandler.class);

    private final String frontendBaseUrl;

    public OAuth2LoginFailureHandler(@Value("${app.frontend-base-url}") String frontendBaseUrl) {
        this.frontendBaseUrl = frontendBaseUrl;
    }

    @Override
    public void onAuthenticationFailure(HttpServletRequest request, HttpServletResponse response,
                                         AuthenticationException exception) throws IOException, ServletException {
        String reason = resolveReason(exception);
        int conceptualStatus = CustomOidcUserService.EMAIL_MISSING_ERROR_CODE.equals(reason) ? 400 : 401;
        log.error("구글 로그인 실패 (reason={}, status={}): {}", reason, conceptualStatus, exception.getMessage(), exception);

        String redirectUrl = UriComponentsBuilder.fromUriString(frontendBaseUrl)
                .path("/login")
                .queryParam("error", reason)
                .build()
                .toUriString();
        response.sendRedirect(redirectUrl);
    }

    private String resolveReason(AuthenticationException exception) {
        if (exception instanceof OAuth2AuthenticationException oAuth2Exception
                && oAuth2Exception.getError() != null
                && CustomOidcUserService.EMAIL_MISSING_ERROR_CODE.equals(oAuth2Exception.getError().getErrorCode())) {
            return CustomOidcUserService.EMAIL_MISSING_ERROR_CODE;
        }
        return "oauth_failed";
    }
}
