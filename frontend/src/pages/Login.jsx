import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [demoUsers, setDemoUsers] = useState([]);

  useEffect(() => {
    api.listUsers().then(setDemoUsers).catch(() => {});
  }, []);

  const DEMO_PASSWORDS = {
    alice: "alice123",
    priya: "priya123",
    raj: "raj123",
    tom: "tom123",
  };

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Login failed");
    }
  }

  async function quickLogin(u) {
    setError("");
    try {
      await login(u.username, DEMO_PASSWORDS[u.username] || "");
      navigate("/");
    } catch (err) {
      setError(err.message || "Login failed");
    }
  }

  return (
    <div className="login-wrap">
      <div className="card">
        <h2>Design Review Sign In</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <label>Username</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
          </div>
          <div className="form-row">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <div className="error-text">{error}</div>}
          <button type="submit" className="primary">
            Sign in
          </button>
        </form>

        {demoUsers.length > 0 && (
          <>
            <p className="section-title" style={{ marginTop: 20 }}>
              Demo users (click to sign in)
            </p>
            <div className="quick-login-grid">
              {demoUsers.map((u) => (
                <button key={u.id} onClick={() => quickLogin(u)}>
                  <div style={{ fontWeight: 600 }}>{u.display_name}</div>
                  <div className="muted">{u.role}</div>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
