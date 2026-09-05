import { apiRequest } from "./api";
import type { AuthenticatedRequest } from "./catalog-api";

export type WorkStatus = "QUEUED" | "ASSIGNED" | "IN_PROGRESS" | "WAITING_REQUESTER" | "RESOLVED" | "CLOSED";
export type WorkScope = "team" | "unassigned" | "mine";
export type WorkAction = "assign" | "start" | "wait" | "resume" | "resolve" | "close";

export type ServiceWorkItem = {
  id: number;
  request_id: number;
  reference: string;
  title: string;
  requester_name: string;
  service_team_id: number;
  service_team_name: string;
  assignee_user_id: number | null;
  assignee_name: string | null;
  status: WorkStatus;
  version: number;
  resolution_summary: string | null;
  queued_at: string;
  assigned_at: string | null;
  started_at: string | null;
  waiting_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  due_at: string | null;
  can_manage: boolean;
};

export type WorkItemPage = { items: ServiceWorkItem[]; total: number };

export const listWorkItems = (
  token: string,
  scope: WorkScope = "team",
  status?: WorkStatus,
  offset = 0,
) => {
  const query = new URLSearchParams({ scope, limit: "50", offset: String(offset) });
  if (status) query.set("status", status);
  return apiRequest<WorkItemPage>(`/fulfillment/work-items?${query.toString()}`, {}, token);
};

export const actOnWorkItem = (
  token: string,
  item: Pick<ServiceWorkItem, "id" | "version">,
  action: WorkAction,
  options: { assigneeUserId?: number; note?: string } = {},
) => apiRequest<ServiceWorkItem>(`/fulfillment/work-items/${item.id}/actions`, {
  method: "POST",
  body: JSON.stringify({
    action,
    version: item.version,
    assignee_user_id: options.assigneeUserId,
    note: options.note,
  }),
}, token);

export type FulfillmentRequest = AuthenticatedRequest;
