"use client";

import { useEffect, useState } from "react";

import { ServiceQueue } from "../../components/fulfillment/service-queue";
import {
  ApiError,
  getCurrentUser,
  refreshSession,
  type ApiUser,
} from "../../lib/api";
import {
  clearSession,
  getStoredSession,
  saveSession,
  userHasAnyRole,
  type StoredSession,
} from "../../lib/auth";

export default function ServiceQueuePage() {
  const [session, setSession] = useState<StoredSession | null>(null);
  const [user, setUser] = useState<ApiUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = getStoredSession();
    if (!stored) {
      const timer = window.setTimeout(() => setReady(true), 0);
      return () => window.clearTimeout(timer);
    }
    let cancelled = false;
    async function restore() {
      try {
        const current = await getCurrentUser(stored.accessToken);
        if (!cancelled) {
          const next = { ...stored, user: current };
          saveSession(next);
          setSession(next);
          setUser(current);
        }
      } catch {
        try {
          const rotated = await refreshSession(stored.refreshToken);
          if (!cancelled) {
            const next = {
              accessToken: rotated.access_token,
              refreshToken: rotated.refresh_token,
              user: rotated.user,
            };
            saveSession(next);
            setSession(next);
            setUser(rotated.user);
          }
        } catch {
          clearSession();
        }
      } finally {
        if (!cancelled) setReady(true);
      }
    }
    void restore();
    return () => { cancelled = true; };
  }, []);

  async function request<T>(operation: (accessToken: string) => Promise<T>): Promise<T> {
    if (!session) throw new Error("Sign in again before opening the service queue.");
    try {
      return await operation(session.accessToken);
    } catch (cause) {
      if (!(cause instanceof ApiError) || cause.status !== 401) throw cause;
      const rotated = await refreshSession(session.refreshToken);
      const next = {
        accessToken: rotated.access_token,
        refreshToken: rotated.refresh_token,
        user: rotated.user,
      };
      saveSession(next);
      setSession(next);
      setUser(rotated.user);
      return operation(rotated.access_token);
    }
  }

  if (!ready) return <main className="grid min-h-screen place-items-center bg-slate-50 text-sm text-slate-500">Restoring service session...</main>;
  if (!session || !user) return <main className="grid min-h-screen place-items-center bg-slate-50 p-6"><div className="max-w-md rounded-2xl border border-slate-200 bg-white p-6 text-center"><h1 className="text-xl font-semibold">Sign in required</h1><p className="mt-2 text-sm text-slate-600">Open the main CentralOps workspace, sign in, then return to the service queue.</p><a href="/" className="mt-4 inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white">Back to workspace</a></div></main>;

  const allowed = userHasAnyRole(user, "SERVICE_AGENT", "SERVICE_LEAD", "ADMIN");
  return <main className="min-h-screen bg-slate-50">
    <header className="border-b border-slate-200 bg-white px-5 py-4">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
        <div><p className="text-xs font-semibold uppercase tracking-wide text-blue-700">CentralOps AI</p><h1 className="mt-1 text-2xl font-semibold text-slate-950">Service fulfillment</h1><p className="mt-1 text-sm text-slate-500">Approval and service work remain separate governed lifecycles.</p></div>
        <a href="/" className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700">Back to workspace</a>
      </div>
    </header>
    <div className="mx-auto max-w-7xl p-5 md:p-7">
      <div className="mb-5 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600"><strong className="text-slate-900">Signed in:</strong> {user.full_name} / {user.roles.join(" · ") || user.role}</div>
      {allowed ? <ServiceQueue request={request} /> : <div role="alert" className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900"><h2 className="font-semibold">Service queue access is restricted</h2><p className="mt-2">Only authorized service-team agents, service leads and administrators can open operational work. Approval roles alone do not grant fulfillment access.</p></div>}
    </div>
  </main>;
}
