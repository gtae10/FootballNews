import { Fragment, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiFetch } from "../api/client";
import { isUnauthorized } from "../utils/handleApiError";
import { splitIntoParagraphs, tierBadge, timeAgo } from "../utils/articleDisplay";

// 본문 문단 사이에 끼워 넣을 이미지는 최대 2장으로 제한한다 (너무 많으면 요약문
// 사이사이가 이미지로 도배돼 오히려 읽기 어려워진다).
const MAX_INLINE_IMAGES = 2;

function hideOnError(e) {
  e.currentTarget.style.display = "none";
}

// 본문 크롤링으로 찾은 이미지(images)를 imageUrl보다 우선한다. imageUrl(RSS
// 썸네일)은 종종 "Sky Sports News" 같은 매체 브랜드 그래픽/섹션 공통 템플릿
// 이미지라 선수·경기 사진이 아닌 경우가 있는 반면, images는 실제 본문에서
// 크롤링한 사진이라 그럴 가능성이 낮다(사용자 피드백으로 확인됨: Sky Sports
// "Paper Talk" 로고 그래픽이 대표 이미지로 뜨는 문제). 본문 이미지가 하나도
// 없을 때만 imageUrl로 폴백한다(그마저 없으면 이미지 없는 기사로 처리).
function splitHeroAndInlineImages(article) {
  const bodyImages = article.images ?? [];
  if (bodyImages.length > 0) {
    return { hero: bodyImages[0], inline: bodyImages.slice(1, 1 + MAX_INLINE_IMAGES) };
  }
  return { hero: article.imageUrl ?? null, inline: [] };
}

// 문단 배열 안에서 이미지를 끼워 넣을 위치(문단 인덱스)를 고르게 분산시킨다.
// 예: 문단 6개 + 이미지 2장이면 대략 2번째, 4번째 문단 뒤에 하나씩 배치된다.
function buildImagePlacements(paragraphCount, inlineImages) {
  const placements = new Map();
  inlineImages.forEach((url, i) => {
    const afterIndex = Math.min(
      Math.floor(((i + 1) * paragraphCount) / (inlineImages.length + 1)),
      paragraphCount - 1
    );
    placements.set(afterIndex, url);
  });
  return placements;
}

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

      {!loading && !error && article && (() => {
        const { hero, inline } = splitHeroAndInlineImages(article);
        const paragraphs = article.contentKo ? splitIntoParagraphs(article.contentKo) : [];
        const imagePlacements = buildImagePlacements(paragraphs.length, inline);

        return (
          <div style={{ paddingTop: 28 }}>
            {hero && (
              <img
                className="rf-detail-hero"
                src={hero}
                alt=""
                loading="lazy"
                // 원본 서버가 이미지를 지웠거나 핫링크를 막으면 이미지 영역만 숨기고
                // 텍스트는 그대로 보여준다 (썸네일과 동일한 폴백 원칙).
                onError={hideOnError}
                style={{ marginBottom: 20 }}
              />
            )}
            <div className="rf-article-meta" style={{ paddingBottom: 16 }}>
              <span style={{ color: tierBadge(article.sourceTier).color, fontSize: 12.5 }}>
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
              {paragraphs.length > 0 ? (
                paragraphs.map((paragraph, index) => (
                  <Fragment key={index}>
                    <p>{paragraph}</p>
                    {imagePlacements.has(index) && (
                      <img
                        className="rf-detail-image"
                        src={imagePlacements.get(index)}
                        alt=""
                        loading="lazy"
                        onError={hideOnError}
                      />
                    )}
                  </Fragment>
                ))
              ) : (
                <p>본문 번역이 아직 준비되지 않았습니다. 원문 링크에서 전체 기사를 확인해 주세요.</p>
              )}
            </div>
            <a href={article.originalUrl} target="_blank" rel="noreferrer" className="rf-btn" style={{ display: "inline-block" }}>
              원문 기사 열기 ↗
            </a>
          </div>
        );
      })()}
    </div>
  );
}
