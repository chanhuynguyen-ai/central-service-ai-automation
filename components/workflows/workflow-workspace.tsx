"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import type { AuthenticatedRequest, FormValue } from "../../lib/catalog-api";
import {
  decideApprovalTask, getSubmission, listApprovalTasks, listSubmissions,
  type ApprovalTask, type Decision, type InboxTask, type Submission, type SubmissionDetail,
} from "../../lib/workflow-api";

const button = "rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50";
const primary = "rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50";
const input = "w-full rounded-lg border border-slate-300 bg-white p-2 text-sm focus:ring-2 focus:ring-blue-300";
export const stateLabel = (value: string) => value.toLowerCase().replaceAll("_", " ");
const displayValue = (value: FormValue | undefined) => value == null ? "Not supplied"
  : typeof value === "boolean" ? (value ? "Yes" : "No")
    : Array.isArray(value) ? value.join(", ") : typeof value === "object" ? `${value.start} to ${value.end}` : String(value);

function DecisionForm({ task, request, onDecided }: {
  task: ApprovalTask; request: AuthenticatedRequest; onDecided: (result: SubmissionDetail) => void;
}) {
  const [decision, setDecision] = useState<Decision>("approve");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function act(event: FormEvent) {
    event.preventDefault();
    if (busy || (decision !== "approve" && !comment.trim())) return;
    if (!window.confirm(`Confirm ${stateLabel(decision)}? This decision is recorded in the approval history.`)) return;
    setBusy(true); setError("");
    try { onDecided(await request((token) => decideApprovalTask(token, task, decision, comment))); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Decision could not be recorded."); }
    finally { setBusy(false); }
  }
  return <form onSubmit={act} className="mt-3 space-y-3 rounded-xl border border-blue-200 bg-blue-50 p-4" aria-label="Approval decision">
    <p className="text-sm font-semibold text-blue-900">Assigned to you</p>
    <label className="grid gap-1 text-sm" htmlFor={`decision-${task.id}`}>Decision
      <select id={`decision-${task.id}`} className={input} disabled={busy} value={decision} onChange={(event) => setDecision(event.target.value as Decision)}>
        <option value="approve">Approve</option><option value="reject">Reject</option><option value="request_changes">Request changes</option>
      </select>
    </label>
    <label className="grid gap-1 text-sm" htmlFor={`comment-${task.id}`}>Decision comment{decision !== "approve" ? " (required)" : " (optional)"}
      <textarea id={`comment-${task.id}`} className={input} maxLength={2000} rows={3} disabled={busy} required={decision !== "approve"} value={comment} onChange={(event) => setComment(event.target.value)} />
    </label>
    {error ? <p role="alert" className="text-sm text-rose-800">{error}</p> : null}
    <button type="submit" className={primary} disabled={busy || (decision !== "approve" && !comment.trim())}>{busy ? "Recording..." : "Record decision"}</button>
  </form>;
}

export function WorkflowWorkspace({ mode, request, currentUserId, initialRequestId, onEditChanges }: {
  mode: "submissions" | "approvals"; request: AuthenticatedRequest; currentUserId: number;
  initialRequestId?: number | null; onEditChanges: () => void;
}) {
  const requestRef = useRef(request);
  useEffect(() => { requestRef.current = request; }, [request]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [tasks, setTasks] = useState<InboxTask[]>([]);
  const [total, setTotal] = useState(0);
  const [history, setHistory] = useState<"pending" | "history">("pending");
  const [selected, setSelected] = useState<number | null>(initialRequestId ?? null);
  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [moreBusy, setMoreBusy] = useState(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    let cancelled = false;
    const operation = mode === "approvals"
      ? requestRef.current((token) => listApprovalTasks(token, history)).then((result) => { if (!cancelled) { setTasks(result.items); setTotal(result.total); } })
      : requestRef.current((token) => listSubmissions(token)).then((result) => { if (!cancelled) { setSubmissions(result.items); setTotal(result.total); } });
    operation.catch((cause) => { if (!cancelled) setError(cause instanceof Error ? cause.message : "Could not load workflow data."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [mode, history, refresh]);
  useEffect(() => {
    if (selected === null) return;
    let cancelled = false;
    requestRef.current((token) => getSubmission(token, selected))
      .then((result) => { if (!cancelled) setDetail(result); })
      .catch((cause) => { if (!cancelled) setError(cause instanceof Error ? cause.message : "Could not open submission."); });
    return () => { cancelled = true; };
  }, [selected, refresh]);
  function open(id: number) { if (id === selected) setRefresh((value) => value + 1); else setSelected(id); setDetail(null); setNotice(""); setError(""); }
  function onDecided(result: SubmissionDetail) {
    if (!mounted.current) return;
    setDetail(result); setNotice("Decision recorded."); setError(""); setRefresh((value) => value + 1);
  }
  async function more() {
    setMoreBusy(true); setError("");
    try {
      if (mode === "approvals") {
        const result = await requestRef.current((token) => listApprovalTasks(token, history, tasks.length));
        if (mounted.current) { setTasks((old) => [...old, ...result.items.filter((row) => !old.some((item) => item.id === row.id))]); setTotal(result.total); }
      } else {
        const result = await requestRef.current((token) => listSubmissions(token, submissions.length));
        if (mounted.current) { setSubmissions((old) => [...old, ...result.items.filter((row) => !old.some((item) => item.id === row.id))]); setTotal(result.total); }
      }
    } catch (cause) { if (mounted.current) setError(cause instanceof Error ? cause.message : "Could not load more."); }
    finally { if (mounted.current) setMoreBusy(false); }
  }
  const count = mode === "approvals" ? tasks.length : submissions.length;
  return <section className="mt-6 space-y-4" aria-label="Workflow workspace">
    <div className="flex flex-wrap items-center justify-between gap-3">
      {mode === "approvals" ? <div className="flex gap-2">{(["pending", "history"] as const).map((tab) => <button type="button" key={tab} aria-pressed={history === tab} className={history === tab ? primary : button} onClick={() => { if (history === tab) setRefresh((value) => value + 1); else setHistory(tab); setLoading(true); setTasks([]); setError(""); }}>{tab === "pending" ? "Pending tasks" : "Task history"}</button>)}</div>
        : <p className="text-sm text-slate-600">Submitted requests within your authorized scope. Private drafts remain under My drafts.</p>}
      <button type="button" className={button} onClick={() => { setError(""); setLoading(true); setRefresh((value) => value + 1); }}>Refresh workflow</button>
    </div>
    {error ? <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</p> : null}
    {notice ? <p role="status" className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</p> : null}
    <div className="grid items-start gap-5 xl:grid-cols-[minmax(250px,0.65fr)_minmax(0,1.35fr)]">
      <div className="space-y-3">
        {loading ? <p role="status" className="text-sm text-slate-500">Loading workflows...</p> : null}
        {mode === "approvals" ? tasks.map((task) => <button key={task.id} type="button" className="block w-full rounded-xl border border-slate-200 bg-white p-4 text-left hover:border-blue-400" onClick={() => open(task.request_id)}><span className="block font-semibold text-slate-900">{task.title}</span><span className="mt-1 block text-sm text-slate-600">{task.step_name} / {stateLabel(task.status)}</span><span className="mt-2 block text-xs text-slate-500">{task.requester_name} / Attempt {task.attempt}</span></button>)
          : submissions.map((item) => <button key={item.id} type="button" className="block w-full rounded-xl border border-slate-200 bg-white p-4 text-left hover:border-blue-400" onClick={() => open(item.id)}><span className="block font-semibold text-slate-900">{item.title}</span><span className="mt-1 block text-sm capitalize text-blue-700">{stateLabel(item.status)}</span><span className="mt-2 block text-xs text-slate-500">{item.requester_name} / {item.reference}</span></button>)}
        {!loading && count === 0 ? <p className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">{mode === "approvals" ? "No assigned tasks in this view." : "No submitted requests in your scope yet."}</p> : null}
        {count < total ? <button type="button" className={button} disabled={moreBusy} onClick={() => void more()}>Load more</button> : null}
      </div>
      <div className="space-y-4">{detail ? <>
        <article className="rounded-2xl border border-slate-200 bg-white p-5 md:p-7">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">{detail.reference}</p><h2 className="mt-2 text-xl font-semibold">{detail.title}</h2>
          <p className="mt-2 text-sm text-slate-600">{detail.requester_name} / {detail.requester_department}</p>
          <p className="mt-3 text-sm font-semibold capitalize" role="status">Request status: {stateLabel(detail.status)}</p>
          {detail.status === "approved" ? <p className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">Approval completed. Service fulfillment has not started; it is a separate lifecycle.</p> : null}
          {detail.status === "changes_requested" && detail.requester_id === currentUserId ? <div className="mt-4 space-y-2"><p className="text-sm text-amber-800">Review the feedback below, edit under My drafts, save, then resubmit. The whole approval chain restarts with a new attempt; earlier decisions remain in history.</p><button className={button} type="button" onClick={onEditChanges}>Return to My drafts</button></div> : null}
        </article>
        {[...detail.attempts].reverse().map((attempt) => <article key={attempt.id} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 md:p-7">
          <h3 className="font-semibold">Attempt {attempt.attempt} / {stateLabel(attempt.status)}</h3>
          <p className="text-xs text-slate-500">Form v{attempt.snapshot.form_version} / Workflow v{attempt.snapshot.workflow.version} / {new Date(attempt.started_at).toLocaleString()}</p>
          <div className="rounded-xl bg-slate-50 p-4"><h4 className="font-semibold text-slate-800">Submitted information</h4><p className="my-2 whitespace-pre-wrap text-sm text-slate-600">{attempt.snapshot.description}</p><dl className="grid gap-3 sm:grid-cols-2">{attempt.snapshot.form_schema.sections.flatMap((section) => section.fields).map((field) => <div key={field.key}><dt className="text-xs font-medium text-slate-500">{field.label}</dt><dd className="mt-1 break-words whitespace-pre-wrap text-sm text-slate-800">{displayValue(attempt.snapshot.form_data[field.key])}</dd></div>)}</dl></div>
          <ol className="space-y-3">{attempt.steps.map((step) => <li key={step.id} className="rounded-xl border border-slate-200 p-4"><p className="text-sm font-semibold">{step.step_order}. {step.name} <span className="ml-2 font-normal text-slate-500">{stateLabel(step.status)}</span></p>{step.tasks.map((task) => <div key={task.id} className="mt-3"><p className="text-sm text-slate-600">{task.approver_name} / {stateLabel(task.status)}</p>{task.decision ? <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{task.decision.comment || "Approved without additional comment."}</p> : null}{task.can_decide ? <DecisionForm key={`${task.id}-${task.version}`} task={task} request={request} onDecided={onDecided} /> : null}</div>)}</li>)}</ol>
        </article>)}
      </> : <p className="rounded-2xl border border-dashed border-slate-300 p-8 text-sm text-slate-500">{selected ? "Opening submitted workflow..." : "Select a submitted request or an assigned task to view its approval progress."}</p>}</div>
    </div>
  </section>;
}
