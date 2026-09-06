"use client";

import { Bell, CheckCheck, Loader2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type InAppNotification,
} from "../../lib/notification-api";

type AuthenticatedRequest = <T>(operation: (token: string) => Promise<T>) => Promise<T>;

export function NotificationCenter({ request }: { request: AuthenticatedRequest }) {
  const requestRef = useRef(request);
  useEffect(() => { requestRef.current = request; }, [request]);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<InAppNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const page = await requestRef.current((token) => listNotifications(token));
      setItems(page.items);
      setUnread(page.unread);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Notifications could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void load(); }, 0);
    const interval = window.setInterval(() => { void load(); }, 30000);
    return () => {
      window.clearTimeout(timer);
      window.clearInterval(interval);
    };
  }, [load]);

  async function readOne(item: InAppNotification) {
    if (item.read_at) return;
    const updated = await requestRef.current((token) => markNotificationRead(token, item.id));
    setItems((current) => current.map((row) => row.id === updated.id ? updated : row));
    setUnread((value) => Math.max(0, value - 1));
  }

  async function readAll() {
    await requestRef.current((token) => markAllNotificationsRead(token));
    setItems((current) => current.map((row) => ({
      ...row,
      read_at: row.read_at ?? new Date().toISOString(),
      status: "READ",
    })));
    setUnread(0);
  }

  return <div className="relative">
    <button
      type="button"
      aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
      aria-expanded={open}
      onClick={() => { setOpen((value) => !value); if (!open) void load(); }}
      className="relative grid size-10 place-items-center rounded-lg text-slate-600 hover:bg-slate-100"
    >
      <Bell className="size-5" />
      {unread > 0 ? <span className="absolute right-1 top-1 min-w-4 rounded-full bg-blue-600 px-1 text-[10px] font-semibold leading-4 text-white">{unread > 99 ? "99+" : unread}</span> : null}
    </button>
    {open ? <div className="absolute right-0 top-12 z-50 w-[min(92vw,390px)] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <div><h2 className="text-sm font-semibold text-slate-900">Notifications</h2><p className="text-xs text-slate-500">{unread} unread</p></div>
        <button type="button" disabled={!unread} onClick={() => void readAll()} className="flex items-center gap-1 text-xs font-medium text-blue-700 disabled:opacity-40"><CheckCheck className="size-4" />Mark all read</button>
      </div>
      <div className="max-h-[440px] overflow-y-auto">
        {loading && items.length === 0 ? <div className="grid place-items-center p-8 text-slate-500"><Loader2 className="size-5 animate-spin" /></div> : null}
        {error ? <p role="alert" className="m-3 rounded-lg bg-rose-50 p-3 text-xs text-rose-800">{error}</p> : null}
        {!loading && !error && items.length === 0 ? <p className="p-8 text-center text-sm text-slate-500">No notifications yet.</p> : null}
        {items.map((item) => <button
          key={item.id}
          type="button"
          onClick={() => void readOne(item)}
          className={`block w-full border-b border-slate-100 px-4 py-3 text-left last:border-0 ${item.read_at ? "bg-white" : "bg-blue-50/60"}`}
        >
          <div className="flex items-start gap-3">
            <span className={`mt-1 size-2 shrink-0 rounded-full ${item.read_at ? "bg-slate-200" : "bg-blue-600"}`} />
            <span className="min-w-0"><span className="block text-sm font-semibold text-slate-900">{item.subject}</span><span className="mt-1 block text-xs leading-5 text-slate-600">{item.body}</span><span className="mt-1 block text-[11px] text-slate-400">{new Date(item.created_at).toLocaleString()}</span></span>
          </div>
        </button>)}
      </div>
    </div> : null}
  </div>;
}
