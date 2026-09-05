"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import type { AuthenticatedRequest } from "../../lib/catalog-api";
import {
  getActivityPermissions, getRequestComments, getRequestTimeline, postRequestComment,
  type ActivityPermissions, type CommentVisibility, type Page, type RequestComment, type RequestEvent,
} from "../../lib/activity-api";

const button = "rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50";
const emptyPage = <T,>(): Page<T> => ({ items: [], next_before_id: null });
const errorText = (cause: unknown) => cause instanceof Error ? cause.message : "Activity could not be loaded.";
const eventLabels: Record<string, string> = {
  REQUEST_SUBMITTED: "Request submitted", WORKFLOW_STARTED: "Approval workflow started",
  APPROVAL_ASSIGNED: "Approval step assigned", APPROVAL_APPROVED: "Approval recorded",
  APPROVAL_REJECTED: "Request rejected", CHANGES_REQUESTED: "Changes requested",
  WORKFLOW_APPROVED: "Approval workflow completed", COMMENT_ADDED: "Public comment added",
  INTERNAL_NOTE_ADDED: "Internal note added",
};

export function CommentList({ items }: { items: RequestComment[] }) {
  return <ol className="space-y-3">{items.map((item) => <li key={item.id} className="rounded-xl border border-slate-200 p-4">
    <div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-semibold text-slate-800">{item.author_name}</p>
      <time className="text-xs text-slate-500" dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time></div>
    <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-slate-700">{item.body}</p>
  </li>)}</ol>;
}

export function ActivityTimeline({ items }: { items: RequestEvent[] }) {
  return <ol className="ml-2 space-y-5 border-l border-slate-200 pl-5">{items.map((item) => <li key={item.id} className="relative">
    <span aria-hidden="true" className="absolute -left-[25px] top-1.5 size-2 rounded-full bg-blue-600" />
    <p className="text-sm font-medium text-slate-800">{eventLabels[item.event_type] ?? "Recorded activity"}{item.visibility === "INTERNAL" ? <span className="ml-2 rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-900">Internal</span> : null}</p>
    <p className="mt-1 text-xs text-slate-500">{item.actor_name ?? "System"} / <time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time>{typeof item.payload.attempt === "number" ? ` / Attempt ${item.payload.attempt}` : ""}</p>
    {item.payload.backfilled === true ? <p className="mt-1 text-xs text-slate-500">Imported from an existing audit record; original recorded time retained.</p> : null}
  </li>)}</ol>;
}

export function RequestActivity({ requestId, request, revision }: {
  requestId: number; request: AuthenticatedRequest; revision: number;
}) {
  const requestRef = useRef(request);
  useEffect(() => { requestRef.current = request; }, [request]);
  const mountedRef = useRef(true);
  useEffect(() => { mountedRef.current = true; return () => { mountedRef.current = false; }; }, []);
  const [permissions, setPermissions] = useState<ActivityPermissions | null>(null);
  const [comments, setComments] = useState<Page<RequestComment>>(emptyPage);
  const [internal, setInternal] = useState<Page<RequestComment>>(emptyPage);
  const [timeline, setTimeline] = useState<Page<RequestEvent>>(emptyPage);
  const [visibility, setVisibility] = useState<CommentVisibility>("REQUESTER_VISIBLE");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [moreBusy, setMoreBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [refresh, setRefresh] = useState(0);
  const pendingKeyRef = useRef<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    async function load() {
      const [access, publicPage, eventPage] = await Promise.all([
        requestRef.current((token) => getActivityPermissions(token, requestId)),
        requestRef.current((token) => getRequestComments(token, requestId, "REQUESTER_VISIBLE")),
        requestRef.current((token) => getRequestTimeline(token, requestId)),
      ]);
      const privatePage = access.can_read_internal
        ? await requestRef.current((token) => getRequestComments(token, requestId, "INTERNAL")) : emptyPage<RequestComment>();
      if (!cancelled) { setPermissions(access); setComments(publicPage); setInternal(privatePage); setTimeline(eventPage); }
    }
    void load().catch((cause) => { if (!cancelled) { setPermissions(null); setComments(emptyPage()); setInternal(emptyPage()); setTimeline(emptyPage()); setError(errorText(cause)); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [requestId, refresh, revision]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (body.trim()) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [body]);
  function switchAudience(next: CommentVisibility) {
    if (next === visibility || busy || moreBusy) return;
    if (body.trim() && !window.confirm("Discard the unsent comment before changing its audience?")) return;
    setVisibility(next); setBody(""); pendingKeyRef.current = null; setNotice(""); setError("");
  }
  async function post(event: FormEvent) {
    event.preventDefault();
    if (busy || loading || !body.trim()) return;
    if (visibility === "INTERNAL" && !window.confirm("Record this as an internal note? It will not be shown in the requester's discussion.")) return;
    pendingKeyRef.current ??= crypto.randomUUID();
    const key = pendingKeyRef.current;
    setBusy(true); setError(""); setNotice("");
    try {
      const row = await requestRef.current((token) => postRequestComment(token, requestId, body, visibility, key));
      if (!mountedRef.current) return;
      const update = (old: Page<RequestComment>) => ({ ...old, items: [row, ...old.items.filter((item) => item.id !== row.id)] });
      if (visibility === "INTERNAL") setInternal(update); else setComments(update);
      setBody(""); pendingKeyRef.current = null; setNotice("Comment recorded. It cannot be edited or deleted."); setRefresh((value) => value + 1);
    } catch (cause) { if (mountedRef.current) setError(errorText(cause)); }
    finally { if (mountedRef.current) setBusy(false); }
  }
  async function moreEvents() {
    if (!timeline.next_before_id || moreBusy) return;
    setMoreBusy(true); setError("");
    try {
      const page = await requestRef.current((token) => getRequestTimeline(token, requestId, timeline.next_before_id));
      if (mountedRef.current) setTimeline((old) => ({ ...page, items: [...old.items, ...page.items.filter((row) => !old.items.some((item) => item.id === row.id))] }));
    } catch (cause) { if (mountedRef.current) setError(errorText(cause)); }
    finally { if (mountedRef.current) setMoreBusy(false); }
  }
  const active = visibility === "INTERNAL" ? internal : comments;
  async function moreComments() {
    if (!active.next_before_id || moreBusy) return;
    setMoreBusy(true); setError("");
    try {
      const page = await requestRef.current((token) => getRequestComments(token, requestId, visibility, active.next_before_id));
      const update = (old: Page<RequestComment>) => ({ ...page, items: [...old.items, ...page.items.filter((row) => !old.items.some((item) => item.id === row.id))] });
      if (mountedRef.current) { if (visibility === "INTERNAL") setInternal(update); else setComments(update); }
    } catch (cause) { if (mountedRef.current) setError(errorText(cause)); }
    finally { if (mountedRef.current) setMoreBusy(false); }
  }
  const canPost = permissions && (visibility === "INTERNAL" ? permissions.can_write_internal : permissions.can_comment);
  return <section aria-label="Request activity" className="space-y-4">
    <article className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 md:p-7">
      <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="font-semibold text-slate-900">Discussion</h3>
        <button type="button" className={button} disabled={busy || moreBusy || loading} onClick={() => { setError(""); setLoading(true); setRefresh((value) => value + 1); }}>Refresh activity</button></div>
      <div className="flex flex-wrap gap-2"><button type="button" className={button} disabled={busy || moreBusy} aria-pressed={visibility === "REQUESTER_VISIBLE"} onClick={() => switchAudience("REQUESTER_VISIBLE")}>Public discussion</button>
        {permissions?.can_read_internal ? <button type="button" className={button} disabled={busy || moreBusy} aria-pressed={visibility === "INTERNAL"} onClick={() => switchAudience("INTERNAL")}>Internal notes</button> : null}</div>
      <p className={`rounded-lg p-3 text-sm ${visibility === "INTERNAL" ? "bg-amber-50 text-amber-900" : "bg-blue-50 text-blue-900"}`}>
        {visibility === "INTERNAL" ? "Restricted to eligible assigned reviewers and authorized administrators/auditors. The requester cannot read these notes." : "Visible to the requester and everyone authorized to read this submitted request. Do not include secrets."}</p>
      {loading ? <p role="status" className="text-sm text-slate-500">Loading activity...</p> : null}
      {error ? <p role="alert" className="text-sm text-rose-800">{error}</p> : null}
      {notice ? <p role="status" className="text-sm text-emerald-800">{notice}</p> : null}
      {permissions ? <><CommentList items={active.items} />
        {!loading && active.items.length === 0 ? <p className="text-sm text-slate-500">No comments in this discussion yet.</p> : null}
        {active.next_before_id ? <button type="button" className={button} disabled={moreBusy || busy} onClick={() => void moreComments()}>Older comments</button> : null}
        {canPost ? <form aria-label="Add request comment" className="space-y-3 border-t border-slate-100 pt-4" onSubmit={post}>
          <label htmlFor={`request-comment-${requestId}`} className="block text-sm font-medium">{visibility === "INTERNAL" ? "Internal note" : "Public comment"}</label>
          <textarea id={`request-comment-${requestId}`} rows={4} maxLength={5000} required disabled={busy || loading} value={body}
            onChange={(event) => { setBody(event.target.value); pendingKeyRef.current = null; }}
            className="w-full rounded-xl border border-slate-300 p-3 text-sm focus:ring-2 focus:ring-blue-300" />
          <p className="text-xs text-slate-500">Append-only: correct a mistake with a new comment. Posting does not approve, reopen or complete the request.</p>
          <button type="submit" disabled={busy || loading || !body.trim()} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy ? "Recording..." : "Post comment"}</button>
        </form> : <p className="text-sm text-slate-500">Read-only discussion for your current permissions.</p>}
      </> : null}
    </article>
    <article className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 md:p-7">
      <div><h3 className="font-semibold text-slate-900">Activity timeline</h3><p className="mt-1 text-xs text-slate-500">Newest records first. Only activity you are authorized to see is included.</p></div>
      <ActivityTimeline items={timeline.items} />
      {!loading && permissions && timeline.items.length === 0 ? <p className="text-sm text-slate-500">No recorded timeline events yet.</p> : null}
      {timeline.next_before_id ? <button type="button" className={button} disabled={moreBusy} onClick={() => void moreEvents()}>Older activity</button> : null}
    </article>
    <aside aria-label="Attachments availability" className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">Attachments are not available in this release. Authorized file storage is a separate milestone.</aside>
  </section>;
}
