import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

  it("로그인한 사용자도 기본값은 전체 탭이라 club 파라미터 없이 전체 기사를 조회한다", async () => {
    // 회귀 테스트: 예전엔 로그인 사용자의 관심 구단 중 첫 번째로 전체 탭 필터가
    // 자동으로 채워지는 버그가 있었다 — "전체" 탭은 club 필터가 전혀 없어야 한다.
    mockApiFetch();
    useAuth.mockReturnValue({ isGuest: false });

    renderFeedPage();

    await waitFor(() => expect(screen.getByRole("combobox")).toHaveValue(""));
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/articles"));
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

describe("FeedPage 카테고리 필터", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ isGuest: true });
  });

  it("기본값은 전체이며, 카테고리 파라미터 없이 조회한다", async () => {
    mockApiFetch();
    renderFeedPage();

    await waitFor(() => expect(screen.getByRole("button", { name: "전체" })).toHaveAttribute("data-selected", "true"));
    expect(apiFetch).toHaveBeenCalledWith("/articles");
  });

  it("경기 칩을 누르면 category=MATCH로 다시 조회한다", async () => {
    mockApiFetch();
    renderFeedPage();
    const user = userEvent.setup();

    await screen.findByRole("button", { name: "경기" });
    await user.click(screen.getByRole("button", { name: "경기" }));

    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/articles?category=MATCH"));
    expect(screen.getByRole("button", { name: "경기" })).toHaveAttribute("data-selected", "true");
    expect(screen.getByRole("button", { name: "전체" })).toHaveAttribute("data-selected", "false");
  });

  it("club과 category를 함께 지정하면 두 파라미터가 모두 전달된다", async () => {
    mockApiFetch();
    renderFeedPage();
    const user = userEvent.setup();

    await screen.findByRole("option", { name: "Liverpool" });
    await user.selectOptions(screen.getByRole("combobox"), "Liverpool");
    await user.click(screen.getByRole("button", { name: "이적" }));

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith("/articles?club=Liverpool&category=TRANSFER")
    );
  });
});

describe("FeedPage 전체/관심구단 탭", () => {
  const PREFERENCES = {
    clubs: [CLUBS[0], CLUBS[1]],
    favoriteClub: CLUBS[0],
  };

  function mockTabApiFetch({ isGuest }) {
    apiFetch.mockImplementation(async (path) => {
      if (path === "/clubs") return CLUBS;
      if (path === "/articles/top?limit=10") return [];
      if (path === "/users/me/preferences") {
        if (isGuest) throw new Error("게스트는 이 경로를 호출하면 안 됨");
        return PREFERENCES;
      }
      if (path.startsWith("/articles")) return { content: [] };
      throw new Error(`unexpected apiFetch call: ${path}`);
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("기본은 전체 탭이며, 로그인 사용자라도 club 파라미터 없이 조회한다", async () => {
    mockTabApiFetch({ isGuest: false });
    useAuth.mockReturnValue({ isGuest: false });

    renderFeedPage();

    await waitFor(() => expect(screen.getByRole("tab", { name: "전체" })).toHaveAttribute("aria-selected", "true"));
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/articles"));
  });

  it("관심구단 탭을 누르면 관심 구단 전체 목록으로 clubs 파라미터를 조회한다", async () => {
    mockTabApiFetch({ isGuest: false });
    useAuth.mockReturnValue({ isGuest: false });
    renderFeedPage();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("tab", { name: "관심구단" }));

    // URLSearchParams가 쉼표를 퍼센트 인코딩하지만(백엔드는 디코딩 후 동일하게 처리),
    // 실제로 만들어지는 요청 문자열 그대로 검증한다.
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/articles?clubs=Liverpool%2CArsenal"));
  });

  it("관심구단 탭에서 최애팀만 보기를 선택하면 club 파라미터 하나만 조회한다", async () => {
    mockTabApiFetch({ isGuest: false });
    useAuth.mockReturnValue({ isGuest: false });
    renderFeedPage();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("tab", { name: "관심구단" }));
    await user.click(await screen.findByRole("button", { name: "최애팀만" }));

    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/articles?club=Liverpool"));
  });

  it("게스트가 관심구단 탭을 누르면 로그인 안내만 보이고 기사를 조회하지 않는다", async () => {
    mockTabApiFetch({ isGuest: true });
    useAuth.mockReturnValue({ isGuest: true });
    renderFeedPage();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("tab", { name: "관심구단" }));

    expect(await screen.findByRole("link", { name: /로그인하면/ })).toBeInTheDocument();
    expect(apiFetch).not.toHaveBeenCalledWith("/users/me/preferences");
    expect(apiFetch).not.toHaveBeenCalledWith(expect.stringContaining("clubs="));
  });
});
