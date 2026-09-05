"use client";

import { useEffect, useRef, useState, type ChangeEvent } from "react";
import type { AuthenticatedRequest } from "../../lib/catalog-api";
import {
  completeAttachment,
  createAttachmentDownload,
  listAttachments,
  reserveAttachment,
  uploadReservedFile,
  type RequestAttachment,
} from "../../lib/attachment-api";

const button = "rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50";

function humanSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function RequestAttachments({ requestId, request }: {
  requestId: number;
  request: AuthenticatedRequest;
}) {
  const requestRef = useRef(request);
  useEffect(() => { requestRef.current = request; }, [request]);
  const [items, setItems] = useState<RequestAttachment[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let cancelled = false;
    requestRef.current((token) => listAttachments(token, requestId))
      .then((rows) => { if (!cancelled) setItems(rows); })
      .catch((cause) => { if (!cancelled) setError(cause instanceof Error ? cause.message : "Could not load attachments."); });
    return () => { cancelled = true; };
  }, [requestId, revision]);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await requestRef.current(async (token) => {
        const reservation = await reserveAttachment(token, requestId, file, "REQUESTER_VISIBLE");
        await uploadReservedFile(reservation, file);
        await completeAttachment(token, requestId, reservation.attachment_id);
      });
      setNotice("Attachment uploaded.");
      setRevision((value) => value + 1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function download(item: RequestAttachment) {
    setError(""); setNotice("");
    try {
      const result = await requestRef.current((token) => createAttachmentDownload(token, requestId, item.id));
      window.location.assign(result.download_url);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not create download link.");
    }
  }

  return <section className="rounded-2xl border border-slate-200 bg-white p-5 md:p-7" aria-label="Request attachments">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h3 className="font-semibold text-slate-900">Attachments</h3><p className="mt-1 text-sm text-slate-500">PDF, Word, Excel, PNG, JPG or text up to 10 MB.</p></div>
      <label className={`${button} cursor-pointer`}>
        {busy ? "Uploading..." : "Add attachment"}
        <input className="sr-only" type="file" disabled={busy} onChange={(event) => void upload(event)}
          accept="application/pdf,.docx,.xlsx,image/jpeg,image/png,text/plain" />
      </label>
    </div>
    {error ? <p role="alert" className="mt-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p> : null}
    {notice ? <p role="status" className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p> : null}
    <ul className="mt-4 divide-y divide-slate-100">
      {items.filter((item) => item.status === "READY").map((item) => <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
        <div className="min-w-0"><p className="truncate text-sm font-medium text-slate-800">{item.original_filename}</p><p className="text-xs text-slate-500">{humanSize(item.size_bytes)} / {item.uploader_name}</p></div>
        <button type="button" className={button} onClick={() => void download(item)}>Download</button>
      </li>)}
      {items.filter((item) => item.status === "READY").length === 0 ? <li className="py-4 text-sm text-slate-500">No completed attachments yet.</li> : null}
    </ul>
  </section>;
}
