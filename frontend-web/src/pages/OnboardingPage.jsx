import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { isUnauthorized } from "../utils/handleApiError";

const TRUST_LEVELS = [
  { level: 1, label: "1단계 — 공식 소스만" },
  { level: 2, label: "2단계 — 공식 + 주요 매체" },
  { level: 3, label: "3단계 — 균형있게" },
  { level: 4, label: "4단계 — 대부분의 소스" },
  { level: 5, label: "5단계 — 모든 소스" },
];

export default function OnboardingPage() {
  const navigate = useNavigate();
  const { refresh } = useAuth();

  const [step, setStep] = useState(1);
  const [clubs, setClubs] = useState([]);
  const [selectedClubIds, setSelectedClubIds] = useState(new Set());
  const [favoriteClubId, setFavoriteClubId] = useState(null);
  const [search, setSearch] = useState("");
  const [trustLevel, setTrustLevel] = useState(3);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiFetch("/clubs")
      .then(setClubs)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const clubsByLeague = useMemo(() => {
    const filtered = clubs.filter((club) =>
      club.name.toLowerCase().includes(search.toLowerCase())
    );
    return filtered.reduce((groups, club) => {
      (groups[club.league] ??= []).push(club);
      return groups;
    }, {});
  }, [clubs, search]);

  const selectedClubs = useMemo(
    () => clubs.filter((club) => selectedClubIds.has(club.id)),
    [clubs, selectedClubIds]
  );

  function toggleClub(clubId) {
    setSelectedClubIds((prev) => {
      const next = new Set(prev);
      if (next.has(clubId)) {
        next.delete(clubId);
        // 관심 구단에서 제외된 구단이 최애팀으로 지정돼 있었다면 함께 해제한다.
        setFavoriteClubId((favorite) => (favorite === clubId ? null : favorite));
      } else {
        next.add(clubId);
      }
      return next;
    });
  }

  function toggleFavoriteClub(clubId) {
    setFavoriteClubId((prev) => (prev === clubId ? null : clubId));
  }

  async function handleFinish() {
    setSaving(true);
    setError(null);
    try {
      await apiFetch("/users/me/preferences", {
        method: "PUT",
        body: JSON.stringify({
          clubIds: [...selectedClubIds],
          notificationTrustLevel: trustLevel,
          favoriteClubId,
        }),
      });
      await refresh();
      navigate("/feed", { replace: true });
    } catch (err) {
      if (isUnauthorized(err)) {
        navigate("/login", { replace: true });
        return;
      }
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="rf-status">불러오는 중...</p>;

  return (
    <div style={{ paddingTop: 40 }}>
      <div className="rf-progress">
        <div className="rf-progress-bar" data-active="true" />
        <div className="rf-progress-bar" data-active={step >= 2 ? "true" : "false"} />
        <div className="rf-progress-bar" data-active={step >= 3 ? "true" : "false"} />
        <div className="rf-progress-label">STEP {step} / 3</div>
      </div>

      {error && <p className="rf-error" role="alert">오류: {error}</p>}

      {step === 1 && (
        <section style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          <div>
            <div className="rf-title-lg">관심 구단을 골라주세요</div>
            <div className="rf-subtitle">선택한 구단의 소식이 피드 상단에 먼저 노출됩니다.</div>
          </div>
          <input
            className="rf-input"
            type="search"
            placeholder="구단 검색 (예: Liverpool, 아스날)"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 26 }}>
            {Object.entries(clubsByLeague).map(([league, leagueClubs]) => (
              <div key={league}>
                <div className="rf-league-label">{league}</div>
                <div className="rf-chip-group">
                  {leagueClubs.map((club) => (
                    <button
                      key={club.id}
                      type="button"
                      className="rf-chip"
                      data-selected={selectedClubIds.has(club.id) ? "true" : "false"}
                      aria-pressed={selectedClubIds.has(club.id)}
                      onClick={() => toggleClub(club.id)}
                    >
                      {club.name}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
          {selectedClubs.length > 0 && (
            <div>
              <div className="rf-league-label">최애팀 (선택)</div>
              <div className="rf-chip-group">
                {selectedClubs.map((club) => (
                  <button
                    key={club.id}
                    type="button"
                    className="rf-chip"
                    data-selected={favoriteClubId === club.id ? "true" : "false"}
                    aria-pressed={favoriteClubId === club.id}
                    onClick={() => toggleFavoriteClub(club.id)}
                  >
                    ★ {club.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div style={{ display: "flex", gap: 14, paddingTop: 12 }}>
            <button
              type="button"
              className="rf-btn-primary"
              onClick={() => setStep(2)}
              disabled={selectedClubIds.size === 0}
            >
              다음
            </button>
          </div>
        </section>
      )}

      {step === 2 && (
        <section style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          <div>
            <div className="rf-title-lg">어디까지 알림을 받을까요?</div>
            <div className="rf-subtitle">선택한 단계까지의 신뢰도를 가진 기사만 알림으로 보냅니다.</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {TRUST_LEVELS.map(({ level, label }) => (
              <button
                key={level}
                type="button"
                className="rf-tier-row"
                data-selected={trustLevel === level ? "true" : "false"}
                aria-pressed={trustLevel === level}
                onClick={() => setTrustLevel(level)}
              >
                <span className="rf-tier-num" style={{ color: "var(--rf-red)" }}>
                  {level}
                </span>
                <span className="rf-tier-name">{label}</span>
                {trustLevel === level && (
                  <span className="rf-mono" style={{ fontSize: 11, color: "var(--rf-red)" }}>
                    ● 선택
                  </span>
                )}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 14 }}>
            <button type="button" className="rf-btn" onClick={() => setStep(1)}>
              이전
            </button>
            <button type="button" className="rf-btn-primary" onClick={() => setStep(3)}>
              다음
            </button>
          </div>
        </section>
      )}

      {step === 3 && (
        <section style={{ display: "flex", flexDirection: "column", gap: 26 }}>
          <div>
            <div className="rf-title-lg">준비됐습니다</div>
            <div className="rf-subtitle">설정은 언제든 설정 페이지에서 바꿀 수 있어요.</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div className="rf-row">
              <div className="rf-mono rf-row-label" style={{ fontSize: 11, letterSpacing: "0.14em" }}>
                CLUBS
              </div>
              <div style={{ flex: 1, fontSize: 14.5, lineHeight: 1.7 }}>
                {selectedClubs.map((club) => club.name).join(" · ")}
              </div>
            </div>
            <div className="rf-row">
              <div className="rf-mono rf-row-label" style={{ fontSize: 11, letterSpacing: "0.14em" }}>
                FAVORITE
              </div>
              <div style={{ flex: 1, fontSize: 14.5 }}>
                {selectedClubs.find((club) => club.id === favoriteClubId)?.name ?? "미설정"}
              </div>
            </div>
            <div className="rf-row">
              <div className="rf-mono rf-row-label" style={{ fontSize: 11, letterSpacing: "0.14em" }}>
                ALERT TIER
              </div>
              <div style={{ flex: 1, fontSize: 14.5 }}>{TRUST_LEVELS.find((t) => t.level === trustLevel)?.label}</div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 14 }}>
            <button type="button" className="rf-btn" onClick={() => setStep(2)} disabled={saving}>
              이전
            </button>
            <button type="button" className="rf-btn-primary" onClick={handleFinish} disabled={saving}>
              {saving ? "저장 중..." : "피드로 이동"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
