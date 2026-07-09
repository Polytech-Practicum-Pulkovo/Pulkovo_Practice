import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import Modal from "../../components/Modal";
import { ROLE_LABELS, fullName } from "../../utils/role";

export default function ProfilePage() {
  const { employee, role, logout } = useAuth();
  const navigate = useNavigate();
  const [confirmingLogout, setConfirmingLogout] = useState(false);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div>
      <div className="row-between mb-16">
        <h1>Личный кабинет</h1>
        <div className="row">
          <Link className="btn btn-primary" to="/app/profile/change-password">
            Сменить пароль
          </Link>
          <button className="btn btn-danger" onClick={() => setConfirmingLogout(true)}>
            Выйти из аккаунта
          </button>
        </div>
      </div>

      <div className="card" style={{ maxWidth: 480 }}>
        <div className="field-static">
          <label>ФИО</label>
          <div className="value">{fullName(employee)}</div>
        </div>
        <div className="field-static">
          <label>Email</label>
          <div className="value">{employee?.email || "—"}</div>
        </div>
        <div className="field-static">
          <label>Табельный номер</label>
          <div className="value">{employee?.employee_number || "—"}</div>
        </div>
        <div className="field-static">
          <label>Роль</label>
          <div className="value">{employee?.role || ROLE_LABELS[role]}</div>
        </div>
        <div className="field-static">
          <label>Должность</label>
          <div className="value">{employee?.position || "—"}</div>
        </div>
        <div className="field-static">
          <label>Подразделение</label>
          <div className="value">{employee?.department || "—"}</div>
        </div>
      </div>

      {confirmingLogout && (
        <Modal onClose={() => setConfirmingLogout(false)}>
          <h3>Вы действительно хотите выйти?</h3>
          <div className="row mt-16">
            <button className="btn btn-secondary" onClick={() => setConfirmingLogout(false)}>
              Назад
            </button>
            <button className="btn btn-danger" onClick={handleLogout}>
              Выйти из аккаунта
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
