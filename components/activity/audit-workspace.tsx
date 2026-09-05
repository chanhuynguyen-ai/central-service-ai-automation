"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import type { AuthenticatedRequest } from "../../lib/catalog-api";
import { getAuditEvents, type AuditEvent, type Page } from "../../lib/activity-api";

export function AuditWorkspace({ request }: { request: AuthenticatedRequest }) {
  const requestRef = useRef(request);
  useEffect(() => { requestRef.current = request; }, [request]);
  const [eventType, setEventType] = useState("");
  const [requestId, setRequestId] = useState("");
  const [filters, setFilters] = useState<{ eventType?: string; requestId?: number }>({});
  const [page, setPage] = useState<Page<AuditEvent>>({ items: [], next_before_id: null });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [busy, setBusy] = useState(false);
  const generationRef = useRef(0);
  useEffect(() => {
    const generation = ++generationRef.current;
    requestRef.current((token) => getAuditEvents(token, filters)).then((result) => {
      if (generation === generationRef.current) setPage(result);
    }).catch((cause) => { if (generation === generationRef.current) { setPage({ items: [], next_before_id: null }); setError(cause instanceof Error ? cause.message : "Audit access unavailable."); } })
      .finally(() => { if (generation === generationRef.current) setLoading(false); });
    return () => { generationRef.current++; };
  }, [filters, refresh]);
  function search(event: FormEvent) {
    event.preventDefault();
    setError(""); setLoading(true);
    setFilters({ eventType: eventType.trim() || undefined, requestId: requestId ? Number(requestId) : undefined });
  }
  async function more() {
    if (!page.next_before_id || busy || loading) return;
    const generation = generationRef.current;
    setBusy(true); setError("");
    try {
      const result = await requestRef.current((token) => getAuditEvents(token, filters, page.next_before_id));
      if (generation === generationRef.current) setPage((old) => ({ ...result, items: [...old.items, ...result.items.filter((row) => !old.items.some((item) => item.id === row.id))] }));
    } catch (cause) { if (generation === generationRef.current) setError(cause instanceof Error ? cause.message : "Could not load older audit entries."); }
    finally { if (generation === generationRef.current) setBusy(false); }
  }
  return <section aria-label="Audit workspace" className="mt-6 space-y-4">
    <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">Privileged read-only view. Access is itself audited. Comment bodies, passwords, tokens and form values are not copied into this view. Older records may have no resource or correlation identifier.</p>
    <form aria-label="Filter audit records" onSubmit={search} className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4">
      <div className="space-y-1"><label htmlFor="audit-event-filter" className="block text-sm font-medium">Event type</label><input id="audit-event-filter" pattern="[a-z_]+" maxLength={60} placeholder="e.g. approval_decided" value={eventType} disabled={busy} onChange={(event) => setEventType(event.target.value)} className="rounded-lg border border-slate-300 p-2 text-sm" /></div>
      <div className="space-y-1"><label htmlFor="audit-request-filter" className="block text-sm font-medium">Numeric request ID</label><input id="audit-request-filter" type="number" min={1} step={1} value={requestId} disabled={busy} onChange={(event) => setRequestId(event.target.value)} className="w-40 rounded-lg border border-slate-300 p-2 text-sm" /></div>
      <button className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={busy || loading} type="submit">Apply filters</button>
      <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm disabled:opacity-50" disabled={busy || loading} type="button" onClick={() => { setError(""); setLoading(true); setRefresh((old) => old + 1); }}>Refresh audit</button>
    </form>
    {loading ? <p role="status" className="text-sm text-slate-500">Loading audit records...</p> : null}
    {error ? <p role="alert" className="rounded-xl bg-rose-50 p-4 text-sm text-rose-800">{error}</p> : null}
    {!loading ? <ol className="space-y-3">{page.items.map((item) => <li key={item.id} className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap justify-between gap-2"><p className="break-all font-semibold text-slate-900">{item.event_type}</p><time className="text-xs text-slate-500" dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time></div>
      <p className="mt-1 text-sm text-slate-600">{item.actor_name ?? "System / unauthenticated"} / {item.resource_type ?? "Legacy resource"}{item.resource_id ? ` #${item.resource_id}` : ""}{item.request_id ? ` / Request #${item.request_id}` : ""}</p>
      {Object.keys(item.details).length ? <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-700">{JSON.stringify(item.details, null, 2)}</pre> : null}
      {item.correlation_id ? <p className="mt-2 break-all font-mono text-xs text-slate-400">Correlation: {item.correlation_id}</p> : null}
    </li>)}</ol> : null}
    {!loading && !error && page.items.length === 0 ? <p className="text-sm text-slate-500">No audit records match these filters.</p> : null}
    {!loading && page.next_before_id ? <button type="button" className="rounded-lg border border-slate-300 px-4 py-2 text-sm disabled:opacity-50" disabled={busy} onClick={() => void more()}>Older audit records</button> : null}
  </section>;
}
