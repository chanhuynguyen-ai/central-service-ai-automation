"use client";

import { useEffect, useRef, useState, type FormEvent, type MutableRefObject } from "react";
import { ApiError } from "../../lib/api";
import {
  createDraft, getDraft, getDraftLookups, listCatalog, listDrafts, updateDraft,
  type AuthenticatedRequest, type CatalogEntry, type CatalogVersion,
  type DraftLookups, type DraftValues, type FieldIssue, type FormValue, type RequestDraft,
} from "../../lib/catalog-api";
import { DynamicForm } from "./dynamic-form";

const button = "rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50";
const primary = "rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50";
const input = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200";
const emptyValues = (): DraftValues => ({ title: "", description: "", form_data: {} });

export function CatalogWorkspace({ mode, request, beforeLeave: beforeLeaveRef, onBrowse }: {
  mode: "catalog" | "drafts"; request: AuthenticatedRequest;
  beforeLeave: MutableRefObject<() => boolean>; onBrowse: () => void;
}) {
  const requestRef = useRef(request);
  useEffect(() => { requestRef.current = request; }, [request]);
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [drafts, setDrafts] = useState<RequestDraft[]>([]);
  const [total, setTotal] = useState(0);
  const [lookups, setLookups] = useState<DraftLookups>({ users: [], departments: [] });
  const [version, setVersion] = useState<CatalogVersion | null>(null);
  const [draft, setDraft] = useState<RequestDraft | null>(null);
  const [values, setValues] = useState<DraftValues>(emptyValues);
  const [issues, setIssues] = useState<FieldIssue[]>([]);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [conflict, setConflict] = useState(false);
  const [search, setSearch] = useState("");
  const [reload, setReload] = useState(0);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);

  useEffect(() => {
    let cancelled = false;
    requestRef.current((token) => Promise.all([listCatalog(token), listDrafts(token), getDraftLookups(token)]))
      .then(([services, result, options]) => {
        if (cancelled) return;
        setCatalog(services); setDrafts(result.items); setTotal(result.total); setLookups(options);
      })
      .catch((cause) => { if (!cancelled) setError(cause instanceof Error ? cause.message : "Could not load services."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [reload]);

  useEffect(() => {
    beforeLeaveRef.current = () => !dirty || window.confirm("You have unsaved changes. Leave without saving?");
    const warn = (event: BeforeUnloadEvent) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", warn);
    return () => { beforeLeaveRef.current = () => true; window.removeEventListener("beforeunload", warn); };
  }, [dirty, beforeLeaveRef]);

  function resetEditor() {
    if (!beforeLeaveRef.current()) return;
    setVersion(null); setDraft(null); setValues(emptyValues()); setIssues([]);
    setDirty(false); setConflict(false); setError(""); setNotice("");
  }
  function choose(entry: CatalogEntry) {
    if (!beforeLeaveRef.current()) return;
    setVersion(entry.published_version); setDraft(null);
    setValues({ title: entry.published_version.title, description: "", form_data: {} });
    setIssues([]); setError(""); setNotice(""); setConflict(false); setDirty(false);
  }
  function acceptDraft(result: RequestDraft) {
    setDraft(result); setVersion(result.request_type_version);
    setValues({ title: result.title, description: result.description, form_data: result.form_data });
    setIssues(result.validation.errors); setDirty(false); setConflict(false);
  }
  async function openDraft(id: number) {
    if (!beforeLeaveRef.current()) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await requestRef.current((token) => getDraft(token, id));
      if (alive.current) acceptDraft(result);
    } catch (cause) {
      if (alive.current) setError(cause instanceof Error ? cause.message : "Could not open draft.");
    } finally { if (alive.current) setBusy(false); }
  }
  function changeField(key: string, value: FormValue) {
    setValues((current) => ({ ...current, form_data: { ...current.form_data, [key]: value } }));
    setDirty(true); setNotice(""); setIssues((current) => current.filter((issue) => issue.field !== key));
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!version || busy || conflict) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await requestRef.current((token) => draft
        ? updateDraft(token, draft, values) : createDraft(token, version.id, values));
      if (!alive.current) return;
      acceptDraft(result);
      setDrafts((current) => [result, ...current.filter((item) => item.id !== result.id)]);
      if (!draft) setTotal((current) => current + 1);
      setNotice(result.validation.valid
        ? "Saved privately. Required fields are complete. Workflow submission is the next phase."
        : "Draft saved. You can return later to complete the highlighted fields.");
    } catch (cause) {
      if (!alive.current) return;
      setError(cause instanceof Error ? cause.message : "Could not save draft.");
      if (cause instanceof ApiError && cause.status === 409 && draft) setConflict(true);
      if (cause instanceof ApiError && Array.isArray(cause.detail)) {
        setIssues(cause.detail.filter((issue): issue is FieldIssue =>
          typeof issue === "object" && issue !== null && "field" in issue && "message" in issue));
      }
    } finally { if (alive.current) setBusy(false); }
  }
  async function loadMore() {
    setBusy(true); setError("");
    try {
      const result = await requestRef.current((token) => listDrafts(token, drafts.length));
      if (alive.current) {
        setDrafts((current) => [...current, ...result.items.filter((item) => !current.some((existing) => existing.id === item.id))]);
        setTotal(result.total);
      }
    } catch (cause) { if (alive.current) setError(cause instanceof Error ? cause.message : "Could not load drafts."); }
    finally { if (alive.current) setBusy(false); }
  }

  const filtered = catalog.filter((entry) => `${entry.code} ${entry.category} ${entry.published_version.title}`.toLowerCase().includes(search.toLowerCase()));
  return <section className="mt-6 space-y-4" aria-label="Catalog and draft workspace">
    {error ? <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}
      {conflict && draft ? <button type="button" disabled={busy} className={`${button} ml-3 bg-white`} onClick={() => void openDraft(draft.id)}>Reload saved version</button> : null}
    </div> : null}
    {notice ? <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</p> : null}
    {version ? <form onSubmit={save} noValidate className="mx-auto max-w-3xl space-y-5 rounded-2xl border border-slate-200 bg-white p-5 md:p-7">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-xl font-semibold text-slate-900">{version.title}</h2><p className="mt-1 text-sm text-slate-500">Form version {version.version} · {draft ? `Saved revision ${draft.revision}` : "Not saved yet"}</p></div><button type="button" disabled={busy} className={button} onClick={resetEditor}>Back to {mode === "catalog" ? "catalog" : "drafts"}</button></div>
      {version.status === "RETIRED" ? <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">A newer service version exists. This draft keeps its original form; your data is not silently migrated.</p> : null}
      {version.description ? <p className="text-sm leading-6 text-slate-600">{version.description}</p> : null}
      <label className="grid gap-2 text-sm font-medium" htmlFor="draft-title">Request title *<input id="draft-title" className={input} disabled={busy} maxLength={180} value={values.title} onChange={(event) => { setValues((current) => ({ ...current, title: event.target.value })); setDirty(true); setNotice(""); }} /></label>
      {issues.filter((issue) => issue.field === "title").map((issue) => <p key={issue.field} className="text-sm text-rose-700">{issue.message}</p>)}
      <label className="grid gap-2 text-sm font-medium" htmlFor="draft-description">Business context *<textarea id="draft-description" className={input} disabled={busy} rows={3} maxLength={5000} value={values.description} onChange={(event) => { setValues((current) => ({ ...current, description: event.target.value })); setDirty(true); setNotice(""); }} /></label>
      {issues.filter((issue) => issue.field === "description" || issue.field === "form_data").map((issue) => <p key={issue.field} className="text-sm text-rose-700">{issue.message}</p>)}
      <DynamicForm schema={version.form_schema} values={values.form_data} lookups={lookups} errors={issues} disabled={busy} onChange={changeField} />
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 bg-white py-4"><div className="text-xs text-slate-500"><p>{dirty ? "Unsaved changes" : draft ? `Saved ${new Date(draft.updated_at).toLocaleString()}` : "Only saved drafts are persisted"}</p><p className="mt-1">Saving does not submit, start an SLA, or call an AI model.</p></div><button type="submit" className={primary} disabled={busy || conflict}>{busy ? "Saving..." : "Save draft"}</button></div>
      {draft ? <p className="break-all font-mono text-xs text-slate-500">{draft.reference}</p> : null}
    </form> : <>
      <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-slate-600">{mode === "catalog" ? "Choose a published service. Its form version is preserved in your draft." : `Your private drafts (${drafts.length} of ${total}). Other users cannot open or edit them.`}</p><button type="button" disabled={loading || busy} className={button} onClick={() => { setLoading(true); setError(""); setReload((value) => value + 1); }}>Refresh</button></div>
      {loading ? <p role="status" className="rounded-xl border bg-white p-8 text-sm text-slate-500">Loading catalog and drafts...</p> : mode === "catalog" ? <>
        <label className="grid max-w-md gap-2 text-sm font-medium" htmlFor="catalog-search">Search services<input id="catalog-search" className={input} placeholder="Laptop, software, reimbursement..." value={search} onChange={(event) => setSearch(event.target.value)} /></label>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{filtered.map((entry) => <article key={entry.id} className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5"><p className="text-xs font-semibold uppercase tracking-wide text-blue-700">{entry.category}</p><h2 className="mt-2 text-lg font-semibold text-slate-900">{entry.published_version.title}</h2><p className="my-3 flex-1 text-sm leading-6 text-slate-500">{entry.published_version.description}</p><div className="flex items-center justify-between gap-2"><span className="text-xs text-slate-500">Version {entry.published_version.version}</span><button type="button" className={primary} onClick={() => choose(entry)}>Start draft</button></div></article>)}</div>
        {!filtered.length ? <p className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">{catalog.length ? "No services match your search." : "No active published services yet. An administrator can publish a request type, or run the documented demo catalog seed."}</p> : null}
      </> : <>
        <div className="grid gap-3">{drafts.map((item) => <article key={item.id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-5"><div><h2 className="font-semibold text-slate-900">{item.title || "Untitled draft"}</h2><p className="mt-1 text-xs text-slate-500">{item.request_type_version.title} · Form v{item.request_type_version.version} · Revision {item.revision}</p><p className="mt-1 text-xs text-slate-500">{item.validation.valid ? "Required fields complete" : `${item.validation.errors.length} fields or rules need attention`} · {new Date(item.updated_at).toLocaleString()}</p></div><button type="button" className={button} disabled={busy} onClick={() => void openDraft(item.id)}>Continue editing</button></article>)}</div>
        {!drafts.length ? <div className="rounded-xl border border-slate-200 bg-white p-8 text-center"><p className="mb-4 text-sm text-slate-500">You have no saved drafts.</p><button type="button" className={primary} onClick={onBrowse}>Browse services</button></div> : null}
        {drafts.length < total ? <button type="button" className={button} disabled={busy} onClick={() => void loadMore()}>Load more drafts</button> : null}
      </>}
    </>}
  </section>;
}
