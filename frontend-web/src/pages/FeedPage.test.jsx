import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import FeedPage from "./FeedPage";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";

vi.mock("../api/client", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

const CLUBS = [
  { id: 1, name: "Liverpool", league: "EPL" },
  { id: 2, name: "Arsenal", league: "EPL" },
];

function mockApiFetch({ preferencesShouldFail } = {}) {
  apiFetch.mockImplementation(async (path) => {
    if (path === "/clubs") return CLUBS;
    if (path === "/articles/top?limit=10") return [];
    if (path === "/users/me/preferences") {
      if (preferencesShouldFail) throw new Error("이 경로는 게스트에서 호출되면 안 됨");
      return { clubs: [CLUBS[0]] };
    }
    if (path.startsWith("/articles")) return { content: [] };
    throw new Error(`unexpected apiFetch call: ${path}`);
  });
}

function renderFeedPage() {
  return render(
    <MemoryRouter initialEntries={["/feed"]}>
      <Routes>
        <Route path="/feed" element={<FeedPage />} />
        <Route path="/login" element={<div>로그인 페이지</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("FeedPage 게스트 모드", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("게스트 모드에서는 /users/me/preferences를 호출하지 않고 전체 구단으로 시작한다", async () => {
    mockApiFetch({ preferencesShouldFail: true });
    useAuth.mockReturnValue({ isGuest: true });

    renderFeedPage();

    await waitFor(() => expect(screen.getByRole("combobox")).toHaveValue(""));
    expect(apiFetch).not.toHaveBeenCalledWith("/users/me/preferences");
  });

  it("로그인한 사용자는 관심 구단 기준으로 필터가 채워진다", async () => {
    mockApiFetch();
    useAuth.mockReturnValue({ isGuest: false });

    renderFeedPage();

    await waitFor(() => expect(screen.getByRole("combobox")).toHaveValue("Liverpool"));
  });
});

describe("FeedPage 기사 썸네일", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ isGuest: true });
  });

  it("imageUrl이 있으면 썸네일 이미지를 보여준다", async () => {
    apiFetch.mockImplementation(async (path) => {
      if (path === "/clubs") return CLUBS;
      if (path === "/articles/top?limit=10") return [];
      if (path.startsWith("/articles")) {
        return {
          content: [
            {
              id: 1,
              titleKo: "제목",
              source: "Sky Sports Football",
              publishedAt: "2026-09-04T10:00:00Z",
              originalUrl: "https://example.com/1",
              clubs: ["Liverpool"],
              sourceTier: 1,
              imageUrl: "https://example.com/thumb.jpg",
            },
          ],
        };
      }
      throw new Error(`unexpected apiFetch call: ${path}`);
    });

    const { container } = renderFeedPage();

    await screen.findByText("제목");
    // 썸네일은 장식용(alt="")이라 접근성 트리의 "img" role에서 제외되므로
    // container에서 직접 조회한다.
    const image = container.querySelector("img.rf-article-thumb");
    expect(image).toHaveAttribute("src", "https://example.com/thumb.jpg");
  });

  it("imageUrl이 없으면 이미지 없이 텍스트만 보여준다", async () => {
    apiFetch.mockImplementation(async (path) => {
      if (path === "/clubs") return CLUBS;
      if (path === "/articles/top?limit=10") return [];
      if (path.startsWith("/articles")) {
        return {
          content: [
            {
              id: 1,
              titleKo: "이미지 없는 기사",
              source: "Sky Sports Football",
              publishedAt: "2026-09-04T10:00:00Z",
              originalUrl: "https://example.com/1",
              clubs: ["Liverpool"],
              sourceTier: 1,
              imageUrl: null,
            },
          ],
        };
      }
      throw new Error(`unexpected apiFetch call: ${path}`);
    });

    const { container } = renderFeedPage();

    expect(await screen.findByText("이미지 없는 기사")).toBeInTheDocument();
    expect(container.querySelector("img.rf-article-thumb")).not.toBeInTheDocument();
  });

  it("이미지 로드에 실패하면 이미지 영역을 숨기고 텍스트는 그대로 남는다", async () => {
    apiFetch.mockImplementation(async (path) => {
      if (path === "/clubs") return CLUBS;
      if (path === "/articles/top?limit=10") return [];
      if (path.startsWith("/articles")) {
        return {
          content: [
            {
              id: 1,
              titleKo: "깨진 이미지 기사",
              source: "Sky Sports Football",
              publishedAt: "2026-09-04T10:00:00Z",
              originalUrl: "https://example.com/1",
              clubs: ["Liverpool"],
              sourceTier: 1,
              imageUrl: "https://example.com/broken.jpg",
            },
          ],
        };
      }
      throw new Error(`unexpected apiFetch call: ${path}`);
    });

    const { container } = renderFeedPage();

    await screen.findByText("깨진 이미지 기사");
    const image = container.querySelector("img.rf-article-thumb");
    fireEvent.error(image);

    expect(image).toHaveStyle({ display: "none" });
    expect(screen.getByText("깨진 이미지 기사")).toBeInTheDocument();
  });
});
