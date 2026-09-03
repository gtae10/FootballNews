import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import OnboardingGate from "./OnboardingGate";
import { useAuth } from "../context/AuthContext";

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

function renderGate() {
  return render(
    <MemoryRouter initialEntries={["/feed"]}>
      <Routes>
        <Route path="/onboarding" element={<div>온보딩 페이지</div>} />
        <Route element={<OnboardingGate />}>
          <Route path="/feed" element={<div>피드 페이지</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("OnboardingGate", () => {
  it("온보딩을 완료하지 않은 사용자는 /onboarding으로 리다이렉트된다", () => {
    useAuth.mockReturnValue({ user: { id: 1, onboarded: false } });

    renderGate();

    expect(screen.getByText("온보딩 페이지")).toBeInTheDocument();
  });

  it("온보딩을 완료한 사용자는 피드 페이지를 그대로 볼 수 있다", () => {
    useAuth.mockReturnValue({ user: { id: 1, onboarded: true } });

    renderGate();

    expect(screen.getByText("피드 페이지")).toBeInTheDocument();
  });
});
