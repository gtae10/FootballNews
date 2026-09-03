import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiFetch } from "../api/client";
import { isUnauthorized } from "../utils/handleApiError";
import { tierBadge, timeAgo } from "../utils/articleDisplay";

export default function ArticleDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    apiFetch(`/articles/${id}`)
      .then(setArticle)
      .catch((err) => {
        if (isUnauthorized(err)) {
          navigate("/login", { replace: true });
          return;
        }
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [id, navigate]);

  return (
    <div style={{ paddingTop: 26 }}>
      <Link to="/feed" className="rf-mono" style={{ fontSize: 11, letterSpacing: "0.14em", color: "var(--rf-muted-1)" }}>
        ← 피드
      </Link>

      {loading && (
        <p className="rf-status" style={{ paddingTop: 24 }}>
          불러오는 중...
        </p>
      )}
      {error && (
        <p className="rf-error" role="alert" style={{ paddingTop: 24 }}>
          기사를 불러오지 못했습니다 ({error})
        </p>
      )}

      {!loading && !error && article && (
        <div style={{ paddingTop: 28 }}>
          <div className="rf-article-meta" style={{ paddingBottom: 16 }}>
            <span style={{ color: tierBadge(article.sourceTier).color }}>
              {tierBadge(article.sourceTier).label}
            </span>
            <span>{article.source}</span>
            <span>·</span>
            <span>{timeAgo(article.publishedAt)}</span>
          </div>
          <h1 className="rf-detail-title" style={{ margin: 0 }}>
            {article.titleKo ?? article.titleOriginal}
          </h1>
          {article.titleKo && article.titleOriginal && (
            <p style={{ fontSize: 15, color: "var(--rf-muted-2)", lineHeight: 1.6, paddingTop: 14, fontStyle: "italic" }}>
              {article.titleOriginal}
            </p>
          )}
          <div className="rf-detail-body">
            {article.contentKo ?? "본문 번역이 아직 준비되지 않았습니다. 원문 링크에서 전체 기사를 확인해 주세요."}
          </div>
          <a href={article.originalUrl} target="_blank" rel="noreferrer" className="rf-btn" style={{ display: "inline-block" }}>
            원문 기사 열기 ↗
          </a>
        </div>
      )}
    </div>
  );
}
