export const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";
export const apiConfigured = apiBaseUrl.length > 0;

export type ApiUser = {
  id: number;
  email: string;
  full_name: string;
  department: string;
  role: string;
};

export type ApiServiceRequest = {
  id: number;
  reference: string;
  title: string;
  description: string;
  category: string;
  priority: string;
  status: string;
  department: string;
  ai_confidence: number | null;
  submitted_at: string;
  requester: ApiUser;
};

async function apiRequest<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: "Request failed" })) as {
      detail?: string;
    };
    throw new Error(detail.detail ?? `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string) {
  return apiRequest<{ access_token: string; user: ApiUser }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function listRequests(token: string) {
  return apiRequest<{ items: ApiServiceRequest[]; total: number }>("/requests", {}, token);
}

export async function createRequest(
  token: string,
  payload: { title: string; description: string; category?: string; priority?: string },
) {
  return apiRequest<ApiServiceRequest>("/requests", {
    method: "POST",
    body: JSON.stringify(payload),
  }, token);
}

export async function askPolicyAssistant(
  token: string,
  question: string,
  requestReference?: string,
) {
  return apiRequest<{
    answer: string;
    citations: { title: string; version: string; score: number }[];
    grounded: boolean;
  }>("/assistant/chat", {
    method: "POST",
    body: JSON.stringify({ question, request_reference: requestReference }),
  }, token);
}

export async function getAnalytics(token: string) {
  return apiRequest<{
    total_requests: number;
    open_requests: number;
    pending_approvals: number;
    completed_requests: number;
    sla_compliance_rate: number;
    automation_success_rate: number;
    ai_triage_coverage: number;
  }>("/analytics/summary", {}, token);
}
