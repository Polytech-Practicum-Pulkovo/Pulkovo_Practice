import { API } from "./config";
import { get, put, del } from "./client";

const base = API.notifications;

export function listNotifications(employeeId) {
  return get(base, "/notifications", { employee_id: employeeId });
}

export function markRead(notificationId) {
  return put(base, `/notifications/${notificationId}/read`);
}

export function removeNotification(notificationId) {
  return del(base, `/notifications/${notificationId}`);
}
