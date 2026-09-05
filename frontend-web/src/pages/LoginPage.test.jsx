import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import LoginPage from "./LoginPage";
import { useAuth } from "../context/AuthContext";

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/feed" element={<div>피드 페이지</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("LoginPage 게스트 모드", () => {
  let loginAsGuest;

  beforeEach(() => {
    loginAsGuest = vi.fn();
    useAuth.mockReturnValue({ loginAsGuest });
  });

  it("게스트로 둘러보기 버튼이 보인다", () => {
    renderLoginPage();

    expect(screen.getByRole("button", { name: "게스트로 둘러보기" })).toBeInTheDocument();
  });

  it("게스트로 둘러보기를 누르면 loginAsGuest를 호출하고 /feed로 이동한다", async () => {
    renderLoginPage();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "게스트로 둘러보기" }));

    expect(loginAsGuest).toHaveBeenCalled();
    expect(screen.getByText("피드 페이지")).toBeInTheDocument();
  });
});
