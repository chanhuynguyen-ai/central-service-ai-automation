import { apiRequest } from "./api";

export type CommentVisibility = "REQUESTER_VISIBLE" | "INTERNAL";
export type ActivityPermissions = { can_comment: boolean; can_read_internal: boolean; can_write_internal: boolean };
export type Page<T> = { items: T[]; next_before_id: number | null };
export type RequestComment = {
  id: number; request_id: number; author_user_id: number; author_name: string;
  body: string; visibility: CommentVisibility; created_at: string;
};
export type RequestEvent = {
  id: number; request_id: number; actor_id: number | null; actor_name: string | null;
  event_type: string; visibility: CommentVisibility; payload: Record<string, number | boolean | string>;
  created_at: string;
};
export type AuditEvent = {
  id: number; actor_id: number | null; actor_name: string | null; request_id: number | null;
  event_type: string; resource_type: string | null; resource_id: string | null;
  correlation_id: string | null; details: Record<string, number | boolean | string>; created_at: string;
};
const cursorQuery = (beforeId?: number | null) => `limit=30${beforeId == null ? "" : `&before_id=${beforeId}`}`;
export const getActivityPermissions = (token: string, id: number) =>
  apiRequest<ActivityPermissions>(`/activity/requests/${id}/permissions`, {}, token);
export const getRequestTimeline = (token: string, id: number, beforeId?: number | null) =>
  apiRequest<Page<RequestEvent>>(`/activity/requests/${id}/timeline?${cursorQuery(beforeId)}`, {}, token);
export const getRequestComments = (token: string, id: number, visibility: CommentVisibility, beforeId?: number | null) =>
  apiRequest<Page<RequestComment>>(`/activity/requests/${id}/comments?visibility=${visibility}&${cursorQuery(beforeId)}`, {}, token);
export const postRequestComment = (token: string, id: number, body: string, visibility: CommentVisibility, clientToken: string) =>
  apiRequest<RequestComment>(`/activity/requests/${id}/comments`, {
    method: "POST", body: JSON.stringify({ body, visibility, client_token: clientToken }),
  }, token);
export const getAuditEvents = (token: string, filters: { eventType?: string; requestId?: number } = {}, beforeId?: number | null) => {
  const query = new URLSearchParams(cursorQuery(beforeId));
  if (filters.eventType) query.set("event_type", filters.eventType);
  if (filters.requestId !== undefined) query.set("request_id", String(filters.requestId));
  return apiRequest<Page<AuditEvent>>(`/audit/events?${query}`, {}, token);
};
