import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch, ApiError } from "../api/client";

const AuthContext = createContext(null);

// 게스트 모드 여부를 세션에 남겨, 새로고침해도 로그인 화면으로 튕기지 않게 한다.
// 로그인 여부(user)와는 별개 상태다 — 게스트는 user가 없어도 로그인하지 않은 것과
// 구분되어야 한다(ProtectedRoute가 이 값을 함께 확인한다).
const GUEST_STORAGE_KEY = "rf-guest-mode";

function readGuestFlag() {
  try {
    return sessionStorage.getItem(GUEST_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function writeGuestFlag(value) {
  try {
    if (value) {
      sessionStorage.setItem(GUEST_STORAGE_KEY, "true");
    } else {
      sessionStorage.removeItem(GUEST_STORAGE_KEY);
    }
  } catch {
    // sessionStorage를 쓸 수 없는 환경(프라이빗 모드 등)이면 조용히 무시한다 —
    // 게스트 모드 자체는 메모리 상태로 여전히 동작하고, 새로고침 시에만 풀린다.
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isGuest, setIsGuest] = useState(readGuestFlag);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const me = await apiFetch("/auth/me");
      setUser(me);
      setIsGuest(false);
      writeGuestFlag(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setUser(null);
      } else {
        throw err;
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const loginAsGuest = useCallback(() => {
    setUser(null);
    setIsGuest(true);
    writeGuestFlag(true);
  }, []);

  const logout = useCallback(async () => {
    await apiFetch("/auth/logout", { method: "POST" });
    setUser(null);
    setIsGuest(false);
    writeGuestFlag(false);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, isGuest, refresh, logout, loginAsGuest }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth는 AuthProvider 내부에서만 사용할 수 있습니다.");
  }
  return context;
}
