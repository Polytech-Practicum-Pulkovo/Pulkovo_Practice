import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { changePassword } from "../../api/personalData";
import { useAuth } from "../../auth/AuthContext";
import Modal from "../../components/Modal";

function PasswordField({ label, value, onChange }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="field">
      <label>{label}</label>
      <div className="row" style={{ position: "relative" }}>
        <input
          type={visible ? "text" : "password"}
          value={value}
          onChange={onChange}
          required
          style={{ flex: 1 }}
        />
        <button
          type="button"
          className="link-button"
          style={{ position: "absolute", right: 10 }}
          onClick={() => setVisible((v) => !v)}
        >
          {visible ? "🙈" : "👁"}
        </button>
      </div>
    </div>
  );
}

export default function ChangePasswordPage() {
  const { employee } = useAuth();
  const navigate = useNavigate();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null); // "success" | "error" | null
  const [errorReason, setErrorReason] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setResult(null);

    if (newPassword !== confirmPassword) {
      setError("Новый пароль и подтверждение не совпадают, проверьте ввод");
      return;
    }

    setLoading(true);
    try {
      await changePassword(employee.id_employee, oldPassword, newPassword);
      setResult("success");
    } catch (err) {
      setErrorReason(err.message || "Неизвестная ошибка");
      setResult("error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1>Смена пароля</h1>
      <form className="card" style={{ maxWidth: 480 }} onSubmit={handleSubmit}>
        <PasswordField label="Введите старый пароль" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} />
        <PasswordField label="Введите новый пароль" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
        <PasswordField
          label="Повторите пароль"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
        />
        {error && <div className="alert alert-error">⚠ {error}</div>}
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Сохраняем…" : "Сменить пароль"}
        </button>
      </form>

      {result === "success" && (
        <Modal>
          <h3>Пароль успешно изменён!</h3>
          <button className="btn btn-primary mt-16" onClick={() => navigate("/app/profile")}>
            Вернуться в личный кабинет
          </button>
        </Modal>
      )}

      {result === "error" && (
        <Modal onClose={() => setResult(null)}>
          <h3 style={{ color: "var(--red-dark)" }}>Не удалось изменить пароль</h3>
          <p>{errorReason}</p>
          <button className="btn btn-primary" onClick={() => setResult(null)}>
            Повторить попытку
          </button>
        </Modal>
      )}
    </div>
  );
}
