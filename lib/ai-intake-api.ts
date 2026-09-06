import { apiRequest } from "./api";
import type { FormData } from "./catalog-api";

export type IntakeAlternative = {
  request_type_code: string;
  title: string;
  confidence: number;
};

export type IntakeClarification = {
  field: string;
  prompt: string;
};

export type IntakeDraftSuggestion = {
  request_type_code: string;
  title: string;
  category: string;
  request_type_version_id: number;
  confidence: number;
  alternatives: IntakeAlternative[];
  needs_human_confirmation: boolean;
  provider: string;
  model: string;
  extracted_fields: FormData;
  missing_required_fields: string[];
  clarifications: IntakeClarification[];
  field_issues: string[];
};

export const suggestIntakeDraft = (token: string, text: string, requestTypeCode?: string) =>
  apiRequest<IntakeDraftSuggestion>("/ai/intake/draft", {
    method: "POST",
    body: JSON.stringify({ text, request_type_code: requestTypeCode ?? null }),
  }, token);
