package com.liverpool.news.security;

import com.liverpool.news.entity.User;
import com.liverpool.news.repository.UserRepository;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserRequest;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserService;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.security.oauth2.core.oidc.user.OidcUserAuthority;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class CustomOidcUserService extends OidcUserService {

    public static final String EMAIL_MISSING_ERROR_CODE = "email_missing";

    private final UserRepository userRepository;

    public CustomOidcUserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @Override
    public OidcUser loadUser(OidcUserRequest userRequest) {
        OidcUser oidcUser = super.loadUser(userRequest);

        String email = oidcUser.getEmail();
        if (email == null || email.isBlank()) {
            // Spring Security의 OAuth2 로그인 필터 체인은 AuthenticationException(과 그 하위 타입)만
            // AuthenticationFailureHandler로 넘긴다. 여기서 일반 RuntimeException(IllegalStateException 등)을
            // 던지면 필터 체인을 그대로 뚫고 나가 GlobalExceptionHandler도, 등록된 실패 핸들러도 거치지 못한 채
            // 컨테이너 기본 에러 페이지로 떨어진다. 그래서 반드시 OAuth2AuthenticationException으로 던져야
            // OAuth2LoginFailureHandler가 이 실패를 정상적으로 처리할 수 있다.
            throw new OAuth2AuthenticationException(
                    new OAuth2Error(EMAIL_MISSING_ERROR_CODE, "구글 계정에서 이메일 정보를 가져올 수 없습니다.", null));
        }

        User user = userRepository.findByEmail(email)
                .orElseGet(() -> userRepository.save(new User(email, oidcUser.getFullName())));

        return new AppOidcUser(user.getId(), oidcUser, List.of(new OidcUserAuthority(oidcUser.getIdToken(), oidcUser.getUserInfo())));
    }

    public static class AppOidcUser extends org.springframework.security.oauth2.core.oidc.user.DefaultOidcUser {
        private final Long userId;

        public AppOidcUser(Long userId, OidcUser oidcUser, List<OidcUserAuthority> authorities) {
            super(authorities, oidcUser.getIdToken(), oidcUser.getUserInfo());
            this.userId = userId;
        }

        public Long getUserId() {
            return userId;
        }
    }
}
