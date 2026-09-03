package com.liverpool.news.controller;

import com.liverpool.news.dto.UpdateNicknameRequest;
import com.liverpool.news.dto.UserResponse;
import com.liverpool.news.security.AuthenticatedUser;
import com.liverpool.news.security.OAuth2LoginSuccessHandler;
import com.liverpool.news.service.UserService;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/users/me")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @PatchMapping("/nickname")
    public UserResponse updateNickname(@AuthenticationPrincipal AuthenticatedUser user,
                                        @Valid @RequestBody UpdateNicknameRequest request) {
        return userService.updateNickname(user.id(), request.nickname());
    }

    @DeleteMapping
    public ResponseEntity<Void> deleteAccount(@AuthenticationPrincipal AuthenticatedUser user,
                                               HttpServletResponse response) {
        userService.deleteAccount(user.id());

        Cookie cookie = new Cookie(OAuth2LoginSuccessHandler.ACCESS_TOKEN_COOKIE, "");
        cookie.setHttpOnly(true);
        cookie.setPath("/");
        cookie.setMaxAge(0);
        response.addCookie(cookie);

        return ResponseEntity.noContent().build();
    }
}
