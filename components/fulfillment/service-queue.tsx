"use client";

import { useEffect, useRef, useState } from "react";

import {
  actOnWorkItem,
  listWorkItems,
  type FulfillmentRequest,
  type ServiceWorkItem,
  type WorkAction,
  type WorkScope,
  type WorkStatus,
} from "../../lib/fulfillment-api";

const button = "rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50";
const primary = "rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50";
const label = (value: string) => value.toLowerCase().replaceAll("_", " ");
const statuses: WorkStatus[] = ["QUEUED", "ASSIGNED", "IN_PROGRESS", "WAITING_REQUESTER", "RESOLVED", "CLOSED"];

function actionsFor(item: ServiceWorkItem): WorkAction[] {
  if (!item.can_manage) return [];
  if (item.status === "QUEUED") return ["assign"];
  if (item.status === "ASSIGNED") return ["start"];
  if (item.status === "IN_PROGRESS") return ["wait", "resolve"];
  if (item.status === "WAITING_REQUESTER") return ["resume", "resolve"];
  if (item.status === "RESOLVED") return ["close"];
  return [];
}

function WorkCard({ item, request, onChanged }: {
  item: ServiceWorkItem;
  request: FulfillmentRequest;
  onChanged: (item: ServiceWorkItem) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [resolution, setResolution] = useState("");

  async function run(action: WorkAction) {
    if (busy) return;
    if (action === "resolve" && !resolution.trim()) {
      setError("Add a resolution summary before resolving the work item.");
      return;
    }
    const confirmation = action === "close"
      ? "Close this request? This marks the governed request as completed."
      : `Confirm ${label(action)}?`;
    if (!window.confirm(confirmation)) return;
    setBusy(true);
    setError("");
    try {
      const updated = await request((token) => actOnWorkItem(
        token,
        item,
        action,
        action === "resolve" ? { note: resolution.trim() } : {},
      ));
      onChanged(updated);
      if (action === "resolve") setResolution("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The work item could not be updated.");
    } finally {
      setBusy(false);
    }
  }

  const actions = actionsFor(item);
  return <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">{item.reference}</p>
        <h2 className="mt-1 text-lg font-semibold text-slate-950">{item.title}</h2>
        <p className="mt-1 text-sm text-slate-500">{item.requester_name} / {item.service_team_name}</p>
      </div>
      <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold capitalize text-slate-700">{label(item.status)}</span>
    </div>
    <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
      <div><dt className="text-xs font-medium uppercase tracking-wide text-slate-400">Assignee</dt><dd className="mt-1 text-slate-700">{item.assignee_name ?? "Unassigned"}</dd></div>
      <div><dt className="text-xs font-medium uppercase tracking-wide text-slate-400">Queued</dt><dd className="mt-1 text-slate-700">{new Date(item.queued_at).toLocaleString()}</dd></div>
      {item.resolution_summary ? <div className="sm:col-span-2"><dt className="text-xs font-medium uppercase tracking-wide text-slate-400">Resolution</dt><dd className="mt-1 whitespace-pre-wrap text-slate-700">{item.resolution_summary}</dd></div> : null}
    </dl>
    {actions.includes("resolve") ? <label className="mt-4 block text-sm font-medium text-slate-700">Resolution summary
      <textarea value={resolution} onChange={(event) => setResolution(event.target.value)} maxLength={2000} rows={3} disabled={busy} className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-sm" placeholder="Describe the outcome delivered to the requester." />
    </label> : null}
    {error ? <p role="alert" className="mt-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p> : null}
    {actions.length ? <div className="mt-4 flex flex-wrap gap-2">{actions.map((action) => <button key={action} type="button" disabled={busy || (action === "resolve" && !resolution.trim())} className={action === "assign" || action === "start" || action === "resolve" ? primary : button} onClick={() => void run(action)}>{busy ? "Updating..." : action === "assign" ? "Claim work" : action === "wait" ? "Wait for requester" : label(action)}</button>)}</div> : null}
  </article>;
}

export function ServiceQueue({ request }: { request: FulfillmentRequest }) {
  const requestRef = useRef(request);
  useEffect(() => { requestRef.current = request; }, [request]);
  const [scope, setScope] = useState<WorkScope>("team");
  const [status, setStatus] = useState<WorkStatus | "">("");
  const [items, setItems] = useState<ServiceWorkItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    requestRef.current((token) => listWorkItems(token, scope, status || undefined))
      .then((result) => {
        if (!cancelled) {
          setItems(result.items);
          setTotal(result.total);
        }
      })
      .catch((cause) => {
        if (!cancelled) {
          setItems([]);
          setTotal(0);
          setError(cause instanceof Error ? cause.message : "Service queue could not be loaded.");
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [scope, status, refresh]);

  function changed(updated: ServiceWorkItem) {
    setItems((current) => current.map((item) => item.id === updated.id ? updated : item));
    setRefresh((value) => value + 1);
  }

  return <section className="space-y-4" aria-label="Service fulfillment queue">
    <div className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap gap-2">{(["team", "unassigned", "mine"] as WorkScope[]).map((value) => <button key={value} type="button" aria-pressed={scope === value} className={scope === value ? primary : button} onClick={() => setScope(value)}>{value === "team" ? "Team queue" : value === "unassigned" ? "Unassigned" : "Assigned to me"}</button>)}</div>
      <label className="ml-auto grid gap-1 text-sm font-medium text-slate-700">Status
        <select value={status} onChange={(event) => setStatus(event.target.value as WorkStatus | "")} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
          <option value="">All statuses</option>
          {statuses.map((value) => <option key={value} value={value}>{label(value)}</option>)}
        </select>
      </label>
      <button type="button" className={button} onClick={() => setRefresh((value) => value + 1)}>Refresh</button>
    </div>
    <p className="text-sm text-slate-500">{loading ? "Loading service work..." : `${total} work item${total === 1 ? "" : "s"} in this view.`}</p>
    {error ? <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</p> : null}
    {!loading && !error && items.length === 0 ? <p className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">No service work matches this view.</p> : null}
    <div className="grid gap-4 xl:grid-cols-2">{items.map((item) => <WorkCard key={`${item.id}-${item.version}`} item={item} request={request} onChanged={changed} />)}</div>
  </section>;
}
