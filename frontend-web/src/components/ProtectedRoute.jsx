import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute() {
  const { user, loading, isGuest } = useAuth();
  const location = useLocation();

  if (loading) {
    return <p>불러오는 중...</p>;
  }

  // 게스트 모드는 로그인 없이 피드/기사 상세를 둘러보기 위한 것이므로 여기서는
  // 통과시킨다 — 로그인이 실제로 필요한 화면(설정 등)은 각 페이지가 isGuest를
  // 보고 개별적으로 안내한다.
  if (!user && !isGuest) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}
