import { useEffect, useState } from "react";
import { listNotifications, markRead, removeNotification } from "../../api/notifications";
import { useAuth } from "../../auth/AuthContext";
import { formatDate } from "../../utils/format";

export default function NotificationsPage() {
  const { employee } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [openId, setOpenId] = useState(null);

  function reload() {
    return listNotifications(employee.id_employee).then(setNotifications);
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleOpen(notification) {
    setOpenId(notification.id === openId ? null : notification.id);
    if (!notification.is_viewed) {
      await markRead(notification.id);
      await reload();
    }
  }

  async function handleDelete(notificationId) {
    await removeNotification(notificationId);
    await reload();
  }

  return (
    <div>
      <h1>Уведомления</h1>
      <div className="panel">
        {notifications.length === 0 && <div className="empty-state">Уведомлений пока нет</div>}
        {notifications.map((n) => (
          <div
            key={n.id}
            className="row-between"
            style={{ padding: "14px 18px", borderBottom: "1px solid var(--border)" }}
          >
            <div style={{ cursor: "pointer", flex: 1 }} onClick={() => handleOpen(n)}>
              <div>
                {!n.is_viewed && "🔵 "}
                {n.notification_text}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{formatDate(n.date)}</div>
            </div>
            <div className="row">
              {!n.is_viewed ? (
                <>
                  <button className="btn btn-danger" onClick={() => handleDelete(n.id)}>
                    Удалить
                  </button>
                  <button className="btn btn-primary" onClick={() => handleOpen(n)}>
                    Отметить прочитанным
                  </button>
                </>
              ) : (
                <span className="badge badge-gray">Прочитано ✓</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
