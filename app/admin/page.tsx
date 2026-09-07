"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowLeft, FilePlus2, Save, Send, Settings2, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  AdminRequestType,
  AdminRequestTypeVersion,
  createAdminRequestType,
  createAdminRequestTypeVersion,
  listAdminRequestTypes,
  listAdminRequestTypeVersions,
  publishAdminRequestTypeVersion,
  updateAdminRequestType,
  updateAdminRequestTypeVersion,
} from "@/lib/admin-catalog-api";
import { getStoredSession, userHasAnyRole } from "@/lib/auth";

const DEFAULT_SCHEMA = JSON.stringify(
  {
    sections: [
      {
        title: "Request details",
        fields: [
          {
            key: "reason",
            type: "textarea",
            label: "Reason",
            required: true,
          },
        ],
      },
    ],
  },
  null,
  2,
);

export default function AdminPage() {
  const session = typeof window === "undefined" ? null : getStoredSession();
  const token = session?.accessToken ?? "";
  const isAdmin = Boolean(session?.user && userHasAnyRole(session.user, "ADMIN"));
  const [types, setTypes] = useState<AdminRequestType[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [versions, setVersions] = useState<AdminRequestTypeVersion[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const [code, setCode] = useState("");
  const [category, setCategory] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [schemaText, setSchemaText] = useState(DEFAULT_SCHEMA);

  const selected = useMemo(
    () => types.find((item) => item.id === selectedId) ?? null,
    [types, selectedId],
  );
  const draftVersion = useMemo(
    () => [...versions].reverse().find((item) => item.status === "DRAFT") ?? null,
    [versions],
  );

  async function loadTypes(preferredId?: number) {
    if (!token || !isAdmin) return;
    const items = await listAdminRequestTypes(token);
    setTypes(items);
    const nextId = preferredId ?? selectedId ?? items[0]?.id ?? null;
    setSelectedId(nextId);
    if (nextId) setVersions(await listAdminRequestTypeVersions(token, nextId));
  }

  useEffect(() => {
    if (!token || !isAdmin) return;
    void loadTypes().catch((cause) => setError(cause instanceof Error ? cause.message : "Could not load admin catalog."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, isAdmin]);

  useEffect(() => {
    if (!token || !isAdmin || !selectedId) return;
    void listAdminRequestTypeVersions(token, selectedId)
      .then(setVersions)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Could not load versions."));
  }, [token, isAdmin, selectedId]);

  useEffect(() => {
    if (!draftVersion) return;
    setNewTitle(draftVersion.title);
    setNewDescription(draftVersion.description ?? "");
    setSchemaText(JSON.stringify(draftVersion.form_schema, null, 2));
  }, [draftVersion]);

  async function run(action: () => Promise<void>) {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      await action();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Admin action failed.");
    } finally {
      setLoading(false);
    }
  }

  async function createType(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const created = await createAdminRequestType(token, {
        code: code.trim().toUpperCase(),
        category: category.trim(),
        is_active: true,
      });
      setCode("");
      setCategory("");
      setMessage(`Created ${created.code}. Add a draft version before publishing.`);
      await loadTypes(created.id);
    });
  }

  async function toggleActive() {
    if (!selected) return;
    await run(async () => {
      await updateAdminRequestType(token, selected.id, { is_active: !selected.is_active });
      setMessage(`${selected.code} is now ${selected.is_active ? "inactive" : "active"}.`);
      await loadTypes(selected.id);
    });
  }

  function parsedSchema() {
    const value = JSON.parse(schemaText) as Record<string, unknown>;
    if (!value.sections || !Array.isArray(value.sections)) {
      throw new Error("Form schema must contain a sections array.");
    }
    return value;
  }

  async function createDraft() {
    if (!selected) return;
    await run(async () => {
      const created = await createAdminRequestTypeVersion(token, selected.id, {
        title: newTitle.trim(),
        description: newDescription.trim() || null,
        form_schema: parsedSchema(),
      });
      setMessage(`Created immutable candidate v${created.version} as DRAFT.`);
      setVersions(await listAdminRequestTypeVersions(token, selected.id));
    });
  }

  async function saveDraft() {
    if (!selected || !draftVersion) return;
    await run(async () => {
      await updateAdminRequestTypeVersion(token, selected.id, draftVersion.version, {
        title: newTitle.trim(),
        description: newDescription.trim() || null,
        form_schema: parsedSchema(),
      });
      setMessage(`Saved draft v${draftVersion.version}. Published history remains unchanged.`);
      setVersions(await listAdminRequestTypeVersions(token, selected.id));
    });
  }

  async function publishDraft() {
    if (!selected || !draftVersion) return;
    if (!window.confirm(`Publish ${selected.code} v${draftVersion.version}? Previous published versions will be retired and remain immutable.`)) return;
    await run(async () => {
      await publishAdminRequestTypeVersion(token, selected.id, draftVersion.version);
      setMessage(`Published ${selected.code} v${draftVersion.version}. Existing submitted requests keep their original version snapshot.`);
      setVersions(await listAdminRequestTypeVersions(token, selected.id));
    });
  }

  if (!session) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50 p-6">
        <div className="max-w-lg rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
          <ShieldCheck className="mx-auto size-8 text-slate-500" />
          <h1 className="mt-3 text-xl font-semibold">Admin configuration</h1>
          <p className="mt-2 text-sm text-slate-600">Sign in through the main workspace before opening this page.</p>
          <Button asChild className="mt-4"><Link href="/">Back to workspace</Link></Button>
        </div>
      </main>
    );
  }

  if (!isAdmin) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50 p-6">
        <div className="max-w-lg rounded-2xl border border-rose-200 bg-white p-6 text-center shadow-sm">
          <ShieldCheck className="mx-auto size-8 text-rose-600" />
          <h1 className="mt-3 text-xl font-semibold">Administrator access required</h1>
          <p className="mt-2 text-sm text-slate-600">Frontend gating is convenience only; the API also enforces ADMIN authorization.</p>
          <Button asChild variant="outline" className="mt-4"><Link href="/">Back to workspace</Link></Button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 md:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-blue-700">CentralOps AI · Admin</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight">Request type configuration</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Create logical request types, prepare editable draft versions, and publish immutable versions. Submitted requests continue using the version captured at submission time.
            </p>
          </div>
          <Button asChild variant="outline"><Link href="/"><ArrowLeft />Workspace</Link></Button>
        </header>

        <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="space-y-5">
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-center gap-2"><FilePlus2 className="size-4 text-blue-600" /><h2 className="font-semibold">New request type</h2></div>
              <form onSubmit={createType} className="mt-4 grid gap-3">
                <label className="grid gap-1.5 text-sm font-medium">Code<Input value={code} onChange={(event) => setCode(event.target.value)} placeholder="IT_SOFTWARE_ACCESS" required /></label>
                <label className="grid gap-1.5 text-sm font-medium">Category<Input value={category} onChange={(event) => setCategory(event.target.value)} placeholder="IT" required /></label>
                <Button type="submit" disabled={loading}>Create type</Button>
              </form>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
              <h2 className="px-2 py-2 text-sm font-semibold">All logical request types</h2>
              <div className="grid gap-1">
                {types.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setSelectedId(item.id)}
                    className={`rounded-xl border px-3 py-3 text-left transition ${selectedId === item.id ? "border-blue-200 bg-blue-50" : "border-transparent hover:bg-slate-50"}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-semibold">{item.code}</span>
                      <Badge variant="outline">{item.is_active ? "Active" : "Inactive"}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{item.category}</p>
                  </button>
                ))}
              </div>
            </section>
          </aside>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            {selected ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
                  <div>
                    <div className="flex items-center gap-2"><Settings2 className="size-5 text-violet-600" /><h2 className="text-lg font-semibold">{selected.code}</h2></div>
                    <p className="mt-1 text-sm text-slate-500">Category: {selected.category} · Owner team ID: {selected.owner_service_team_id ?? "unassigned"}</p>
                  </div>
                  <Button type="button" variant="outline" onClick={toggleActive} disabled={loading}>{selected.is_active ? "Deactivate" : "Activate"}</Button>
                </div>

                <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_260px]">
                  <div className="space-y-4">
                    <label className="grid gap-1.5 text-sm font-medium">Version title<Input value={newTitle} onChange={(event) => setNewTitle(event.target.value)} placeholder="Software access request" /></label>
                    <label className="grid gap-1.5 text-sm font-medium">Description<Textarea value={newDescription} onChange={(event) => setNewDescription(event.target.value)} className="min-h-24" /></label>
                    <label className="grid gap-1.5 text-sm font-medium">Dynamic form schema JSON<Textarea value={schemaText} onChange={(event) => setSchemaText(event.target.value)} className="min-h-[420px] font-mono text-xs" spellCheck={false} /></label>
                    <div className="flex flex-wrap gap-2">
                      {draftVersion ? (
                        <>
                          <Button type="button" variant="outline" onClick={saveDraft} disabled={loading || !newTitle.trim()}><Save />Save draft v{draftVersion.version}</Button>
                          <Button type="button" onClick={publishDraft} disabled={loading || !newTitle.trim()}><Send />Publish v{draftVersion.version}</Button>
                        </>
                      ) : (
                        <Button type="button" onClick={createDraft} disabled={loading || !newTitle.trim()}><FilePlus2 />Create next draft version</Button>
                      )}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold">Version history</h3>
                    <div className="mt-3 grid gap-2">
                      {[...versions].reverse().map((version) => (
                        <article key={version.id} className="rounded-xl border border-slate-200 p-3">
                          <div className="flex items-center justify-between gap-2">
                            <strong className="text-sm">v{version.version}</strong>
                            <Badge variant="outline">{version.status}</Badge>
                          </div>
                          <p className="mt-1 text-sm text-slate-700">{version.title}</p>
                          <p className="mt-1 text-xs text-slate-500">{version.published_at ? `Published ${new Date(version.published_at).toLocaleString()}` : "Editable draft"}</p>
                        </article>
                      ))}
                      {!versions.length ? <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-500">No versions yet.</p> : null}
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="grid min-h-[420px] place-items-center text-center text-sm text-slate-500">Create or select a request type to configure its versions.</div>
            )}
          </section>
        </div>

        {message ? <p role="status" className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p> : null}
        {error ? <p role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p> : null}
      </div>
    </main>
  );
}
