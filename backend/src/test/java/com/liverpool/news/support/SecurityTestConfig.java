package com.liverpool.news.support;

import com.liverpool.news.security.CustomOidcUserService;
import com.liverpool.news.security.JwtService;
import com.liverpool.news.security.OAuth2LoginFailureHandler;
import com.liverpool.news.security.OAuth2LoginSuccessHandler;
import org.mockito.Mockito;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;

@TestConfiguration
public class SecurityTestConfig {

    @Bean
    public CustomOidcUserService customOidcUserService() {
        return Mockito.mock(CustomOidcUserService.class);
    }

    @Bean
    public OAuth2LoginSuccessHandler oAuth2LoginSuccessHandler() {
        return Mockito.mock(OAuth2LoginSuccessHandler.class);
    }

    @Bean
    public OAuth2LoginFailureHandler oAuth2LoginFailureHandler() {
        return Mockito.mock(OAuth2LoginFailureHandler.class);
    }

    @Bean
    public JwtService jwtService() {
        return Mockito.mock(JwtService.class);
    }
}
