package com.liverpool.news.security;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;

@Component
public class OAuth2LoginSuccessHandler implements AuthenticationSuccessHandler {

    public static final String ACCESS_TOKEN_COOKIE = "access_token";

    private final JwtService jwtService;
    private final String frontendBaseUrl;

    public OAuth2LoginSuccessHandler(
            JwtService jwtService,
            @Value("${app.frontend-base-url}") String frontendBaseUrl
    ) {
        this.jwtService = jwtService;
        this.frontendBaseUrl = frontendBaseUrl;
    }

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request, HttpServletResponse response,
                                         Authentication authentication) throws IOException, ServletException {
        CustomOidcUserService.AppOidcUser user = (CustomOidcUserService.AppOidcUser) authentication.getPrincipal();
        String token = jwtService.issueToken(user.getUserId(), user.getEmail());

        Cookie cookie = new Cookie(ACCESS_TOKEN_COOKIE, token);
        cookie.setHttpOnly(true);
        cookie.setPath("/");
        cookie.setMaxAge((int) jwtService.getValidity().toSeconds());
        cookie.setAttribute("SameSite", "Lax");
        response.addCookie(cookie);

        response.sendRedirect(frontendBaseUrl);
    }
}
