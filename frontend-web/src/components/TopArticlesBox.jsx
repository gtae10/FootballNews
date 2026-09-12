import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import { tierBadge } from "../utils/articleDisplay";

const DEFAULT_VISIBLE_COUNT = 3;

export default function TopArticlesBox() {
  const navigate = useNavigate();
  const [articles, setArticles] = useState([]);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/articles/top?limit=10")
      .then(setArticles)
      .catch(() => setArticles([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading || articles.length === 0) {
    return null;
  }

  const visibleArticles = expanded ? articles : articles.slice(0, DEFAULT_VISIBLE_COUNT);
  const hasMore = articles.length > DEFAULT_VISIBLE_COUNT;

  return (
    <section style={{ borderBottom: "1px solid var(--rf-border-soft)", padding: "20px 0" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span className="rf-top-dot" />
        <h2 style={{ fontSize: 14, fontWeight: 500, letterSpacing: "-.01em", margin: 0 }}>
          오늘의 주요 소식
        </h2>
        <span className="rf-top-rule" />
      </div>
      <div style={{ paddingTop: 16, display: "flex", flexDirection: "column" }}>
        {visibleArticles.map((article, index) => {
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
              <span className="rf-top-rank">{String(index + 1).padStart(2, "0")}</span>
              <span style={{ flex: 1, fontSize: 14.5, lineHeight: 1.55, color: "var(--rf-text-dim)" }}>
                {article.titleKo}
              </span>
              <span className="rf-mono" style={{ fontSize: 12.5, color: badge.color, whiteSpace: "nowrap" }}>
                {badge.label}
              </span>
            </div>
          );
        })}
        {hasMore && (
          <button
            type="button"
            className="rf-btn"
            style={{ alignSelf: "flex-start", marginTop: 10, border: "none", padding: 0 }}
            onClick={() => setExpanded((prev) => !prev)}
          >
            {expanded ? "접기" : "더보기"}
          </button>
        )}
      </div>
    </section>
  );
}
