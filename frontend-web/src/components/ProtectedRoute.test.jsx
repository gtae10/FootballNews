import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import ProtectedRoute from "./ProtectedRoute";
import { useAuth } from "../context/AuthContext";

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

function renderProtectedRoute(initialPath = "/feed") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>로그인 페이지</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/feed" element={<div>피드 페이지</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  it("인증 정보 로딩 중에는 로딩 표시를 보여준다", () => {
    useAuth.mockReturnValue({ user: null, loading: true });

    renderProtectedRoute();

    expect(screen.getByText("불러오는 중...")).toBeInTheDocument();
  });

  it("로그인하지 않은 사용자는 /login으로 리다이렉트된다", () => {
    useAuth.mockReturnValue({ user: null, loading: false });

    renderProtectedRoute();

    expect(screen.getByText("로그인 페이지")).toBeInTheDocument();
  });

  it("로그인한 사용자는 보호된 페이지를 그대로 볼 수 있다", () => {
    useAuth.mockReturnValue({ user: { id: 1, email: "test@example.com" }, loading: false });

    renderProtectedRoute();

    expect(screen.getByText("피드 페이지")).toBeInTheDocument();
  });
});
