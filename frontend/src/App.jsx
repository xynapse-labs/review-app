import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import DrawingDetail from "./pages/DrawingDetail";
import NotificationBell from "./components/NotificationBell";

function TopBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="topbar">
      <h1 onClick={() => navigate("/")} style={{ cursor: "pointer" }}>
        Digital Design Review
      </h1>
      {user && (
        <div className="topbar-right">
          <NotificationBell />
          <div className="user-chip">
            <span>{user.display_name}</span>
            <span className="role">{user.role}</span>
          </div>
          <button onClick={handleLogout}>Log out</button>
        </div>
      )}
    </div>
  );
}

function RequireAuth({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return null;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppRoutes() {
  return (
    <div className="app-shell">
      <TopBar />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/drawings/:id"
          element={
            <RequireAuth>
              <DrawingDetail />
            </RequireAuth>
          }
        />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
