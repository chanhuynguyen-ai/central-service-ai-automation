import { apiRequest } from "@/lib/api";

export type AdminRequestType = {
  id: number;
  code: string;
  category: string;
  owner_service_team_id: number | null;
  is_active: boolean;
  created_at: string;
};

export type AdminRequestTypeVersion = {
  id: number;
  request_type_id: number;
  version: number;
  title: string;
  description: string | null;
  form_schema: Record<string, unknown>;
  validation_schema: Record<string, unknown> | null;
  sla_config: Record<string, unknown> | null;
  attachment_config: Record<string, unknown> | null;
  status: "DRAFT" | "PUBLISHED" | "RETIRED";
  published_at: string | null;
  created_by: number | null;
  created_at: string;
};

export type RequestTypeVersionInput = {
  title: string;
  description?: string | null;
  form_schema: Record<string, unknown>;
  validation_schema?: Record<string, unknown> | null;
  sla_config?: Record<string, unknown> | null;
  attachment_config?: Record<string, unknown> | null;
};

export function listAdminRequestTypes(token: string) {
  return apiRequest<AdminRequestType[]>("/catalog/admin/request-types", {}, token);
}

export function createAdminRequestType(
  token: string,
  payload: { code: string; category: string; owner_service_team_id?: number | null; is_active?: boolean },
) {
  return apiRequest<AdminRequestType>("/catalog/request-types", {
    method: "POST",
    body: JSON.stringify(payload),
  }, token);
}

export function updateAdminRequestType(
  token: string,
  requestTypeId: number,
  payload: { category?: string; owner_service_team_id?: number | null; is_active?: boolean },
) {
  return apiRequest<AdminRequestType>(`/catalog/request-types/${requestTypeId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }, token);
}

export function listAdminRequestTypeVersions(token: string, requestTypeId: number) {
  return apiRequest<AdminRequestTypeVersion[]>(
    `/catalog/request-types/${requestTypeId}/versions`,
    {},
    token,
  );
}

export function createAdminRequestTypeVersion(
  token: string,
  requestTypeId: number,
  payload: RequestTypeVersionInput,
) {
  return apiRequest<AdminRequestTypeVersion>(`/catalog/request-types/${requestTypeId}/versions`, {
    method: "POST",
    body: JSON.stringify(payload),
  }, token);
}

export function updateAdminRequestTypeVersion(
  token: string,
  requestTypeId: number,
  version: number,
  payload: Partial<RequestTypeVersionInput>,
) {
  return apiRequest<AdminRequestTypeVersion>(
    `/catalog/request-types/${requestTypeId}/versions/${version}`,
    { method: "PATCH", body: JSON.stringify(payload) },
    token,
  );
}

export function publishAdminRequestTypeVersion(
  token: string,
  requestTypeId: number,
  version: number,
) {
  return apiRequest<AdminRequestTypeVersion>(
    `/catalog/request-types/${requestTypeId}/versions/${version}/publish`,
    { method: "POST" },
    token,
  );
}
