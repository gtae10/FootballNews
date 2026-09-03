import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function OnboardingGate() {
  const { user } = useAuth();

  if (user && !user.onboarded) {
    return <Navigate to="/onboarding" replace />;
  }

  return <Outlet />;
}
