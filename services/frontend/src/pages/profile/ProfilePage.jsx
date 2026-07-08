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
        <div className="field">
          <label>ФИО</label>
          <input readOnly value={fullName(employee)} />
        </div>
        <div className="field">
          <label>Email</label>
          <input readOnly value={employee?.email || ""} />
        </div>
        <div className="field">
          <label>Табельный номер</label>
          <input readOnly value={employee?.employee_number || ""} />
        </div>
        <div className="field">
          <label>Должность</label>
          <input readOnly value={employee?.position || ROLE_LABELS[role]} />
        </div>
        <div className="field">
          <label>Подразделение</label>
          <input readOnly value={employee?.department || ""} />
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
