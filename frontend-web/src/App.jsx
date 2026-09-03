import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import OnboardingGate from "./components/OnboardingGate";
import LoginPage from "./pages/LoginPage";
import OnboardingPage from "./pages/OnboardingPage";
import FeedPage from "./pages/FeedPage";
import ArticleDetailPage from "./pages/ArticleDetailPage";
import SettingsPage from "./pages/SettingsPage";

function App() {
  return (
    <div className="rf-app">
      <div className="rf-page">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/onboarding" element={<OnboardingPage />} />
            <Route element={<OnboardingGate />}>
              <Route path="/feed" element={<FeedPage />} />
              <Route path="/articles/:id" element={<ArticleDetailPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Route>
          <Route path="/" element={<Navigate to="/feed" replace />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
