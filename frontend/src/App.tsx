import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import PlayerRealtimePanels from "./components/PlayerRealtimePanels";
import AdminPage from "./pages/AdminPage";
import AuthPage from "./pages/AuthPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import GamePage from "./pages/GamePage";
import MarketPage from "./pages/MarketPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import { useAuthStore } from "./store/authStore";
import "./styles.css";

export default function App() {
  const location = useLocation();
  const { accessToken, role, identifier, logout } = useAuthStore();

  const isAuthPage = location.pathname.startsWith("/auth");
  const isAdminPage = location.pathname.startsWith("/admin");
  const showRealtimePanels = Boolean(accessToken && role === "player" && !isAuthPage && !isAdminPage);

  return (
    <main className="layout">
      <header className="topbar hero">
        <div>
          <p className="eyebrow">Monopoly SDS</p>
          <h1>Альфа-подготовка</h1>
          <p className="subline">Общая игровая доска, экономика наград и живой цикл тестирования</p>
        </div>
        <nav className="nav">
          <Link to="/auth">Вход</Link>
          <Link to="/game">Игра</Link>
          <Link to="/market">Торговля</Link>
          <Link to="/admin">Админка</Link>
        </nav>
        <div className="session">
          <span className="session-id">{identifier || "Гость"}</span>
          {accessToken && (
            <button type="button" className="secondary" onClick={logout}>
              Выйти
            </button>
          )}
        </div>
      </header>

      <div className={showRealtimePanels ? "app-shell with-sidebars" : "app-shell"}>
        {showRealtimePanels && accessToken ? <PlayerRealtimePanels token={accessToken} /> : null}

        <div className="app-main">
          <Routes>
            <Route path="/auth" element={<AuthPage />} />
            <Route path="/auth/forgot" element={<ForgotPasswordPage />} />
            <Route path="/auth/reset" element={<ResetPasswordPage />} />
            <Route path="/game" element={accessToken ? <GamePage /> : <Navigate to="/auth" replace />} />
            <Route path="/market" element={accessToken ? <MarketPage /> : <Navigate to="/auth" replace />} />
            <Route
              path="/admin"
              element={accessToken && role === "admin" ? <AdminPage /> : <Navigate to="/auth" replace />}
            />
            <Route path="*" element={<Navigate to={accessToken ? "/game" : "/auth"} replace />} />
          </Routes>
        </div>
      </div>
    </main>
  );
}
