import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import FavoriteTeamSection from "./FavoriteTeamSection";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";

vi.mock("../api/client", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

function renderSection(onViewAll = vi.fn()) {
  return render(
    <MemoryRouter initialEntries={["/feed"]}>
      <Routes>
        <Route path="/feed" element={<FavoriteTeamSection onViewAll={onViewAll} />} />
        <Route path="/settings" element={<div>설정 페이지</div>} />
        <Route path="/articles/:id" element={<div>기사 상세 페이지</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("FavoriteTeamSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("게스트에게는 아무것도 보여주지 않는다", async () => {
    useAuth.mockReturnValue({ isGuest: true });

    const { container } = renderSection();

    expect(apiFetch).not.toHaveBeenCalled();
    expect(container).toBeEmptyDOMElement();
  });

  it("최애팀이 없으면 설정 안내 링크를 보여준다", async () => {
    useAuth.mockReturnValue({ isGuest: false });
    apiFetch.mockImplementation(async (path) => {
      if (path === "/users/me/preferences") return { clubs: [], notificationTrustLevel: 3, favoriteClub: null };
      throw new Error(`unexpected apiFetch call: ${path}`);
    });

    renderSection();

    expect(await screen.findByText("최애팀을 설정해보세요 →")).toBeInTheDocument();
  });

  it("최애팀이 있으면 해당 구단 기사를 최신순 5건 조회해 보여준다", async () => {
    useAuth.mockReturnValue({ isGuest: false });
    apiFetch.mockImplementation(async (path) => {
      if (path === "/users/me/preferences") {
        return { clubs: [{ id: 1, name: "Liverpool", league: "EPL" }], notificationTrustLevel: 3, favoriteClub: { id: 1, name: "Liverpool", league: "EPL" } };
      }
      if (path === "/articles?club=Liverpool&size=5") {
        return {
          content: [
            { id: 1, titleKo: "리버풀 소식 1", publishedAt: "2026-09-04T10:00:00Z", sourceTier: 1 },
            { id: 2, titleKo: "리버풀 소식 2", publishedAt: "2026-09-04T09:00:00Z", sourceTier: 2 },
          ],
        };
      }
      throw new Error(`unexpected apiFetch call: ${path}`);
    });

    renderSection();

    expect(await screen.findByText("Liverpool 소식")).toBeInTheDocument();
    expect(screen.getByText("리버풀 소식 1")).toBeInTheDocument();
    expect(screen.getByText("리버풀 소식 2")).toBeInTheDocument();
  });

  it("더보기를 누르면 onViewAll이 최애팀 이름과 함께 호출된다", async () => {
    useAuth.mockReturnValue({ isGuest: false });
    apiFetch.mockImplementation(async (path) => {
      if (path === "/users/me/preferences") {
        return { clubs: [{ id: 1, name: "Liverpool", league: "EPL" }], notificationTrustLevel: 3, favoriteClub: { id: 1, name: "Liverpool", league: "EPL" } };
      }
      if (path === "/articles?club=Liverpool&size=5") {
        return { content: [{ id: 1, titleKo: "리버풀 소식", publishedAt: "2026-09-04T10:00:00Z", sourceTier: 1 }] };
      }
      throw new Error(`unexpected apiFetch call: ${path}`);
    });
    const onViewAll = vi.fn();

    renderSection(onViewAll);
    const user = userEvent.setup();

    await screen.findByText("리버풀 소식");
    await user.click(screen.getByRole("button", { name: "더보기" }));

    expect(onViewAll).toHaveBeenCalledWith("Liverpool");
  });

  it("기사를 클릭하면 상세 페이지로 이동한다", async () => {
    useAuth.mockReturnValue({ isGuest: false });
    apiFetch.mockImplementation(async (path) => {
      if (path === "/users/me/preferences") {
        return { clubs: [{ id: 1, name: "Liverpool", league: "EPL" }], notificationTrustLevel: 3, favoriteClub: { id: 1, name: "Liverpool", league: "EPL" } };
      }
      if (path === "/articles?club=Liverpool&size=5") {
        return { content: [{ id: 42, titleKo: "리버풀 소식", publishedAt: "2026-09-04T10:00:00Z", sourceTier: 1 }] };
      }
      throw new Error(`unexpected apiFetch call: ${path}`);
    });

    renderSection();
    const user = userEvent.setup();

    await user.click(await screen.findByText("리버풀 소식"));

    expect(await screen.findByText("기사 상세 페이지")).toBeInTheDocument();
  });
});
