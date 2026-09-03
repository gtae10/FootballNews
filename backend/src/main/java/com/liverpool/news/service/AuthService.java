package com.liverpool.news.service;

import com.liverpool.news.dto.UserResponse;
import com.liverpool.news.entity.User;
import com.liverpool.news.exception.UserNotFoundException;
import com.liverpool.news.repository.UserPreferenceRepository;
import com.liverpool.news.repository.UserRepository;
import org.springframework.stereotype.Service;

@Service
public class AuthService {

    private final UserRepository userRepository;
    private final UserPreferenceRepository userPreferenceRepository;

    public AuthService(UserRepository userRepository, UserPreferenceRepository userPreferenceRepository) {
        this.userRepository = userRepository;
        this.userPreferenceRepository = userPreferenceRepository;
    }

    public UserResponse getCurrentUser(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new UserNotFoundException("사용자를 찾을 수 없습니다: " + userId));

        boolean onboarded = userPreferenceRepository.existsByUserId(userId);
        return new UserResponse(user.getId(), user.getEmail(), user.getNickname(), onboarded);
    }
}
