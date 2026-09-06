import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import OnboardingPage from "./OnboardingPage";
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

function renderOnboardingPage() {
  return render(
    <MemoryRouter initialEntries={["/onboarding"]}>
      <Routes>
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/feed" element={<div>피드 페이지</div>} />
        <Route path="/login" element={<div>로그인 페이지</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("OnboardingPage 최애팀 선택", () => {
  let refresh;

  beforeEach(() => {
    vi.clearAllMocks();
    refresh = vi.fn().mockResolvedValue();
    useAuth.mockReturnValue({ refresh });
    apiFetch.mockImplementation(async (path, options = {}) => {
      if (path === "/clubs") return CLUBS;
      if (path === "/users/me/preferences" && (options.method ?? "GET") === "PUT") return {};
      throw new Error(`unexpected apiFetch call: ${path}`);
    });
  });

  it("구단을 선택하기 전에는 최애팀 선택 영역이 보이지 않는다", async () => {
    renderOnboardingPage();

    await screen.findByText("관심 구단을 골라주세요");
    expect(screen.queryByText("최애팀 (선택)")).not.toBeInTheDocument();
  });

  it("구단을 선택하면 그 중에서 최애팀(★)을 고를 수 있다", async () => {
    renderOnboardingPage();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Liverpool" }));

    expect(await screen.findByText("최애팀 (선택)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "★ Liverpool" })).toBeInTheDocument();
  });

  it("관심 구단에서 제외하면 최애팀 지정도 함께 풀린다", async () => {
    renderOnboardingPage();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Liverpool" }));
    await user.click(screen.getByRole("button", { name: "★ Liverpool" }));
    expect(screen.getByRole("button", { name: "★ Liverpool" })).toHaveAttribute("data-selected", "true");

    await user.click(screen.getByRole("button", { name: "Liverpool" }));

    expect(screen.queryByText("최애팀 (선택)")).not.toBeInTheDocument();
  });

  it("최애팀을 선택하고 완료하면 favoriteClubId가 함께 저장된다", async () => {
    renderOnboardingPage();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Liverpool" }));
    await user.click(screen.getByRole("button", { name: "★ Liverpool" }));
    await user.click(screen.getByRole("button", { name: "다음" }));
    await user.click(screen.getByRole("button", { name: "다음" }));

    await user.click(await screen.findByRole("button", { name: "피드로 이동" }));

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
});
