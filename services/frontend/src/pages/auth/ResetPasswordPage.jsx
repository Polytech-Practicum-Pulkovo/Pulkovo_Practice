import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { resetPassword } from "../../api/personalData";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (password.length < 8 || password.length > 16) {
      setError("Длина пароля должна быть не менее 8 и не более 16 символов");
      return;
    }
    if (password !== confirmPassword) {
      setError("Пароли не совпадают, проверьте ввод");
      return;
    }

    setLoading(true);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch {
      setError("Ссылка недействительна или устарела");
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1>Пароль успешно изменён!</h1>
          <p className="subtitle">Войдите в систему с новым паролем.</p>
          <Link className="btn btn-primary btn-block" to="/login">
            Перейти ко входу
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Восстановление доступа</h1>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Введите новый пароль</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <div className="field">
            <label>Повторите пароль</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          {error && <div className="alert alert-error">⚠ {error}</div>}
          <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
            {loading ? "Сохраняем…" : "Установить пароль"}
          </button>
        </form>
      </div>
    </div>
  );
}
