import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login as apiLogin } from "../../api/personalData";
import { useAuth } from "../../auth/AuthContext";
import { roleFromPosition } from "../../utils/role";

const HOME_BY_ROLE = {
  employee: "/app/courses",
  specialist: "/app/questions",
  admin: "/app/admin/courses",
};

export default function LoginPage() {
  const [employeeNumber, setEmployeeNumber] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const employee = await apiLogin(employeeNumber, password);
      login(employee);
      navigate(HOME_BY_ROLE[roleFromPosition(employee.position)] || "/app/profile");
    } catch {
      setError("Неверный табельный номер или пароль");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Вход в систему</h1>
        <p className="subtitle">Введите табельный номер и пароль</p>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Табельный номер</label>
            <input
              value={employeeNumber}
              onChange={(e) => setEmployeeNumber(e.target.value)}
              placeholder="В формате XXXXX"
              inputMode="numeric"
              required
            />
          </div>
          <div className="field">
            <label>Пароль</label>
            <div className="row" style={{ position: "relative" }}>
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Введите пароль"
                required
                style={{ flex: 1 }}
              />
              <button
                type="button"
                className="link-button"
                style={{ position: "absolute", right: 10 }}
                onClick={() => setShowPassword((v) => !v)}
              >
                {showPassword ? "🙈" : "👁"}
              </button>
            </div>
          </div>
          <div className="mb-16">
            <Link to="/forgot-password">Забыли пароль?</Link>
          </div>
          {error && <div className="alert alert-error">⚠ {error}</div>}
          <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
            {loading ? "Входим…" : "Войти"}
          </button>
        </form>
      </div>
    </div>
  );
}
