import { useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../../api/personalData";

export default function ForgotPasswordPage() {
  const [employeeNumber, setEmployeeNumber] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await forgotPassword(employeeNumber);
    } finally {
      setLoading(false);
      setSent(true);
    }
  }

  if (sent) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1>Восстановление доступа</h1>
          <p className="subtitle">
            Если сотрудник с таким табельным номером существует, на почту, привязанную к учётной
            записи, отправлено письмо со ссылкой на смену пароля.
          </p>
          <Link className="btn btn-primary btn-block" to="/login">
            Вернуться ко входу в систему
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Восстановление доступа</h1>
        <p className="subtitle">Введите табельный номер</p>
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
          <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
            {loading ? "Отправляем…" : "Подтвердить"}
          </button>
        </form>
      </div>
    </div>
  );
}
