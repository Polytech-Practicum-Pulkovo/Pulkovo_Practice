import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { fullName, initials, ROLE_LABELS } from "../utils/role";
import Modal from "./Modal";

const NAV_BY_ROLE = {
  employee: [
    { to: "/app/courses", label: "Мои курсы" },
    { to: "/app/notifications", label: "Уведомления" },
  ],
  specialist: [
    { to: "/app/questions", label: "Банк вопросов" },
    { to: "/app/results", label: "Результаты обучения" },
  ],
  admin: [{ to: "/app/admin/courses", label: "Управление курсами" }],
};

export default function Layout() {
  const { employee, role, logout } = useAuth();
  const navigate = useNavigate();
  const [confirmingLogout, setConfirmingLogout] = useState(false);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const navItems = [{ to: "/app/profile", label: "Личный кабинет" }, ...(NAV_BY_ROLE[role] || [])];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          Учебный центр
          <br />
          «Взлётная полоса»
        </div>
        <div className="sidebar-user">
          <div className="avatar">{initials(employee)}</div>
          <div>
            <div className="name">{fullName(employee)}</div>
            <div className="email">{employee?.email}</div>
            <div className="position">{ROLE_LABELS[role]}</div>
          </div>
        </div>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "active" : "")}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button onClick={() => setConfirmingLogout(true)}>← Выйти</button>
        </div>
      </aside>
      <div className="main-area">
        <div className="topbar" />
        <div className="content">
          <Outlet />
        </div>
        <div className="page-footer">© 2027 Учебный центр «Взлётная полоса»</div>
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
