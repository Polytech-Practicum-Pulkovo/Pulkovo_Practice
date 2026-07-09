import { useState } from "react";
import { useNotifications } from "../../notifications/NotificationsContext";
import { formatDate } from "../../utils/format";

export default function NotificationsPage() {
  const { notifications, markAsRead, remove } = useNotifications();
  const [openId, setOpenId] = useState(null);

  async function handleOpen(notification) {
    setOpenId(notification.id === openId ? null : notification.id);
    if (!notification.is_viewed) {
      await markAsRead(notification.id);
    }
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
              {n.is_viewed && <span className="badge badge-gray">Прочитано ✓</span>}
              <button className="btn btn-danger" onClick={() => remove(n.id)}>
                Удалить
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
