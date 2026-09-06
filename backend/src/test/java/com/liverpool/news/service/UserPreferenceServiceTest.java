package com.liverpool.news.service;

import com.liverpool.news.dto.UserPreferenceRequest;
import com.liverpool.news.dto.UserPreferenceResponse;
import com.liverpool.news.entity.Club;
import com.liverpool.news.entity.League;
import com.liverpool.news.entity.User;
import com.liverpool.news.entity.UserPreference;
import com.liverpool.news.repository.ClubRepository;
import com.liverpool.news.repository.UserPreferenceRepository;
import com.liverpool.news.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Optional;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UserPreferenceServiceTest {

    @Mock
    private UserPreferenceRepository userPreferenceRepository;
    @Mock
    private UserRepository userRepository;
    @Mock
    private ClubRepository clubRepository;

    private UserPreferenceService service;

    private final User user = new User("test@example.com", null);
    private final Club liverpool = new Club("Liverpool", League.EPL);
    private final Club arsenal = new Club("Arsenal", League.EPL);

    @BeforeEach
    void setUp() {
        service = new UserPreferenceService(userPreferenceRepository, userRepository, clubRepository);
        lenient().when(userRepository.findById(1L)).thenReturn(Optional.of(user));
        lenient().when(userPreferenceRepository.findByUserId(1L)).thenReturn(Optional.empty());
        lenient().when(userPreferenceRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
    }

    @Test
    void 관심_구단_목록에_이미_있는_구단을_최애팀으로_지정하면_그대로_저장된다() {
        when(clubRepository.findAllById(List.of(1L))).thenReturn(List.of(liverpool));
        when(clubRepository.findById(10L)).thenReturn(Optional.of(liverpool));
        UserPreferenceRequest request = new UserPreferenceRequest(List.of(1L), 3, 10L);

        UserPreferenceResponse response = service.savePreference(1L, request);

        assertThat(response.favoriteClub().name()).isEqualTo("Liverpool");
        assertThat(response.clubs()).hasSize(1);
    }

    @Test
    void 관심_구단_목록에_없는_구단을_최애팀으로_지정하면_관심_구단에도_자동으로_추가된다() {
        when(clubRepository.findAllById(List.of(1L))).thenReturn(List.of(liverpool));
        when(clubRepository.findById(20L)).thenReturn(Optional.of(arsenal));
        UserPreferenceRequest request = new UserPreferenceRequest(List.of(1L), 3, 20L);

        UserPreferenceResponse response = service.savePreference(1L, request);

        assertThat(response.favoriteClub().name()).isEqualTo("Arsenal");
        assertThat(response.clubs()).extracting("name").containsExactlyInAnyOrder("Liverpool", "Arsenal");
    }

    @Test
    void 존재하지_않는_구단을_최애팀으로_지정하면_예외가_발생한다() {
        when(clubRepository.findAllById(List.of(1L))).thenReturn(List.of(liverpool));
        when(clubRepository.findById(999L)).thenReturn(Optional.empty());
        UserPreferenceRequest request = new UserPreferenceRequest(List.of(1L), 3, 999L);

        assertThatThrownBy(() -> service.savePreference(1L, request))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void favoriteClubId가_없으면_최애팀_없이_저장된다() {
        when(clubRepository.findAllById(List.of(1L))).thenReturn(List.of(liverpool));
        UserPreferenceRequest request = new UserPreferenceRequest(List.of(1L), 3, null);

        UserPreferenceResponse response = service.savePreference(1L, request);

        assertThat(response.favoriteClub()).isNull();
    }

    @Test
    void 기존_선호도가_있으면_최애팀만_새로_반영해_갱신한다() {
        UserPreference existing = new UserPreference(user, 3, Set.of(liverpool), null);
        when(userPreferenceRepository.findByUserId(1L)).thenReturn(Optional.of(existing));
        when(clubRepository.findAllById(List.of(1L))).thenReturn(List.of(liverpool));
        when(clubRepository.findById(10L)).thenReturn(Optional.of(liverpool));
        UserPreferenceRequest request = new UserPreferenceRequest(List.of(1L), 4, 10L);

        UserPreferenceResponse response = service.savePreference(1L, request);

        assertThat(response.notificationTrustLevel()).isEqualTo(4);
        assertThat(response.favoriteClub().name()).isEqualTo("Liverpool");
    }
}
