import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { isUnauthorized } from "../utils/handleApiError";

const LEAGUE_OPTIONS = [
  { value: "", label: "선택 안 함" },
  { value: "EPL", label: "EPL" },
  { value: "LA_LIGA", label: "라리가" },
  { value: "BUNDESLIGA", label: "분데스리가" },
  { value: "SERIE_A", label: "세리에 A" },
  { value: "LIGUE_1", label: "리그 1" },
];

export default function SettingsPage() {
  const { user, logout, refresh, isGuest } = useAuth();
  const navigate = useNavigate();

  const [nickname, setNickname] = useState(user?.nickname ?? "");
  const [nicknameSaving, setNicknameSaving] = useState(false);
  const [nicknameError, setNicknameError] = useState(null);
  const [nicknameSaved, setNicknameSaved] = useState(false);

  const [confirmingWithdraw, setConfirmingWithdraw] = useState(false);
  const [withdrawing, setWithdrawing] = useState(false);
  const [withdrawError, setWithdrawError] = useState(null);

  const [clubs, setClubs] = useState([]);
  const [selectedClubIds, setSelectedClubIds] = useState(new Set());
  const [notificationTrustLevel, setNotificationTrustLevel] = useState(null);
  const [clubsLoading, setClubsLoading] = useState(true);
  const [clubsSaving, setClubsSaving] = useState(false);
  const [clubsError, setClubsError] = useState(null);
  const [clubsSaved, setClubsSaved] = useState(false);

  const [suggestions, setSuggestions] = useState([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(true);
  const [twitterHandle, setTwitterHandle] = useState("");
  const [reporterName, setReporterName] = useState("");
  const [reporterLeague, setReporterLeague] = useState("");
  const [memo, setMemo] = useState("");
  const [suggestionSaving, setSuggestionSaving] = useState(false);
  const [suggestionError, setSuggestionError] = useState(null);

  useEffect(() => {
    // 게스트는 계정이 없으므로 인증이 필요한 API를 호출하지 않는다 — 아래에서
    // 로그인 안내만 보여주고 이 페이지의 나머지 기능은 렌더링하지 않는다.
    if (isGuest) {
      setClubsLoading(false);
      setSuggestionsLoading(false);
      return;
    }

    Promise.all([apiFetch("/clubs"), apiFetch("/users/me/preferences")])
      .then(([clubList, preference]) => {
        setClubs(clubList);
        setSelectedClubIds(new Set(preference.clubs.map((club) => club.id)));
        setNotificationTrustLevel(preference.notificationTrustLevel);
      })
      .catch((err) => {
        if (isUnauthorized(err)) {
          navigate("/login", { replace: true });
          return;
        }
        setClubsError(err.message);
      })
      .finally(() => setClubsLoading(false));

    loadSuggestions();
  }, [isGuest]);

  function loadSuggestions() {
    setSuggestionsLoading(true);
    apiFetch("/reporter-suggestions/me")
      .then(setSuggestions)
      .catch(() => setSuggestions([]))
      .finally(() => setSuggestionsLoading(false));
  }

  const clubsByLeague = useMemo(() => {
    return clubs.reduce((groups, club) => {
      (groups[club.league] ??= []).push(club);
      return groups;
    }, {});
  }, [clubs]);

  function toggleClub(clubId) {
    setClubsSaved(false);
    setSelectedClubIds((prev) => {
      const next = new Set(prev);
      if (next.has(clubId)) {
        next.delete(clubId);
      } else {
        next.add(clubId);
      }
      return next;
    });
  }

  async function handleSaveNickname(event) {
    event.preventDefault();
    setNicknameSaving(true);
    setNicknameError(null);
    setNicknameSaved(false);
    try {
      await apiFetch("/users/me/nickname", {
        method: "PATCH",
        body: JSON.stringify({ nickname }),
      });
      await refresh();
      setNicknameSaved(true);
    } catch (err) {
      if (isUnauthorized(err)) {
        navigate("/login", { replace: true });
        return;
      }
      setNicknameError(err.message);
    } finally {
      setNicknameSaving(false);
    }
  }

  async function handleSaveClubs() {
    setClubsSaving(true);
    setClubsError(null);
    setClubsSaved(false);
    try {
      await apiFetch("/users/me/preferences", {
        method: "PUT",
        body: JSON.stringify({
          clubIds: [...selectedClubIds],
          notificationTrustLevel,
        }),
      });
      setClubsSaved(true);
    } catch (err) {
      if (isUnauthorized(err)) {
        navigate("/login", { replace: true });
        return;
      }
      setClubsError(err.message);
    } finally {
      setClubsSaving(false);
    }
  }

  async function handleSubmitSuggestion(event) {
    event.preventDefault();
    setSuggestionSaving(true);
    setSuggestionError(null);
    try {
      await apiFetch("/reporter-suggestions", {
        method: "POST",
        body: JSON.stringify({
          twitterHandle,
          name: reporterName || null,
          league: reporterLeague || null,
          memo: memo || null,
        }),
      });
      setTwitterHandle("");
      setReporterName("");
      setReporterLeague("");
      setMemo("");
      loadSuggestions();
    } catch (err) {
      if (isUnauthorized(err)) {
        navigate("/login", { replace: true });
        return;
      }
      setSuggestionError(err.message);
    } finally {
      setSuggestionSaving(false);
    }
  }

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  async function handleWithdraw() {
    setWithdrawing(true);
    setWithdrawError(null);
    try {
      await apiFetch("/users/me", { method: "DELETE" });
      await refresh();
      navigate("/login", { replace: true });
    } catch (err) {
      if (isUnauthorized(err)) {
        navigate("/login", { replace: true });
        return;
      }
      setWithdrawError(err.message);
      setWithdrawing(false);
    }
  }

  if (isGuest) {
    return (
      <div style={{ paddingTop: 26 }}>
        <p>
          <Link to="/feed" className="rf-mono" style={{ fontSize: 11, letterSpacing: "0.14em", color: "var(--rf-muted-1)" }}>
            ← 피드
          </Link>
        </p>
        <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-.02em", margin: "24px 0 4px" }}>설정</h1>
        <p className="rf-status" role="status">
          로그인이 필요한 기능입니다. 관심 구단, 알림, 기자 제보는 로그인 후 이용할 수 있어요.
        </p>
        <Link to="/login" className="rf-btn-primary" style={{ display: "inline-block" }}>
          Google 로그인하러 가기
        </Link>
      </div>
    );
  }

  return (
    <div style={{ paddingTop: 26 }}>
      <p>
        <Link to="/feed" className="rf-mono" style={{ fontSize: 11, letterSpacing: "0.14em", color: "var(--rf-muted-1)" }}>
          ← 피드
        </Link>
      </p>
      <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-.02em", margin: "24px 0 4px" }}>설정</h1>

      <section className="rf-section" style={{ paddingTop: 22 }}>
        <div className="rf-section-label">ACCOUNT</div>
        <div className="rf-row">
          <div className="rf-row-label">이메일</div>
          <div style={{ flex: 1 }}>{user?.email}</div>
        </div>
        <form onSubmit={handleSaveNickname} className="rf-row" style={{ alignItems: "center" }}>
          <label className="rf-row-label" htmlFor="settings-nickname">
            닉네임
          </label>
          <input
            id="settings-nickname"
            className="rf-input"
            style={{ flex: 1 }}
            type="text"
            value={nickname}
            onChange={(e) => {
              setNickname(e.target.value);
              setNicknameSaved(false);
            }}
          />
          <button type="submit" className="rf-btn" disabled={nicknameSaving}>
            {nicknameSaving ? "저장 중..." : "변경"}
          </button>
          {nicknameSaved && <span role="status" className="rf-toast"> 저장되었습니다.</span>}
          {nicknameError && <p role="alert" className="rf-error">오류: {nicknameError}</p>}
        </form>

        <div style={{ display: "flex", gap: 14, paddingTop: 18 }}>
          <button type="button" className="rf-btn" onClick={handleLogout}>
            로그아웃
          </button>

          {!confirmingWithdraw && (
            <button type="button" className="rf-btn-danger" onClick={() => setConfirmingWithdraw(true)}>
              탈퇴하기
            </button>
          )}
        </div>

        {confirmingWithdraw && (
          <div role="alertdialog" style={{ paddingTop: 14 }}>
            <p style={{ fontSize: 13, color: "var(--rf-muted-1)" }}>
              정말 탈퇴하시겠습니까? 이 작업은 되돌릴 수 없습니다.
            </p>
            <div style={{ display: "flex", gap: 14 }}>
              <button type="button" className="rf-btn-danger" onClick={handleWithdraw} disabled={withdrawing}>
                {withdrawing ? "처리 중..." : "탈퇴 확인"}
              </button>
              <button type="button" className="rf-btn" onClick={() => setConfirmingWithdraw(false)} disabled={withdrawing}>
                취소
              </button>
            </div>
            {withdrawError && <p role="alert" className="rf-error">오류: {withdrawError}</p>}
          </div>
        )}
      </section>

      <section className="rf-section">
        <div className="rf-section-label">MY CLUBS</div>
        {clubsLoading && <p className="rf-status" style={{ paddingTop: 16 }}>불러오는 중...</p>}
        {clubsError && <p role="alert" className="rf-error">오류: {clubsError}</p>}
        {!clubsLoading && !clubsError && (
          <>
            <div style={{ display: "flex", flexDirection: "column", gap: 22, paddingTop: 18 }}>
              {Object.entries(clubsByLeague).map(([league, leagueClubs]) => (
                <fieldset key={league} style={{ border: "none", margin: 0, padding: 0 }}>
                  <legend className="rf-league-label" style={{ padding: 0, marginBottom: 10 }}>
                    {league}
                  </legend>
                  <div className="rf-chip-group">
                    {leagueClubs.map((club) => (
                      <label key={club.id} className="rf-chip" data-selected={selectedClubIds.has(club.id) ? "true" : "false"}>
                        <input
                          type="checkbox"
                          checked={selectedClubIds.has(club.id)}
                          onChange={() => toggleClub(club.id)}
                          style={{ position: "absolute", opacity: 0, width: 0, height: 0 }}
                        />
                        {club.name}
                      </label>
                    ))}
                  </div>
                </fieldset>
              ))}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, paddingTop: 20 }}>
              <button type="button" className="rf-btn-primary" style={{ flex: "none" }} onClick={handleSaveClubs} disabled={clubsSaving}>
                {clubsSaving ? "저장 중..." : "관심 설정 저장"}
              </button>
              {clubsSaved && <span role="status" className="rf-toast">저장되었습니다.</span>}
            </div>
          </>
        )}
      </section>

      <section className="rf-section">
        <div className="rf-section-label">기자 제보</div>
        <form onSubmit={handleSubmitSuggestion} style={{ display: "flex", flexDirection: "column", gap: 10, paddingTop: 16 }}>
          <label className="rf-field">
            트위터(X) 핸들
            <input
              className="rf-input"
              type="text"
              value={twitterHandle}
              onChange={(e) => setTwitterHandle(e.target.value)}
              placeholder="@handle"
              required
            />
          </label>
          <label className="rf-field">
            기자 이름 (선택)
            <input className="rf-input" type="text" value={reporterName} onChange={(e) => setReporterName(e.target.value)} />
          </label>
          <label className="rf-field">
            주로 다루는 리그 (선택)
            <select className="rf-select" value={reporterLeague} onChange={(e) => setReporterLeague(e.target.value)}>
              {LEAGUE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="rf-field">
            메모 (선택)
            <textarea className="rf-input" rows={3} value={memo} onChange={(e) => setMemo(e.target.value)} />
          </label>
          <button type="submit" className="rf-btn" style={{ alignSelf: "flex-start" }} disabled={suggestionSaving}>
            {suggestionSaving ? "제출 중..." : "제보하기"}
          </button>
          {suggestionError && <p role="alert" className="rf-error">오류: {suggestionError}</p>}
        </form>

        <div style={{ paddingTop: 26 }}>
          <div className="rf-mono" style={{ fontSize: 10.5, letterSpacing: "0.16em", color: "var(--rf-muted-4)", paddingBottom: 8 }}>
            내 제보 내역
          </div>
          {suggestionsLoading && <p className="rf-status">불러오는 중...</p>}
          {!suggestionsLoading && suggestions.length === 0 && <p className="rf-status">아직 제보한 내역이 없습니다.</p>}
          {!suggestionsLoading && suggestions.length > 0 && (
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {suggestions.map((suggestion) => (
                <li
                  key={suggestion.id}
                  style={{ display: "flex", gap: 14, padding: "14px 0", borderTop: "1px solid var(--rf-border-faintest)" }}
                >
                  <span style={{ flex: 1, fontSize: 14 }}>
                    {suggestion.twitterHandle}
                    {suggestion.name && ` (${suggestion.name})`}
                  </span>
                  {suggestion.league && (
                    <span className="rf-mono" style={{ fontSize: 10.5, color: "var(--rf-muted-4)" }}>
                      {suggestion.league}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
