package com.liverpool.news.service;

import com.liverpool.news.dto.ClubResponse;
import com.liverpool.news.dto.UserPreferenceRequest;
import com.liverpool.news.dto.UserPreferenceResponse;
import com.liverpool.news.entity.Club;
import com.liverpool.news.entity.User;
import com.liverpool.news.entity.UserPreference;
import com.liverpool.news.exception.OnboardingRequiredException;
import com.liverpool.news.exception.UserNotFoundException;
import com.liverpool.news.repository.ClubRepository;
import com.liverpool.news.repository.UserPreferenceRepository;
import com.liverpool.news.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

@Service
public class UserPreferenceService {

    private final UserPreferenceRepository userPreferenceRepository;
    private final UserRepository userRepository;
    private final ClubRepository clubRepository;

    public UserPreferenceService(UserPreferenceRepository userPreferenceRepository,
                                  UserRepository userRepository,
                                  ClubRepository clubRepository) {
        this.userPreferenceRepository = userPreferenceRepository;
        this.userRepository = userRepository;
        this.clubRepository = clubRepository;
    }

    public UserPreferenceResponse getPreference(Long userId) {
        UserPreference preference = userPreferenceRepository.findByUserId(userId)
                .orElseThrow(() -> new OnboardingRequiredException("아직 온보딩을 완료하지 않은 사용자입니다: " + userId));
        return toResponse(preference);
    }

    @Transactional
    public UserPreferenceResponse savePreference(Long userId, UserPreferenceRequest request) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new UserNotFoundException("사용자를 찾을 수 없습니다: " + userId));

        Set<Club> clubs = new HashSet<>(clubRepository.findAllById(request.clubIds()));

        UserPreference preference = userPreferenceRepository.findByUserId(userId)
                .orElseGet(() -> new UserPreference(user, request.notificationTrustLevel(), clubs));

        preference.setNotificationTrustLevel(request.notificationTrustLevel());
        preference.setClubs(clubs);

        return toResponse(userPreferenceRepository.save(preference));
    }

    private UserPreferenceResponse toResponse(UserPreference preference) {
        List<ClubResponse> clubs = preference.getClubs().stream()
                .map(club -> new ClubResponse(club.getId(), club.getName(), club.getLeague().name()))
                .toList();
        return new UserPreferenceResponse(clubs, preference.getNotificationTrustLevel());
    }
}
