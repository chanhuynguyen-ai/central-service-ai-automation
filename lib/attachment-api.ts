import { apiRequest } from "./api";

export type RequestAttachment = {
  id: number;
  request_id: number;
  uploaded_by: number;
  uploader_name: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  sha256: string | null;
  visibility: "REQUESTER_VISIBLE" | "INTERNAL";
  status: "PENDING" | "READY" | "QUARANTINED" | "DELETED";
  created_at: string;
  ready_at: string | null;
};

type PresignResult = {
  attachment_id: number;
  upload_url: string;
  upload_method: "PUT";
  required_headers: Record<string, string>;
  expires_in_seconds: number;
};

export const listAttachments = (token: string, requestId: number) =>
  apiRequest<RequestAttachment[]>(`/requests/${requestId}/attachments`, {}, token);

export const reserveAttachment = (
  token: string,
  requestId: number,
  file: File,
  visibility: "REQUESTER_VISIBLE" | "INTERNAL",
) => apiRequest<PresignResult>(`/requests/${requestId}/attachments/presign`, {
  method: "POST",
  body: JSON.stringify({
    filename: file.name,
    mime_type: file.type || "application/octet-stream",
    size_bytes: file.size,
    visibility,
  }),
}, token);

export async function uploadReservedFile(reservation: PresignResult, file: File) {
  const response = await fetch(reservation.upload_url, {
    method: reservation.upload_method,
    headers: reservation.required_headers,
    body: file,
  });
  if (!response.ok) throw new Error("Object storage rejected the upload.");
}

export const completeAttachment = (token: string, requestId: number, attachmentId: number) =>
  apiRequest<RequestAttachment>(`/requests/${requestId}/attachments/${attachmentId}/complete`, {
    method: "POST", body: JSON.stringify({}),
  }, token);

export const createAttachmentDownload = (token: string, requestId: number, attachmentId: number) =>
  apiRequest<{ download_url: string; expires_in_seconds: number }>(
    `/requests/${requestId}/attachments/${attachmentId}/download`,
    { method: "POST" },
    token,
  );
