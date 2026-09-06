"use client";

import { useState } from "react";
import { suggestIntakeDraft, type IntakeDraftSuggestion } from "../../lib/ai-intake-api";
import type { AuthenticatedRequest, CatalogEntry, FormData } from "../../lib/catalog-api";

const primary = "rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50";
const button = "rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50";
const input = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-200";

export function AIIntakeCard({
  request,
  catalog,
  onApply,
}: {
  request: AuthenticatedRequest;
  catalog: CatalogEntry[];
  onApply: (entry: CatalogEntry, description: string, fields: FormData) => void;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [suggestion, setSuggestion] = useState<IntakeDraftSuggestion | null>(null);

  async function suggest(requestTypeCode?: string) {
    if (busy || text.trim().length < 5) return;
    setBusy(true);
    setError("");
    try {
      const result = await request((token) => suggestIntakeDraft(token, text.trim(), requestTypeCode));
      setSuggestion(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "AI intake could not prepare a suggestion.");
    } finally {
      setBusy(false);
    }
  }

  function apply() {
    if (!suggestion) return;
    const entry = catalog.find((item) => item.published_version.id === suggestion.request_type_version_id);
    if (!entry) {
      setError("The suggested service version is no longer available. Refresh the catalog and try again.");
      return;
    }
    onApply(entry, text.trim(), suggestion.extracted_fields);
    setSuggestion(null);
  }

  return <section className="rounded-2xl border border-violet-200 bg-violet-50/60 p-5" aria-labelledby="ai-intake-title">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">AI-assisted intake</p>
        <h2 id="ai-intake-title" className="mt-1 text-lg font-semibold text-slate-900">Describe what you need</h2>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">AI can suggest a published service and prefill values. You review and edit everything before anything is saved or submitted.</p>
      </div>
      <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-violet-700">Advisory only</span>
    </div>
    <label className="mt-4 grid gap-2 text-sm font-medium" htmlFor="ai-intake-text">
      Your request
      <textarea
        id="ai-intake-text"
        rows={4}
        maxLength={5000}
        className={input}
        placeholder="Example: My laptop keeps shutting down during client work and I need a replacement urgently."
        value={text}
        onChange={(event) => { setText(event.target.value); setSuggestion(null); setError(""); }}
      />
    </label>
    <div className="mt-3 flex flex-wrap items-center gap-3">
      <button type="button" className={primary} disabled={busy || text.trim().length < 5 || !catalog.length} onClick={() => void suggest()}>
        {busy ? "Preparing suggestion..." : "Suggest request"}
      </button>
      <p className="text-xs text-slate-500">Only active published request types are eligible.</p>
    </div>
    {error ? <p role="alert" className="mt-3 rounded-lg border border-rose-200 bg-white p-3 text-sm text-rose-700">{error}</p> : null}
    {suggestion ? <div className="mt-4 rounded-xl border border-violet-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">Suggested service</p>
          <p className="mt-1 font-semibold text-slate-900">{suggestion.title}</p>
          <p className="mt-1 text-xs text-slate-500">{suggestion.category} · Confidence {Math.round(suggestion.confidence * 100)}% · {suggestion.provider}</p>
        </div>
        <button type="button" className={primary} onClick={apply}>Review this draft</button>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Prefilled fields</p>
          <p className="mt-1 text-sm text-slate-700">{Object.keys(suggestion.extracted_fields).length ? Object.keys(suggestion.extracted_fields).join(", ") : "No safe values extracted yet."}</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Still required</p>
          <p className="mt-1 text-sm text-slate-700">{suggestion.missing_required_fields.length ? suggestion.missing_required_fields.join(", ") : "No required fields missing."}</p>
        </div>
      </div>
      {suggestion.clarifications.length ? <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">Please clarify before submission</p>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">{suggestion.clarifications.map((item) => <li key={item.field}>{item.prompt}</li>)}</ul>
      </div> : null}
      {suggestion.alternatives.length ? <div className="mt-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">Alternatives</p>
        <div className="flex flex-wrap gap-2">{suggestion.alternatives.map((item) => <button key={item.request_type_code} type="button" className={button} disabled={busy} onClick={() => void suggest(item.request_type_code)}>{item.title}</button>)}</div>
      </div> : null}
      <p className="mt-4 text-xs leading-5 text-slate-500">AI does not choose approvers, grant permissions, or submit the request. Required fields and clarification prompts are derived from the published form schema.</p>
    </div> : null}
  </section>;
}
