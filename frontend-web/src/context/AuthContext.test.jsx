import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./AuthContext";
import { apiFetch } from "../api/client";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual("../api/client");
  return { ...actual, apiFetch: vi.fn() };
});

function Probe() {
  const { user, loading, isGuest, loginAsGuest, logout } = useAuth();
  if (loading) return <p>불러오는 중...</p>;
  return (
    <div>
      <p>user: {user ? user.email : "none"}</p>
      <p>isGuest: {String(isGuest)}</p>
      <button onClick={loginAsGuest}>게스트로 둘러보기</button>
      <button onClick={logout}>로그아웃</button>
    </div>
  );
}

function renderProbe() {
  return render(
    <AuthProvider>
      <Probe />
    </AuthProvider>
  );
}

describe("AuthContext 게스트 모드", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    apiFetch.mockImplementation(async (path) => {
      if (path === "/auth/me") {
        const { ApiError } = await vi.importActual("../api/client");
        throw new ApiError(401, "unauthorized");
      }
      throw new Error(`unexpected call: ${path}`);
    });
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it("loginAsGuest를 호출하면 isGuest가 true가 되고 user는 null로 유지된다", async () => {
    renderProbe();
    const user = userEvent.setup();

    await waitFor(() => expect(screen.getByText("isGuest: false")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "게스트로 둘러보기" }));

    expect(screen.getByText("isGuest: true")).toBeInTheDocument();
    expect(screen.getByText("user: none")).toBeInTheDocument();
  });

  it("게스트 상태는 세션에 저장되어 새로고침(재마운트) 후에도 유지된다", async () => {
    const { unmount } = renderProbe();
    const user = userEvent.setup();

    await waitFor(() => expect(screen.getByText("isGuest: false")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "게스트로 둘러보기" }));
    expect(screen.getByText("isGuest: true")).toBeInTheDocument();

    unmount();
    renderProbe();

    await waitFor(() => expect(screen.getByText("isGuest: true")).toBeInTheDocument());
  });

  it("logout을 호출하면 게스트 상태도 함께 해제된다", async () => {
    apiFetch.mockImplementation(async (path) => {
      if (path === "/auth/me") {
        const { ApiError } = await vi.importActual("../api/client");
        throw new ApiError(401, "unauthorized");
      }
      if (path === "/auth/logout") return null;
      throw new Error(`unexpected call: ${path}`);
    });

    renderProbe();
    const user = userEvent.setup();

    await waitFor(() => expect(screen.getByText("isGuest: false")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "게스트로 둘러보기" }));
    expect(screen.getByText("isGuest: true")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "로그아웃" }));

    await waitFor(() => expect(screen.getByText("isGuest: false")).toBeInTheDocument());
  });
});
