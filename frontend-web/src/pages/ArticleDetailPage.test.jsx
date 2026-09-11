import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import ArticleDetailPage from "./ArticleDetailPage";
import { apiFetch } from "../api/client";

vi.mock("../api/client", () => ({
  apiFetch: vi.fn(),
}));

const BASE_ARTICLE = {
  id: 1,
  titleKo: "번역된 제목",
  titleOriginal: "Original Title",
  contentKo:
    "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다. 네 번째 문장입니다.",
  source: "Sky Sports Football",
  originalUrl: "https://example.com/article/1",
  publishedAt: "2026-08-30T10:00:00Z",
  translatedAt: "2026-08-30T10:05:00Z",
  sourceTier: 1,
  imageUrl: null,
  category: "MATCH",
  images: [],
};

// FeedPage와 동일하게 대표/본문 이미지는 alt=""(장식용)로 렌더링되므로 접근성 트리에
// "img" role로 노출되지 않는다 — role 쿼리 대신 컨테이너에서 직접 <img> 태그를 찾는다.
function renderDetailPage() {
  return render(
    <MemoryRouter initialEntries={["/articles/1"]}>
      <Routes>
        <Route path="/articles/:id" element={<ArticleDetailPage />} />
        <Route path="/login" element={<div>로그인 페이지</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ArticleDetailPage 이미지 표시", () => {
  it("본문 크롤링 이미지가 없으면 imageUrl(대표 썸네일)을 상단 대표 이미지로 보여준다", async () => {
    apiFetch.mockResolvedValue({ ...BASE_ARTICLE, imageUrl: "https://example.com/thumb.jpg", images: [] });

    const { container } = renderDetailPage();
    await screen.findByText("번역된 제목");

    const hero = container.querySelector(".rf-detail-hero");
    expect(hero).not.toBeNull();
    expect(hero).toHaveAttribute("src", "https://example.com/thumb.jpg");
  });

  it("본문 크롤링 이미지가 있으면 imageUrl보다 우선해서 대표 이미지로 쓴다", async () => {
    // Sky Sports "Paper Talk" 로고 그래픽처럼 imageUrl이 매체 브랜드 템플릿
    // 이미지일 수 있어, 실제 본문에서 크롤링한 사진(images)을 우선한다.
    apiFetch.mockResolvedValue({
      ...BASE_ARTICLE,
      imageUrl: "https://example.com/skysports-brand-thumb.jpg",
      images: ["https://example.com/body1.jpg", "https://example.com/body2.jpg"],
    });

    const { container } = renderDetailPage();
    await screen.findByText("번역된 제목");

    const hero = container.querySelector(".rf-detail-hero");
    expect(hero).toHaveAttribute("src", "https://example.com/body1.jpg");
  });

  it("imageUrl과 images가 모두 없으면 이미지 영역을 렌더링하지 않는다", async () => {
    apiFetch.mockResolvedValue({ ...BASE_ARTICLE, imageUrl: null, images: [] });

    const { container } = renderDetailPage();
    await screen.findByText("번역된 제목");

    expect(container.querySelectorAll("img")).toHaveLength(0);
  });

  it("본문 크롤링 이미지를 문단 사이에 끼워 넣되 최대 2장까지만 보여준다", async () => {
    apiFetch.mockResolvedValue({
      ...BASE_ARTICLE,
      imageUrl: "https://example.com/thumb.jpg",
      images: [
        "https://example.com/body1.jpg",
        "https://example.com/body2.jpg",
        "https://example.com/body3.jpg",
      ],
    });

    const { container } = renderDetailPage();
    await screen.findByText("번역된 제목");

    const inlineImages = container.querySelectorAll(".rf-detail-image");
    expect(inlineImages).toHaveLength(2);
    expect(Array.from(inlineImages).map((img) => img.getAttribute("src"))).toEqual([
      "https://example.com/body2.jpg",
      "https://example.com/body3.jpg",
    ]);
  });

  it("이미지 로드 실패 시 해당 이미지만 숨기고 텍스트는 그대로 보여준다", async () => {
    apiFetch.mockResolvedValue({ ...BASE_ARTICLE, imageUrl: "https://example.com/thumb.jpg" });

    const { container } = renderDetailPage();
    await screen.findByText("번역된 제목");

    const hero = container.querySelector(".rf-detail-hero");
    hero.dispatchEvent(new Event("error"));

    await waitFor(() => expect(hero.style.display).toBe("none"));
    expect(screen.getByText("번역된 제목")).toBeInTheDocument();
  });

  it("본문 번역이 없으면 안내 문구를 보여주고 이미지를 문단에 끼워 넣지 않는다", async () => {
    apiFetch.mockResolvedValue({
      ...BASE_ARTICLE,
      contentKo: null,
      imageUrl: "https://example.com/thumb.jpg",
      images: ["https://example.com/body1.jpg"],
    });

    const { container } = renderDetailPage();

    await screen.findByText(
      "본문 번역이 아직 준비되지 않았습니다. 원문 링크에서 전체 기사를 확인해 주세요."
    );
    expect(container.querySelectorAll(".rf-detail-image")).toHaveLength(0);
  });
});
