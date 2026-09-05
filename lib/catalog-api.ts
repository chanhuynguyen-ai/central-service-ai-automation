import { apiRequest } from "./api";

export type FieldType = "text" | "textarea" | "number" | "currency" | "date" | "date_range"
  | "boolean" | "select" | "multi_select" | "user_picker" | "department_picker" | "attachment" | "url";
export type FormValue = string | number | boolean | null | string[] | { start: string; end: string };
export type FormData = Record<string, FormValue>;
export type FormField = {
  key: string; type: FieldType; label: string; required: boolean;
  helper_text?: string | null; placeholder?: string | null;
  options: { value: string; label: string }[];
};
export type FormSchema = { sections: { title: string; description?: string | null; fields: FormField[] }[] };
export type CatalogVersion = {
  id: number; request_type_id: number; version: number; title: string;
  description: string | null; form_schema: FormSchema; status: string;
};
export type CatalogEntry = {
  id: number; code: string; category: string; published_version: CatalogVersion;
};
export type FieldIssue = { field: string; code: string; message: string };
export type DraftValidation = { valid: boolean; errors: FieldIssue[]; missing_fields: string[] };
export type RequestDraft = {
  id: number; reference: string; title: string; description: string; status: "draft" | "changes_requested";
  request_type_version_id: number; revision: number; form_data: FormData;
  updated_at: string; request_type_version: CatalogVersion; validation: DraftValidation;
};
export type DraftValues = { title: string; description: string; form_data: FormData };
export type DraftLookups = { users: { id: number; name: string }[]; departments: { id: number; name: string }[] };
export type AuthenticatedRequest = <T>(operation: (accessToken: string) => Promise<T>) => Promise<T>;

export const listCatalog = (token: string) => apiRequest<CatalogEntry[]>("/catalog/request-types", {}, token);
export const listDrafts = (token: string, offset = 0) =>
  apiRequest<{ items: RequestDraft[]; total: number }>(`/requests/drafts?limit=50&offset=${offset}`, {}, token);
export const getDraft = (token: string, id: number) => apiRequest<RequestDraft>(`/requests/drafts/${id}`, {}, token);
export const getDraftLookups = (token: string) => apiRequest<DraftLookups>("/requests/drafts/lookups", {}, token);
export const createDraft = (token: string, versionId: number, values: DraftValues) =>
  apiRequest<RequestDraft>("/requests/drafts", {
    method: "POST", body: JSON.stringify({ ...values, request_type_version_id: versionId }),
  }, token);
export const updateDraft = (token: string, draft: RequestDraft, values: DraftValues) =>
  apiRequest<RequestDraft>(`/requests/drafts/${draft.id}`, {
    method: "PUT", body: JSON.stringify({ ...values, revision: draft.revision }),
  }, token);
