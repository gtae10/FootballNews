import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import SettingsPage from "./SettingsPage";
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

function mockApiFetchDefaults(overrides = {}) {
  apiFetch.mockImplementation(async (path, options = {}) => {
    const method = options.method ?? "GET";

    if (path === "/clubs" && method === "GET") return CLUBS;
    if (path === "/users/me/preferences" && method === "GET") {
      return { clubs: [CLUBS[0]], notificationTrustLevel: 3 };
    }
    if (path === "/reporter-suggestions/me" && method === "GET") {
      return overrides.suggestions ?? [];
    }
    if (path === "/users/me/nickname" && method === "PATCH") return {};
    if (path === "/users/me/preferences" && method === "PUT") return {};
    if (path === "/reporter-suggestions" && method === "POST") return {};
    if (path === "/users/me" && method === "DELETE") return null;

    throw new Error(`unexpected apiFetch call: ${method} ${path}`);
  });
}

function renderSettingsPage() {
  return render(
    <MemoryRouter initialEntries={["/settings"]}>
      <Routes>
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/feed" element={<div>피드 페이지</div>} />
        <Route path="/login" element={<div>로그인 페이지</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("SettingsPage", () => {
  let refresh;
  let logout;

  beforeEach(() => {
    vi.clearAllMocks();
    refresh = vi.fn().mockResolvedValue();
    logout = vi.fn().mockResolvedValue();
    useAuth.mockReturnValue({
      user: { id: 1, email: "test@example.com", nickname: null, onboarded: true },
      logout,
      refresh,
    });
    mockApiFetchDefaults();
  });

  it("계정 이메일과 구독 중인 구단을 보여준다", async () => {
    renderSettingsPage();

    expect(screen.getByText(/test@example.com/)).toBeInTheDocument();

    await waitFor(() => expect(screen.getByRole("checkbox", { name: "Liverpool" })).toBeChecked());
    expect(screen.getByRole("checkbox", { name: "Arsenal" })).not.toBeChecked();
  });

  it("닉네임을 변경하면 저장 후 인증 정보를 새로고침한다", async () => {
    renderSettingsPage();
    const user = userEvent.setup();

    const input = screen.getByLabelText("닉네임");
    await user.clear(input);
    await user.type(input, "리버풀팬");
    await user.click(screen.getByRole("button", { name: "변경" }));

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/users/me/nickname",
        expect.objectContaining({ method: "PATCH", body: JSON.stringify({ nickname: "리버풀팬" }) })
      )
    );
    expect(refresh).toHaveBeenCalled();
  });

  it("기자 제보를 제출하면 내 제보 목록을 새로고침한다", async () => {
    mockApiFetchDefaults({ suggestions: [] });
    renderSettingsPage();
    const user = userEvent.setup();

    await waitFor(() => expect(screen.getByText("아직 제보한 내역이 없습니다.")).toBeInTheDocument());

    await user.type(screen.getByLabelText("트위터(X) 핸들"), "@some_reporter");

    apiFetch.mockImplementation(async (path, options = {}) => {
      const method = options.method ?? "GET";
      if (path === "/reporter-suggestions" && method === "POST") return {};
      if (path === "/reporter-suggestions/me" && method === "GET") {
        return [{ id: 1, twitterHandle: "@some_reporter", name: null, league: null, memo: null }];
      }
      if (path === "/clubs") return CLUBS;
      if (path === "/users/me/preferences") return { clubs: [], notificationTrustLevel: 3 };
      return {};
    });

    await user.click(screen.getByRole("button", { name: "제보하기" }));

    await waitFor(() => expect(screen.getByText("@some_reporter")).toBeInTheDocument());
  });

  it("탈퇴 확인 전에는 계정을 삭제하지 않는다", async () => {
    renderSettingsPage();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "탈퇴하기" }));

    expect(screen.getByText(/정말 탈퇴하시겠습니까/)).toBeInTheDocument();
    expect(apiFetch).not.toHaveBeenCalledWith("/users/me", expect.objectContaining({ method: "DELETE" }));

    await user.click(screen.getByRole("button", { name: "탈퇴 확인" }));

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith("/users/me", expect.objectContaining({ method: "DELETE" }))
    );
    expect(refresh).toHaveBeenCalled();
  });

  describe("최애팀", () => {
    it("저장된 최애팀이 별표로 표시된다", async () => {
      apiFetch.mockImplementation(async (path, options = {}) => {
        const method = options.method ?? "GET";
        if (path === "/clubs" && method === "GET") return CLUBS;
        if (path === "/users/me/preferences" && method === "GET") {
          return { clubs: [CLUBS[0], CLUBS[1]], notificationTrustLevel: 3, favoriteClub: CLUBS[0] };
        }
        if (path === "/reporter-suggestions/me" && method === "GET") return [];
        return {};
      });

      renderSettingsPage();

      expect(await screen.findByRole("button", { name: "★ Liverpool" })).toHaveAttribute("data-selected", "true");
      expect(screen.getByRole("button", { name: "★ Arsenal" })).toHaveAttribute("data-selected", "false");
    });

    it("최애팀을 바꿔서 저장하면 favoriteClubId가 함께 전달된다", async () => {
      mockApiFetchDefaults();
      renderSettingsPage();
      const user = userEvent.setup();

      await user.click(await screen.findByRole("button", { name: "★ Liverpool" }));
      await user.click(screen.getByRole("button", { name: "관심 설정 저장" }));

      await waitFor(() =>
        expect(apiFetch).toHaveBeenCalledWith(
          "/users/me/preferences",
          expect.objectContaining({
            method: "PUT",
            body: JSON.stringify({ clubIds: [1], notificationTrustLevel: 3, favoriteClubId: 1 }),
          })
        )
      );
    });

    it("최애팀 구단의 관심 설정을 해제하면 최애팀 지정도 함께 풀린다", async () => {
      apiFetch.mockImplementation(async (path, options = {}) => {
        const method = options.method ?? "GET";
        if (path === "/clubs" && method === "GET") return CLUBS;
        if (path === "/users/me/preferences" && method === "GET") {
          return { clubs: [CLUBS[0]], notificationTrustLevel: 3, favoriteClub: CLUBS[0] };
        }
        if (path === "/reporter-suggestions/me" && method === "GET") return [];
        return {};
      });

      renderSettingsPage();

      await screen.findByRole("button", { name: "★ Liverpool" });
      await userEvent.setup().click(screen.getByRole("checkbox", { name: "Liverpool" }));

      expect(screen.queryByRole("button", { name: "★ Liverpool" })).not.toBeInTheDocument();
    });
  });

  describe("게스트 모드", () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: null,
        logout,
        refresh,
        isGuest: true,
      });
    });

    it("설정 화면 대신 로그인 안내를 보여주고 인증이 필요한 API를 호출하지 않는다", async () => {
      renderSettingsPage();

      expect(await screen.findByText(/로그인이 필요한 기능입니다/)).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Google 로그인하러 가기" })).toBeInTheDocument();

      expect(apiFetch).not.toHaveBeenCalledWith("/users/me/preferences");
      expect(apiFetch).not.toHaveBeenCalledWith("/reporter-suggestions/me");
      expect(screen.queryByRole("button", { name: "제보하기" })).not.toBeInTheDocument();
    });
  });
});
