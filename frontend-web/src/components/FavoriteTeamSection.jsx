import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { tierBadge, timeAgo } from "../utils/articleDisplay";

const VISIBLE_COUNT = 5;

// 이 섹션은 사용자가 FeedPage의 club/category 필터를 바꿔도 항상 최애팀 기준으로
// 고정 유지되어야 하므로, FeedPage의 필터 상태와 무관하게 자체적으로 최애팀
// 정보와 기사를 불러온다 (FeedPage.jsx 참고).
export default function FavoriteTeamSection({ onViewAll }) {
  const navigate = useNavigate();
  const { isGuest } = useAuth();

  const [favoriteClub, setFavoriteClub] = useState(undefined); // undefined = 조회 전, null = 미설정
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isGuest) {
      setFavoriteClub(null);
      setLoading(false);
      return;
    }

    apiFetch("/users/me/preferences")
      .then((preference) => setFavoriteClub(preference.favoriteClub ?? null))
      .catch(() => setFavoriteClub(null));
  }, [isGuest]);

  useEffect(() => {
    if (!favoriteClub) {
      setLoading(false);
      return;
    }

    setLoading(true);
    apiFetch(`/articles?club=${encodeURIComponent(favoriteClub.name)}&size=${VISIBLE_COUNT}`)
      .then((data) => setArticles(data.content ?? []))
      .catch(() => setArticles([]))
      .finally(() => setLoading(false));
  }, [favoriteClub]);

  if (isGuest || favoriteClub === undefined) {
    return null;
  }

  if (favoriteClub === null) {
    return (
      <section style={{ borderBottom: "1px solid var(--rf-border-soft)", padding: "20px 0" }}>
        <p className="rf-status">
          <Link to="/settings">최애팀을 설정해보세요 →</Link>
        </p>
      </section>
    );
  }

  if (loading) {
    return null;
  }

  return (
    <section style={{ borderBottom: "1px solid var(--rf-border-soft)", padding: "20px 0" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span className="rf-top-dot" />
        <h2 style={{ fontSize: 14, fontWeight: 500, letterSpacing: "-.01em", margin: 0 }}>
          {favoriteClub.name} 소식
        </h2>
        <span className="rf-top-rule" />
      </div>
      <div style={{ paddingTop: 16, display: "flex", flexDirection: "column" }}>
        {articles.length === 0 && <p className="rf-status">아직 소식이 없습니다.</p>}
        {articles.map((article) => {
          const badge = tierBadge(article.sourceTier);
          return (
            <div
              key={article.id}
              className="rf-top-item"
              role="link"
              tabIndex={0}
              onClick={() => navigate(`/articles/${article.id}`)}
              onKeyDown={(e) => {
                if (e.key === "Enter") navigate(`/articles/${article.id}`);
              }}
              style={{ cursor: "pointer" }}
            >
              <span style={{ flex: 1, fontSize: 14.5, lineHeight: 1.55, color: "var(--rf-text-dim)" }}>
                {article.titleKo}
              </span>
              <span className="rf-mono" style={{ fontSize: 10.5, color: badge.color, whiteSpace: "nowrap" }}>
                {timeAgo(article.publishedAt)}
              </span>
            </div>
          );
        })}
        {articles.length > 0 && (
          <button
            type="button"
            className="rf-btn"
            style={{ alignSelf: "flex-start", marginTop: 10, border: "none", padding: 0 }}
            onClick={() => onViewAll(favoriteClub.name)}
          >
            더보기
          </button>
        )}
      </div>
    </section>
  );
}
