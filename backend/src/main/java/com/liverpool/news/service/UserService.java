package com.liverpool.news.service;

import com.liverpool.news.dto.UserResponse;
import com.liverpool.news.entity.User;
import com.liverpool.news.exception.UserNotFoundException;
import com.liverpool.news.repository.ReporterSuggestionRepository;
import com.liverpool.news.repository.UserPreferenceRepository;
import com.liverpool.news.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final UserPreferenceRepository userPreferenceRepository;
    private final ReporterSuggestionRepository reporterSuggestionRepository;

    public UserService(UserRepository userRepository,
                        UserPreferenceRepository userPreferenceRepository,
                        ReporterSuggestionRepository reporterSuggestionRepository) {
        this.userRepository = userRepository;
        this.userPreferenceRepository = userPreferenceRepository;
        this.reporterSuggestionRepository = reporterSuggestionRepository;
    }

    @Transactional
    public UserResponse updateNickname(Long userId, String nickname) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new UserNotFoundException("사용자를 찾을 수 없습니다: " + userId));

        user.setNickname(nickname);

        boolean onboarded = userPreferenceRepository.existsByUserId(userId);
        return new UserResponse(user.getId(), user.getEmail(), user.getNickname(), onboarded);
    }

    @Transactional
    public void deleteAccount(Long userId) {
        reporterSuggestionRepository.deleteAllByUserId(userId);
        userPreferenceRepository.deleteByUserId(userId);
        userRepository.deleteById(userId);
    }
}
