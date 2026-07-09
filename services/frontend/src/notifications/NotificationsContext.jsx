import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { listNotifications, markRead, removeNotification } from "../api/notifications";
import { useAuth } from "../auth/AuthContext";

const NotificationsContext = createContext(null);

export function NotificationsProvider({ children }) {
  const { employee } = useAuth();
  const [notifications, setNotifications] = useState([]);

  const refresh = useCallback(() => {
    if (!employee?.id_employee) return Promise.resolve();
    return listNotifications(employee.id_employee).then(setNotifications);
  }, [employee?.id_employee]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const markAsRead = useCallback(
    async (notificationId) => {
      await markRead(notificationId);
      await refresh();
    },
    [refresh]
  );

  const remove = useCallback(
    async (notificationId) => {
      await removeNotification(notificationId);
      await refresh();
    },
    [refresh]
  );

  const unreadCount = notifications.filter((n) => !n.is_viewed).length;

  const value = useMemo(
    () => ({ notifications, unreadCount, refresh, markAsRead, remove }),
    [notifications, unreadCount, refresh, markAsRead, remove]
  );

  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}

export function useNotifications() {
  const ctx = useContext(NotificationsContext);
  if (!ctx) throw new Error("useNotifications must be used within NotificationsProvider");
  return ctx;
}
