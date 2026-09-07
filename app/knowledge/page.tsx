"use client";

import { FormEvent, useState, useSyncExternalStore } from "react";
import { ArrowLeft, Bot, FileText, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { askPolicyAssistant, PolicyAnswer } from "@/lib/api";
import { getStoredSession } from "@/lib/auth";

const INITIAL_MESSAGE =
  "Ask about an internal policy. Answers are generated only from policy evidence you are allowed to access.";

const subscribeSession = () => () => undefined;
const getServerToken = () => "";
const getClientToken = () => getStoredSession()?.accessToken ?? "";

export default function KnowledgePage() {
  const token = useSyncExternalStore(subscribeSession, getClientToken, getServerToken);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<PolicyAnswer | null>(null);
  const [message, setMessage] = useState(INITIAL_MESSAGE);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim() || !token) return;
    setLoading(true);
    setMessage("");
    try {
      const answer = await askPolicyAssistant(token, question.trim());
      setResult(answer);
    } catch (cause) {
      setResult(null);
      setMessage(cause instanceof Error ? cause.message : "The policy assistant is unavailable.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 md:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-teal-700">CentralOps AI · Knowledge</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight">Policy assistant</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              Permission-aware retrieval filters policies by publication state, effective date,
              department, and role before evidence is sent to the model.
            </p>
          </div>
          <Button asChild variant="outline"><Link href="/"><ArrowLeft />Workspace</Link></Button>
        </div>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
            <div className="grid size-10 place-items-center rounded-xl bg-teal-600 text-white"><Bot className="size-5" /></div>
            <div>
              <h2 className="font-semibold">Grounded policy search</h2>
              <p className="text-xs text-slate-500">AI is evidence support, not policy or approval authority.</p>
            </div>
            <span className="ml-auto inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700"><ShieldCheck className="size-3.5" />Permission filtered</span>
          </div>

          <form onSubmit={submit} className="mt-5 flex gap-2">
            <Input
              aria-label="Policy question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about a policy..."
              className="h-11"
            />
            <Button type="submit" disabled={!token || loading} className="h-11 bg-teal-600 hover:bg-teal-700">
              <Sparkles />{loading ? "Searching..." : "Ask policy"}
            </Button>
          </form>

          {!token ? <p role="alert" className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">Sign in through the main workspace before using policy search.</p> : null}
          {message ? <p className="mt-4 text-sm leading-6 text-slate-600">{message}</p> : null}

          {result ? (
            <div className="mt-6 space-y-4">
              {result.insufficient_evidence ? (
                <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                  <p className="font-semibold">Insufficient policy evidence</p>
                  <p className="mt-1 leading-6">{result.answer}</p>
                </div>
              ) : (
                <div className="rounded-xl border border-teal-100 bg-teal-50/50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">Grounded answer</p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-800">{result.answer}</p>
                </div>
              )}

              <div>
                <div className="flex items-center gap-2"><FileText className="size-4 text-slate-500" /><h3 className="text-sm font-semibold">Evidence</h3></div>
                {result.citations.length ? (
                  <div className="mt-2 grid gap-2">
                    {result.citations.map((citation) => (
                      <article key={citation.chunk_id} className="rounded-xl border border-slate-200 bg-white p-3 text-sm">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="font-medium text-slate-900">{citation.title} · v{citation.version}</p>
                          <span className="font-mono text-xs text-slate-500">score {citation.score.toFixed(3)}</span>
                        </div>
                        <p className="mt-1 text-xs text-slate-500">
                          {[citation.source_name, citation.section ? `Section: ${citation.section}` : null, citation.page ? `Page ${citation.page}` : null].filter(Boolean).join(" · ") || "Indexed policy chunk"}
                        </p>
                      </article>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-slate-500">No source was returned because the accessible evidence did not meet the grounding threshold.</p>
                )}
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
