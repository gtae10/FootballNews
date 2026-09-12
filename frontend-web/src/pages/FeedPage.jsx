import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { isUnauthorized } from "../utils/handleApiError";
import { tierBadge, timeAgo } from "../utils/articleDisplay";
import TopArticlesBox from "../components/TopArticlesBox";
import FavoriteTeamSection from "../components/FavoriteTeamSection";

const CATEGORY_OPTIONS = [
  { value: "", label: "전체" },
  { value: "MATCH", label: "경기" },
  { value: "TRANSFER", label: "이적" },
  { value: "PLAYER", label: "선수" },
];

export default function FeedPage() {
  const navigate = useNavigate();
  const { isGuest } = useAuth();

  const [articles, setArticles] = useState([]);
  const [clubs, setClubs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // "전체" 탭 전용 보조 필터 — 관심구단 탭의 최애팀 로직과 섞이지 않도록 별도 상태로 둔다.
  const [allClubFilter, setAllClubFilter] = useState("");
  // "관심구단" 탭 전용 — 팔로우한 구단 전체 vs 최애팀 하나만.
  const [activeTab, setActiveTab] = useState("all"); // "all" | "interests"
  const [interestsSubFilter, setInterestsSubFilter] = useState("all"); // "all" | "favorite"
  // undefined = 아직 조회 전, null = 게스트라 해당 없음 / 조회 실패
  const [preferences, setPreferences] = useState(undefined);

  const [categoryFilter, setCategoryFilter] = useState("");
  const [keywordInput, setKeywordInput] = useState("");
  const [keyword, setKeyword] = useState("");

  useEffect(() => {
    apiFetch("/clubs")
      .then(setClubs)
      .catch(() => setClubs([]));
  }, []);

  useEffect(() => {
    if (isGuest) {
      setPreferences(null);
      return;
    }
    apiFetch("/users/me/preferences")
      .then(setPreferences)
      .catch(() => setPreferences(null));
  }, [isGuest]);

  useEffect(() => {
    // 관심구단 탭은 로그인 사용자의 관심 구단 정보가 있어야 조회할 수 있다.
    if (activeTab === "interests") {
      if (isGuest) {
        setArticles([]);
        setLoading(false);
        return;
      }
      if (preferences === undefined) {
        return; // 아직 관심 구단 정보를 불러오는 중
      }
    }

    const params = new URLSearchParams();

    if (activeTab === "all") {
      if (allClubFilter) params.set("club", allClubFilter);
    } else if (interestsSubFilter === "favorite") {
      const favoriteClub = preferences?.favoriteClub;
      if (!favoriteClub) {
        setArticles([]);
        setLoading(false);
        return;
      }
      params.set("club", favoriteClub.name);
    } else {
      const clubNames = (preferences?.clubs ?? []).map((c) => c.name);
      if (clubNames.length === 0) {
        setArticles([]);
        setLoading(false);
        return;
      }
      params.set("clubs", clubNames.join(","));
    }

    if (categoryFilter) params.set("category", categoryFilter);
    if (keyword) params.set("keyword", keyword);

    setLoading(true);
    setError(null);
    const query = params.toString() ? `?${params.toString()}` : "";

    apiFetch(`/articles${query}`)
      .then((data) => setArticles(data.content ?? []))
      .catch((err) => {
        if (isUnauthorized(err)) {
          navigate("/login", { replace: true });
          return;
        }
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [activeTab, allClubFilter, interestsSubFilter, categoryFilter, keyword, preferences, isGuest, navigate]);

  function handleSearchSubmit(event) {
    event.preventDefault();
    setKeyword(keywordInput);
  }

  const showInterestsGuestPrompt = activeTab === "interests" && isGuest;
  const interestsNeedsClubs =
    activeTab === "interests" && !isGuest && preferences && interestsSubFilter === "all" &&
    (preferences.clubs ?? []).length === 0;
  const interestsNeedsFavorite =
    activeTab === "interests" && !isGuest && preferences && interestsSubFilter === "favorite" &&
    !preferences.favoriteClub;

  return (
    <div>
      <div className="rf-header">
        <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
          <span className="rf-wordmark">433</span>
        </div>
        <Link to="/settings" style={{ fontSize: 13, color: "var(--rf-muted-1)" }}>
          설정
        </Link>
      </div>

      <TopArticlesBox />

      <FavoriteTeamSection
        onViewAll={(clubName) => {
          setActiveTab("all");
          setAllClubFilter(clubName);
          setCategoryFilter("");
        }}
      />

      <div className="rf-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          className="rf-tab"
          data-selected={activeTab === "all" ? "true" : "false"}
          aria-selected={activeTab === "all"}
          onClick={() => setActiveTab("all")}
        >
          전체
        </button>
        <button
          type="button"
          role="tab"
          className="rf-tab"
          data-selected={activeTab === "interests" ? "true" : "false"}
          aria-selected={activeTab === "interests"}
          onClick={() => setActiveTab("interests")}
        >
          관심구단
        </button>
      </div>

      {showInterestsGuestPrompt ? (
        <p className="rf-status" style={{ paddingTop: 18 }}>
          <Link to="/login">로그인하면 관심 구단 소식만 모아볼 수 있어요 →</Link>
        </p>
      ) : (
        <>
          {activeTab === "interests" && (
            <div className="rf-chip-group" style={{ paddingTop: 18 }}>
              <button
                type="button"
                className="rf-chip"
                data-selected={interestsSubFilter === "all" ? "true" : "false"}
                aria-pressed={interestsSubFilter === "all"}
                onClick={() => setInterestsSubFilter("all")}
              >
                관심 구단 전체
              </button>
              <button
                type="button"
                className="rf-chip"
                data-selected={interestsSubFilter === "favorite" ? "true" : "false"}
                aria-pressed={interestsSubFilter === "favorite"}
                onClick={() => setInterestsSubFilter("favorite")}
              >
                최애팀만
              </button>
            </div>
          )}

          <div className="rf-chip-group" style={{ paddingTop: 18 }}>
            {CATEGORY_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                className="rf-chip"
                data-selected={categoryFilter === option.value ? "true" : "false"}
                aria-pressed={categoryFilter === option.value}
                onClick={() => setCategoryFilter(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSearchSubmit} className="rf-search-row">
            <input
              className="rf-input"
              type="search"
              placeholder="키워드 검색"
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
            />
            {activeTab === "all" && (
              <select
                className="rf-select rf-select-club"
                value={allClubFilter}
                onChange={(e) => setAllClubFilter(e.target.value)}
              >
                <option value="">전체 구단</option>
                {clubs.map((club) => (
                  <option key={club.id} value={club.name}>
                    {club.name}
                  </option>
                ))}
              </select>
            )}
            <button type="submit" className="rf-btn">
              검색
            </button>
          </form>

          {loading && <p className="rf-status">불러오는 중...</p>}
          {error && (
            <p className="rf-error" role="alert">
              기사를 불러오지 못했습니다 ({error})
            </p>
          )}

          {!loading && !error && (
            <div>
              {articles.length === 0 &&
                (interestsNeedsClubs ? (
                  <p className="rf-status">
                    <Link to="/settings">관심 구단을 먼저 설정해보세요 →</Link>
                  </p>
                ) : interestsNeedsFavorite ? (
                  <p className="rf-status">
                    <Link to="/settings">최애팀을 먼저 설정해보세요 →</Link>
                  </p>
                ) : (
                  <p className="rf-status">조건에 맞는 기사가 없습니다</p>
                ))}
              {articles.map((article) => {
                const badge = tierBadge(article.sourceTier);
                return (
                  <div
                    key={article.id}
                    className="rf-article-card"
                    role="link"
                    tabIndex={0}
                    onClick={() => navigate(`/articles/${article.id}`)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") navigate(`/articles/${article.id}`);
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    {article.imageUrl && (
                      <img
                        className="rf-article-thumb"
                        src={article.imageUrl}
                        alt=""
                        loading="lazy"
                        // 원본 서버가 이미지를 지웠거나 핫링크를 막아 로드에 실패하면 이미지
                        // 영역만 숨기고 텍스트는 그대로 보여준다 (이미지를 우리 서버에 저장하지
                        // 않고 원본 URL을 직접 불러오므로 이런 실패는 항상 감안해야 한다).
                        onError={(e) => {
                          e.currentTarget.style.display = "none";
                        }}
                      />
                    )}
                    <div className="rf-article-body">
                      <div className="rf-article-meta">
                        <span style={{ color: badge.color, fontSize: 12.5 }}>{badge.label}</span>
                        <span>{article.source}</span>
                        <span>·</span>
                        <span>{timeAgo(article.publishedAt)}</span>
                      </div>
                      <div className="rf-article-title">{article.titleKo}</div>
                      <div className="rf-article-sub">
                        <span>{(article.clubs ?? []).join(" · ")}</span>
                        <a
                          href={article.originalUrl}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                        >
                          원문 보기 ↗
                        </a>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
