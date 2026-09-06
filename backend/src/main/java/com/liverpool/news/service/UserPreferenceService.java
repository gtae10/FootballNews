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

        Club favoriteClub = null;
        if (request.favoriteClubId() != null) {
            favoriteClub = clubRepository.findById(request.favoriteClubId())
                    .orElseThrow(() -> new IllegalArgumentException(
                            "존재하지 않는 구단은 최애팀으로 지정할 수 없습니다: " + request.favoriteClubId()));
            // 최애팀으로 지정한 구단이 관심 구단 목록에 없으면(온보딩 UI는 관심 구단 중에서만
            // 고르게 하지만, API를 직접 호출하는 경우까지 방어한다) 에러 대신 관심 구단 목록에
            // 자동으로 포함시킨다 — 한 번의 PUT으로 "관심 구단 추가 + 최애팀 지정"이 동시에
            // 되는 편이 별도 400을 반환하는 것보다 자연스럽다.
            clubs.add(favoriteClub);
        }

        Club favoriteClubForNewPreference = favoriteClub;
        UserPreference preference = userPreferenceRepository.findByUserId(userId)
                .orElseGet(() -> new UserPreference(user, request.notificationTrustLevel(), clubs, favoriteClubForNewPreference));

        preference.setNotificationTrustLevel(request.notificationTrustLevel());
        preference.setClubs(clubs);
        preference.setFavoriteClub(favoriteClub);

        return toResponse(userPreferenceRepository.save(preference));
    }

    private UserPreferenceResponse toResponse(UserPreference preference) {
        List<ClubResponse> clubs = preference.getClubs().stream()
                .map(this::toClubResponse)
                .toList();
        Club favoriteClub = preference.getFavoriteClub();
        return new UserPreferenceResponse(
                clubs,
                preference.getNotificationTrustLevel(),
                favoriteClub != null ? toClubResponse(favoriteClub) : null
        );
    }

    private ClubResponse toClubResponse(Club club) {
        return new ClubResponse(club.getId(), club.getName(), club.getLeague().name());
    }
}
