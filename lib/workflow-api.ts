import { apiRequest } from "./api";
import type { FormData, FormSchema } from "./catalog-api";

export type ApprovalTask = {
  id: number; approver_user_id: number; approver_name: string; version: number;
  status: string; can_decide: boolean;
  decision: { decision: string; comment: string; created_at: string } | null;
};
export type WorkflowAttempt = {
  id: number; attempt: number; status: string; started_at: string; completed_at: string | null;
  snapshot: { title: string; description: string; form_data: FormData; form_schema: FormSchema;
    form_version: number; request_type_code: string; workflow: { version: number } };
  steps: { id: number; name: string; step_order: number; status: string; tasks: ApprovalTask[] }[];
};
export type Submission = {
  id: number; reference: string; title: string; status: string; approval_state: string;
  fulfillment_state: string; revision: number; attempt: number; requester_id: number;
  requester_name: string; requester_department: string; submitted_at: string;
  due_at: string | null; approved_at: string | null;
};
export type SubmissionDetail = Submission & { attempts: WorkflowAttempt[] };
export type InboxTask = {
  id: number; version: number; status: string; step_name: string; request_id: number;
  reference: string; title: string; attempt: number; requester_name: string;
};
export type Decision = "approve" | "reject" | "request_changes";

export const submitDraft = (token: string, id: number, revision: number) =>
  apiRequest<SubmissionDetail>(`/workflows/requests/${id}/submit`, {
    method: "POST", body: JSON.stringify({ revision }),
  }, token);
export const listSubmissions = (token: string, offset = 0) =>
  apiRequest<{ items: Submission[]; total: number }>(`/workflows/requests?limit=50&offset=${offset}`, {}, token);
export const getSubmission = (token: string, id: number) =>
  apiRequest<SubmissionDetail>(`/workflows/requests/${id}`, {}, token);
export const listApprovalTasks = (token: string, status: "pending" | "history" = "pending", offset = 0) =>
  apiRequest<{ items: InboxTask[]; total: number }>(`/workflows/approval-tasks?status=${status}&limit=50&offset=${offset}`, {}, token);
export const decideApprovalTask = (token: string, task: ApprovalTask, decision: Decision, comment: string) =>
  apiRequest<SubmissionDetail>(`/workflows/approval-tasks/${task.id}/decisions`, {
    method: "POST", body: JSON.stringify({ version: task.version, decision, comment }),
  }, token);
