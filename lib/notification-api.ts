import { apiRequest } from "./api";

export type InAppNotification = {
  id: number;
  request_id: number | null;
  kind: string;
  subject: string;
  body: string;
  status: string;
  created_at: string;
  read_at: string | null;
};

export type NotificationPage = {
  items: InAppNotification[];
  total: number;
  unread: number;
};

export const listNotifications = (token: string, unreadOnly = false) =>
  apiRequest<NotificationPage>(`/notifications?unread_only=${unreadOnly ? "true" : "false"}`, {}, token);

export const markNotificationRead = (token: string, notificationId: number) =>
  apiRequest<InAppNotification>(`/notifications/${notificationId}/read`, { method: "POST" }, token);

export const markAllNotificationsRead = (token: string) =>
  apiRequest<{ updated: number }>("/notifications/read-all", { method: "POST" }, token);
