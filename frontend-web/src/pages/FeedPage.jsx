import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import { isUnauthorized } from "../utils/handleApiError";
import { tierBadge, timeAgo } from "../utils/articleDisplay";
import TopArticlesBox from "../components/TopArticlesBox";

export default function FeedPage() {
  const navigate = useNavigate();

  const [articles, setArticles] = useState([]);
  const [clubs, setClubs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [clubFilter, setClubFilter] = useState(undefined);
  const [keywordInput, setKeywordInput] = useState("");
  const [keyword, setKeyword] = useState("");

  useEffect(() => {
    apiFetch("/clubs")
      .then(setClubs)
      .catch(() => setClubs([]));

    apiFetch("/users/me/preferences")
      .then((preference) => {
        setClubFilter(preference.clubs[0]?.name ?? "");
      })
      .catch(() => setClubFilter(""));
  }, []);

  useEffect(() => {
    if (clubFilter === undefined) {
      return;
    }

    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    if (clubFilter) params.set("club", clubFilter);
    if (keyword) params.set("keyword", keyword);
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
  }, [clubFilter, keyword, navigate]);

  function handleSearchSubmit(event) {
    event.preventDefault();
    setKeyword(keywordInput);
  }

  return (
    <div>
      <div className="rf-header">
        <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
          <span className="rf-wordmark">리버풀 뉴스</span>
        </div>
        <Link to="/settings" style={{ fontSize: 13, color: "var(--rf-muted-1)" }}>
          설정
        </Link>
      </div>

      <TopArticlesBox />

      <form
        onSubmit={handleSearchSubmit}
        style={{ display: "flex", gap: 10, padding: "18px 0", borderBottom: "1px solid var(--rf-border-soft)" }}
      >
        <input
          className="rf-input"
          style={{ flex: 1 }}
          type="search"
          placeholder="키워드 검색"
          value={keywordInput}
          onChange={(e) => setKeywordInput(e.target.value)}
        />
        <select
          className="rf-select"
          style={{ maxWidth: 200 }}
          value={clubFilter ?? ""}
          onChange={(e) => setClubFilter(e.target.value)}
        >
          <option value="">전체 구단</option>
          {clubs.map((club) => (
            <option key={club.id} value={club.name}>
              {club.name}
            </option>
          ))}
        </select>
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
          {articles.length === 0 && <p className="rf-status">조건에 맞는 기사가 없습니다</p>}
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
                <div className="rf-article-meta">
                  <span style={{ color: badge.color }}>{badge.label}</span>
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
            );
          })}
        </div>
      )}
    </div>
  );
}
