import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { NotificationsProvider, useNotifications } from "../notifications/NotificationsContext";
import { fullName, initials, ROLE_LABELS, ROLE_LEVEL } from "../utils/role";
import Modal from "./Modal";

// Каждый уровень добавляется к предыдущему: Специалист по ОТ видит разделы
// Работника + свои, Администратор — разделы Специалиста + свои.
const NAV_BY_LEVEL = {
  1: [
    { to: "/app/courses", label: "Мои курсы" },
    { to: "/app/notifications", label: "Уведомления", badge: "notifications" },
  ],
  2: [
    { to: "/app/questions", label: "Банк вопросов" },
    { to: "/app/results", label: "Результаты обучения" },
  ],
  3: [{ to: "/app/admin/courses", label: "Управление курсами" }],
};

function navItemsForRole(role) {
  const level = ROLE_LEVEL[role] ?? 1;
  return Object.keys(NAV_BY_LEVEL)
    .map(Number)
    .filter((itemLevel) => itemLevel <= level)
    .sort((a, b) => a - b)
    .flatMap((itemLevel) => NAV_BY_LEVEL[itemLevel]);
}

export default function Layout() {
  return (
    <NotificationsProvider>
      <LayoutInner />
    </NotificationsProvider>
  );
}

function LayoutInner() {
  const { employee, role, logout } = useAuth();
  const { unreadCount } = useNotifications();
  const navigate = useNavigate();
  const [confirmingLogout, setConfirmingLogout] = useState(false);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const navItems = [{ to: "/app/profile", label: "Личный кабинет" }, ...navItemsForRole(role)];

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
              {item.badge === "notifications" && unreadCount > 0 && <span className="nav-badge" />}
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
