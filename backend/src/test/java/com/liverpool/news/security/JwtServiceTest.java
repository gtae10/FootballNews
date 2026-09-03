package com.liverpool.news.security;

import org.junit.jupiter.api.Test;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

class JwtServiceTest {

    private final JwtService jwtService = new JwtService(
            "test-secret-key-for-jwt-signing-must-be-32-bytes-or-longer",
            10080
    );

    @Test
    void 발급한_토큰을_검증하면_동일한_사용자_정보를_반환한다() {
        String token = jwtService.issueToken(42L, "user@example.com");

        Optional<AuthenticatedUser> result = jwtService.parse(token);

        assertThat(result).isPresent();
        assertThat(result.get().id()).isEqualTo(42L);
        assertThat(result.get().email()).isEqualTo("user@example.com");
    }

    @Test
    void 만료된_토큰은_검증에_실패한다() {
        JwtService shortLivedService = new JwtService(
                "test-secret-key-for-jwt-signing-must-be-32-bytes-or-longer", 0);
        String token = shortLivedService.issueToken(1L, "user@example.com");

        Optional<AuthenticatedUser> result = shortLivedService.parse(token);

        assertThat(result).isEmpty();
    }

    @Test
    void 변조된_토큰은_검증에_실패한다() {
        String token = jwtService.issueToken(1L, "user@example.com");
        String tampered = token.substring(0, token.length() - 2) + "xx";

        assertThat(jwtService.parse(tampered)).isEmpty();
    }

    @Test
    void 다른_비밀키로_서명된_토큰은_검증에_실패한다() {
        JwtService otherService = new JwtService(
                "a-completely-different-secret-key-that-is-also-long-enough", 10080);
        String token = otherService.issueToken(1L, "user@example.com");

        assertThat(jwtService.parse(token)).isEmpty();
    }
}
