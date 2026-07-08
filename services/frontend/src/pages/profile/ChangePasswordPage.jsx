import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { changePassword } from "../../api/personalData";
import { useAuth } from "../../auth/AuthContext";
import Modal from "../../components/Modal";

export default function ChangePasswordPage() {
  const { employee } = useAuth();
  const navigate = useNavigate();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null); // "success" | "error" | null
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (newPassword !== confirmPassword) {
      setError("Пароли не совпадают, проверьте ввод");
      return;
    }

    setLoading(true);
    try {
      await changePassword(employee.id_employee, oldPassword, newPassword);
      setResult("success");
    } catch {
      setResult("error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1>Смена пароля</h1>
      <form className="card" style={{ maxWidth: 480 }} onSubmit={handleSubmit}>
        <div className="field">
          <label>Введите старый пароль</label>
          <input type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} required />
        </div>
        <div className="field">
          <label>Введите новый пароль</label>
          <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
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
          <p>Повторите попытку заново или обратитесь к администратору</p>
          <button className="btn btn-primary" onClick={() => setResult(null)}>
            Повторить попытку
          </button>
        </Modal>
      )}
    </div>
  );
}
