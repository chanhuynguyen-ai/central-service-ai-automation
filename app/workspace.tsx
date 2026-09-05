"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, BarChart3, Bell, Bot, CheckCircle2, ChevronRight, CircleGauge,
  Clock3, FileText, Inbox, LayoutDashboard, LogOut, Menu, Plus, Search, Send,
  Settings, ShieldCheck, Sparkles, Workflow, X,
} from "lucide-react";
import { WorkflowWorkspace } from "@/components/workflows/workflow-workspace";
import { CatalogWorkspace } from "@/components/catalog/catalog-workspace";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader,
  DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  ApiError,
  ApiServiceRequest,
  ApiUser,
  TokenResponse,
  apiConfigured,
  askPolicyAssistant,
  createRequest as createApiRequest,
  getAnalytics,
  getCurrentUser,
  listRequests,
  login,
  logoutSession,
  refreshSession,
} from "@/lib/api";
import {
  clearSession,
  getStoredSession,
  saveSession,
  userHasAnyRole,
} from "@/lib/auth";

type RequestStatus = "Pending approval" | "In progress" | "Completed" | "Rejected";
type Priority = "Low" | "Medium" | "High" | "Urgent";

type ServiceRequest = {
  id: string;
  title: string;
  requester: string;
  department: string;
  category: string;
  priority: Priority;
  status: RequestStatus;
  submitted: string;
  aiConfidence: number;
};

type RequestDraft = {
  title: string;
  description: string;
  category: string;
  priority: Priority;
};

function mapApiRequest(request: ApiServiceRequest): ServiceRequest {
  return {
    id: request.reference,
    title: request.title,
    requester: request.requester.full_name,
    department: request.department,
    category: request.category.replaceAll("_", " "),
    priority: `${request.priority.charAt(0).toUpperCase()}${request.priority.slice(1)}` as Priority,
    status: ({
      pending_approval: "Pending approval",
      in_progress: "In progress",
      completed: "Completed",
      rejected: "Rejected",
    }[request.status] ?? "In progress") as RequestStatus,
    submitted: new Date(request.submitted_at).toLocaleDateString(),
    aiConfidence: Math.round((request.ai_confidence ?? 0) * 100),
  };
}

const initialRequests: ServiceRequest[] = [
  { id: "CSR-1048", title: "VPN access for new finance analyst", requester: "Linh Tran", department: "Finance", category: "Access request", priority: "High", status: "Pending approval", submitted: "12 min ago", aiConfidence: 96 },
  { id: "CSR-1047", title: "Replace damaged barcode scanner", requester: "Minh Nguyen", department: "Warehouse", category: "IT support", priority: "High", status: "In progress", submitted: "38 min ago", aiConfidence: 91 },
  { id: "CSR-1046", title: "Update payroll bank information", requester: "An Pham", department: "Sales", category: "HR support", priority: "Medium", status: "Completed", submitted: "2 hr ago", aiConfidence: 94 },
  { id: "CSR-1045", title: "Air conditioning issue - meeting room 4B", requester: "Mai Ho", department: "Operations", category: "Facility", priority: "Medium", status: "In progress", submitted: "3 hr ago", aiConfidence: 89 },
  { id: "CSR-1044", title: "Purchase approval for team headsets", requester: "Quang Le", department: "Customer Service", category: "Procurement", priority: "Low", status: "Rejected", submitted: "Yesterday", aiConfidence: 93 },
];

const nav: Array<{
  label: string;
  icon: typeof Inbox;
  roles?: string[];
}> = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Service catalog", icon: FileText },
  { label: "Submitted requests", icon: FileText },
  { label: "My drafts", icon: FileText },
  { label: "Requests", icon: Inbox },
  { label: "Approvals", icon: CheckCircle2, roles: ["APPROVER", "ADMIN"] },
  { label: "AI assistant", icon: Bot },
  { label: "Analytics", icon: BarChart3, roles: ["APPROVER", "ADMIN"] },
  { label: "Automation", icon: Workflow, roles: ["APPROVER", "ADMIN"] },
];

const statusStyles: Record<RequestStatus, string> = {
  "Pending approval": "border-amber-200 bg-amber-50 text-amber-700",
  "In progress": "border-blue-200 bg-blue-50 text-blue-700",
  Completed: "border-emerald-200 bg-emerald-50 text-emerald-700",
  Rejected: "border-rose-200 bg-rose-50 text-rose-700",
};

const priorityStyles: Record<Priority, string> = {
  Low: "text-slate-500", Medium: "text-blue-700", High: "text-orange-700", Urgent: "text-rose-700",
};

function Logo() {
  return (
    <div className="flex items-center gap-3">
      <div className="grid size-10 place-items-center rounded-xl bg-blue-600 text-white shadow-lg shadow-blue-950/20"><Workflow className="size-5" /></div>
      <div><p className="text-[17px] font-semibold tracking-tight text-white">CentralOps AI</p><p className="text-xs text-slate-400">Service automation</p></div>
    </div>
  );
}

function MetricCard({ label, value, note, icon: Icon, tone }: { label: string; value: string; note: string; icon: typeof Inbox; tone: string }) {
  return (
    <article className="enter rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(16,24,40,0.04)]">
      <div className="flex items-start justify-between gap-3"><div><p className="text-sm font-medium text-slate-500">{label}</p><p className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">{value}</p></div><div className={`grid size-10 place-items-center rounded-xl ${tone}`}><Icon className="size-5" /></div></div>
      <p className="mt-3 text-sm text-slate-500">{note}</p>
    </article>
  );
}

function NewRequestDialog({ onCreate }: { onCreate: (request: RequestDraft) => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("IT support");
  const [priority, setPriority] = useState<Priority>("Medium");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim() || !description.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await onCreate({ title: title.trim(), description: description.trim(), category, priority });
      setTitle(""); setDescription(""); setOpen(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not create request");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button className="h-10 rounded-lg bg-blue-600 px-4 hover:bg-blue-700"><Plus />New request</Button></DialogTrigger>
      <DialogContent className="sm:max-w-[580px]">
        <form onSubmit={submit}>
          <DialogHeader><DialogTitle>Legacy prototype request</DialogTitle><DialogDescription>This earlier intake path does not use versioned workflow tasks. Use Service catalog for governed approval.</DialogDescription></DialogHeader>
          <div className="grid gap-4 py-5">
            <label className="grid gap-2 text-sm font-medium text-slate-700">Request title<Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="What do you need help with?" required /></label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-2 text-sm font-medium text-slate-700">Category<Select value={category} onValueChange={setCategory}><SelectTrigger className="w-full"><SelectValue /></SelectTrigger><SelectContent>{["IT support", "Access request", "HR support", "Facility", "Procurement"].map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></label>
              <label className="grid gap-2 text-sm font-medium text-slate-700">Priority<Select value={priority} onValueChange={(value) => setPriority(value as Priority)}><SelectTrigger className="w-full"><SelectValue /></SelectTrigger><SelectContent>{(["Low", "Medium", "High", "Urgent"] as Priority[]).map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></label>
            </div>
            <label className="grid gap-2 text-sm font-medium text-slate-700">Description<Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Add context, expected outcome, and any relevant deadline." className="min-h-28" required /></label>
            <div className="flex items-start gap-3 rounded-xl border border-blue-100 bg-blue-50 p-3 text-sm text-blue-800"><Sparkles className="mt-0.5 size-4 shrink-0" /><p>The AI triage service analyzes category, urgency, routing, and a concise summary. A human remains responsible for the approval decision.</p></div>
            {error ? <p className="text-sm font-medium text-rose-700">{error}</p> : null}
          </div>
          <DialogFooter><Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" disabled={submitting} className="bg-blue-600 hover:bg-blue-700">{submitting ? "Running AI triage..." : "Submit request"}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function LoginScreen({ onAuthenticated }: { onAuthenticated: (result: TokenResponse) => void }) {
  const [email, setEmail] = useState("admin@centralops.demo");
  const [password, setPassword] = useState("Admin123!");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await login(email, password);
      onAuthenticated(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Sign in failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#071426] p-5">
      <div className="w-full max-w-md rounded-3xl border border-slate-700 bg-white p-7 shadow-2xl shadow-black/25">
        <div className="mb-7 flex items-center gap-3">
          <div className="grid size-11 place-items-center rounded-xl bg-blue-600 text-white"><Workflow className="size-5" /></div>
          <div><p className="text-lg font-semibold text-slate-950">CentralOps AI</p><p className="text-sm text-slate-500">Secure service workspace</p></div>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-950">Sign in</h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">Use a seeded demo account to test employee, approver, and admin permissions.</p>
        <form onSubmit={submit} className="mt-6 grid gap-4">
          <label className="grid gap-2 text-sm font-medium text-slate-700">Email<Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <label className="grid gap-2 text-sm font-medium text-slate-700">Password<Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          {error ? <p className="text-sm font-medium text-rose-700">{error}</p> : null}
          <Button type="submit" disabled={loading} className="mt-1 h-11 bg-blue-600 hover:bg-blue-700">{loading ? "Signing in..." : "Sign in to workspace"}</Button>
        </form>
        <div className="mt-6 rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-500"><strong className="text-slate-700">Demo:</strong> admin@centralops.demo / Admin123!</div>
      </div>
    </main>
  );
}

export default function Workspace() {
  const [activeNav, setActiveNav] = useState("Overview");
  const [selectedSubmission, setSelectedSubmission] = useState<number | null>(null);
  const beforeLeaveCatalog = useRef<() => boolean>(() => true);
  const [mobileNav, setMobileNav] = useState(false);
  const [requests, setRequests] = useState<ServiceRequest[]>(apiConfigured ? [] : initialRequests);
  const [query, setQuery] = useState("");
  const [assistantInput, setAssistantInput] = useState("");
  const [assistantReply, setAssistantReply] = useState("I can explain policies, help classify a request, or show you where it is in the approval process.");
  const [token, setToken] = useState("");
  const [refreshToken, setRefreshToken] = useState("");
  const [currentUser, setCurrentUser] = useState<ApiUser | null>(null);
  const [sessionReady, setSessionReady] = useState(!apiConfigured);
  const [workspaceLoading, setWorkspaceLoading] = useState(apiConfigured);
  const [workspaceError, setWorkspaceError] = useState("");
  const [reloadNonce, setReloadNonce] = useState(0);
  const [metrics, setMetrics] = useState(apiConfigured
    ? { open: 0, pending: 0, sla: 0, automation: 0, triage: 0 }
    : { open: 12, pending: 4, sla: 94.2, automation: 99.7, triage: 92.8 });

  function applySession(result: TokenResponse) {
    saveSession({
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
      user: result.user,
    });
    setToken(result.access_token);
    setRefreshToken(result.refresh_token);
    setCurrentUser(result.user);
  }

  function resetSession() {
    clearSession();
    setToken("");
    setRefreshToken("");
    setCurrentUser(null);
    setSelectedSubmission(null);
    setActiveNav("Overview");
  }

  useEffect(() => {
    if (!apiConfigured) return;

    const stored = getStoredSession();
    if (!stored) {
      const timer = window.setTimeout(() => setSessionReady(true), 0);
      return () => window.clearTimeout(timer);
    }

    const storedSession = stored;

    async function restoreSession() {
      try {
        const user = await getCurrentUser(storedSession.accessToken);
        setToken(storedSession.accessToken);
        setRefreshToken(storedSession.refreshToken);
        setCurrentUser(user);
        saveSession({ ...storedSession, user });
      } catch {
        try {
          const rotated = await refreshSession(storedSession.refreshToken);
          applySession(rotated);
        } catch {
          resetSession();
        }
      } finally {
        setSessionReady(true);
      }
    }

    void restoreSession();
  }, []);

  useEffect(() => {
    if (!apiConfigured || !token || !currentUser) return;

    async function loadWorkspace() {
      setWorkspaceLoading(true);
      setWorkspaceError("");
      try {
        const requestResult = await listRequests(token);
        const mappedRequests = requestResult.items.map(mapApiRequest);
        setRequests(mappedRequests);

        if (userHasAnyRole(currentUser, "APPROVER", "ADMIN")) {
          const analytics = await getAnalytics(token);
          setMetrics({
            open: analytics.open_requests,
            pending: analytics.pending_approvals,
            sla: analytics.sla_compliance_rate,
            automation: analytics.automation_success_rate,
            triage: analytics.ai_triage_coverage,
          });
        } else {
          setMetrics((current) => ({
            ...current,
            open: mappedRequests.filter((request) => request.status !== "Completed" && request.status !== "Rejected").length,
            pending: mappedRequests.filter((request) => request.status === "Pending approval").length,
          }));
        }
      } catch (cause) {
        if (cause instanceof ApiError && cause.status === 401 && refreshToken) {
          try {
            const rotated = await refreshSession(refreshToken);
            applySession(rotated);
            return;
          } catch {
            resetSession();
          }
        } else {
          setRequests([]);
          setWorkspaceError(cause instanceof Error
            ? cause.message
            : "Could not load live workspace data.");
        }
      } finally {
        setWorkspaceLoading(false);
      }
    }

    void loadWorkspace();
  }, [token, refreshToken, currentUser, reloadNonce]);

  const visibleNav = useMemo(
    () => nav.filter((item) => !item.roles || userHasAnyRole(currentUser, ...item.roles)),
    [currentUser],
  );

  useEffect(() => {
    if (visibleNav.some((item) => item.label === activeNav)) return;
    const timer = window.setTimeout(() => setActiveNav("Overview"), 0);
    return () => window.clearTimeout(timer);
  }, [activeNav, visibleNav]);

  async function withSessionRefresh<T>(operation: (accessToken: string) => Promise<T>): Promise<T> {
    try {
      return await operation(token);
    } catch (cause) {
      if (!(cause instanceof ApiError) || cause.status !== 401 || !refreshToken) throw cause;
      const rotated = await refreshSession(refreshToken);
      applySession(rotated);
      return operation(rotated.access_token);
    }
  }

  async function handleLogout() {
    if (!beforeLeaveCatalog.current()) return;
    if (refreshToken) {
      try {
        await logoutSession(refreshToken);
      } catch {
        // Local logout must still succeed if the server session is already expired/revoked.
      }
    }
    resetSession();
  }

  const filteredRequests = useMemo(() => requests.filter((request) =>
    `${request.id} ${request.title} ${request.requester} ${request.department}`.toLowerCase().includes(query.toLowerCase())
  ), [requests, query]);
  const visibleRequests = activeNav === "Approvals"
    ? filteredRequests.filter((request) => request.status === "Pending approval")
    : filteredRequests;
  const canViewOperationalAnalytics = !apiConfigured
    || userHasAnyRole(currentUser, "APPROVER", "ADMIN");
  const connectionStatus = workspaceError
    ? { label: "API unavailable", style: "border-rose-200 bg-rose-50 text-rose-700", dot: "bg-rose-500" }
    : workspaceLoading
      ? { label: "Syncing live data", style: "border-amber-200 bg-amber-50 text-amber-700", dot: "bg-amber-500" }
      : apiConfigured
        ? { label: "Connected to API", style: "border-emerald-200 bg-emerald-50 text-emerald-700", dot: "bg-emerald-500" }
        : { label: "Interactive demo", style: "border-blue-200 bg-blue-50 text-blue-700", dot: "bg-blue-500" };
  const today = useMemo(
    () => new Intl.DateTimeFormat("en", { weekday: "long", day: "numeric", month: "long" }).format(new Date()),
    [],
  );
  const pageCopy: Record<string, { title: string; description: string }> = {
    Overview: { title: "Service operations overview", description: "Monitor requests, approvals, SLA performance, and AI automation." },
    "Service catalog": { title: "Service catalog", description: "Choose a service and create a private, structured draft." },
    "My drafts": { title: "My drafts", description: "Continue editing your saved requests. A draft is not yet submitted for approval." },
    Requests: { title: "Legacy service requests", description: "Earlier prototype requests. Use Service catalog and Submitted requests for versioned approval workflows." },
    Approvals: { title: "Assigned approval tasks", description: "Review submitted information and record decisions on tasks assigned to you." },
    "Submitted requests": { title: "Submitted requests", description: "Follow the recorded approval chain and review feedback on your submissions." },
    "AI assistant": { title: "Policy assistant", description: "Ask grounded questions about policies, routing, and request status." },
    Analytics: { title: "Service analytics", description: "Track demand, SLA compliance, and AI triage coverage." },
    Automation: { title: "Automation monitoring", description: "Review workflow health, run volume, and recoverable failures." },
  };

  async function handleCreate(draft: RequestDraft) {
    if (apiConfigured && token) {
      const created = await withSessionRefresh((accessToken) => createApiRequest(accessToken, {
        ...draft,
        category: draft.category.toLowerCase().replaceAll(" ", "_"),
        priority: draft.priority.toLowerCase(),
      }));
      setRequests((current) => [mapApiRequest(created), ...current]);
      setMetrics((current) => ({ ...current, open: current.open + 1, pending: current.pending + 1 }));
      return;
    }
    setRequests((current) => [{
      id: `CSR-${1049 + Math.floor(Math.random() * 40)}`,
      title: draft.title,
      requester: "Nguyen Chan Huy",
      department: "Technology",
      category: draft.category,
      priority: draft.priority,
      status: "Pending approval",
      submitted: "Just now",
      aiConfidence: 92,
    }, ...current]);
  }

  async function askAssistant(event: FormEvent) {
    event.preventDefault();
    const text = assistantInput.toLowerCase();
    if (!text.trim()) return;
    setAssistantInput("");
    if (apiConfigured && token) {
      try {
        const reference = text.match(/csr-\d+/i)?.[0].toUpperCase();
        const result = await withSessionRefresh((accessToken) =>
          askPolicyAssistant(accessToken, text, reference),
        );
        setAssistantReply(result.answer);
        return;
      } catch (cause) {
        setAssistantReply(cause instanceof Error ? cause.message : "The assistant is unavailable.");
        return;
      }
    }
    if (text.includes("urgent") || text.includes("priority")) setAssistantReply("Mark a request as urgent only when work is blocked, a security risk exists, or a critical customer operation is affected. The on-call service owner will be notified.");
    else if (text.includes("status") || text.includes("csr-")) setAssistantReply("CSR-1048 is waiting for the Finance Systems Owner. It was routed automatically with 96% confidence and remains within its four-hour SLA.");
    else setAssistantReply("Include the affected service, business impact, desired outcome, and deadline. I will use those details to recommend a category and approval route.");
  }

  if (apiConfigured && !sessionReady) {
    return <main className="grid min-h-screen place-items-center bg-[#071426] text-sm font-medium text-slate-200">Restoring secure session...</main>;
  }
  if (apiConfigured && (!token || !currentUser)) return <LoginScreen onAuthenticated={applySession} />;

  return (
    <div className="min-h-screen bg-transparent lg:grid lg:grid-cols-[252px_minmax(0,1fr)]">
      {mobileNav && <button className="fixed inset-0 z-30 bg-slate-950/45 lg:hidden" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-[252px] flex-col bg-[#071426] px-4 py-5 transition-transform lg:sticky lg:top-0 lg:h-screen ${mobileNav ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}>
        <div className="flex items-center justify-between px-2"><Logo /><Button variant="ghost" size="icon-sm" className="text-slate-300 lg:hidden" onClick={() => setMobileNav(false)}><X /></Button></div>
        <nav className="mt-9 space-y-1" aria-label="Primary navigation">
          {visibleNav.map(({ label, icon: Icon }) => {
            const count = label === "Requests"
              ? requests.length
              : 0;
            return <button key={label} onClick={() => { if (!beforeLeaveCatalog.current()) return; setActiveNav(label); setMobileNav(false); }} className={`flex h-11 w-full items-center gap-3 rounded-xl px-3 text-left text-sm font-medium transition ${activeNav === label ? "bg-blue-600 text-white shadow-lg shadow-blue-950/20" : "text-slate-300 hover:bg-slate-800/80 hover:text-white"}`}><Icon className="size-[18px]" /><span className="flex-1">{label}</span>{count > 0 ? <span className={`rounded-full px-2 py-0.5 text-xs ${activeNav === label ? "bg-white/15 text-white" : "bg-slate-800 text-slate-300"}`}>{count}</span> : null}</button>;
          })}
        </nav>
        <div className="mt-auto rounded-2xl border border-slate-700/60 bg-slate-900/60 p-4"><div className="flex items-center gap-2 text-sm font-medium text-white"><ShieldCheck className="size-4 text-emerald-400" />Responsible AI</div><p className="mt-2 text-xs leading-5 text-slate-400">AI recommends routing and summaries. People own approval decisions.</p></div>
        {apiConfigured ? <button onClick={() => void handleLogout()} className="mt-3 flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-slate-300 hover:bg-slate-800"><LogOut className="size-[18px]" />Sign out</button> : <button className="mt-3 flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-slate-300 hover:bg-slate-800"><Settings className="size-[18px]" />Settings</button>}
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur md:px-7">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileNav(true)}><Menu /></Button>
          <div className="relative hidden max-w-md flex-1 md:block"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search requests, people, or IDs" className="h-10 border-slate-200 bg-slate-50 pl-9 shadow-none" /></div>
          <div className="ml-auto flex items-center gap-2"><div className={`hidden items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium sm:flex ${connectionStatus.style}`}><span className={`size-1.5 rounded-full ${connectionStatus.dot}`} />{connectionStatus.label}</div><Button variant="ghost" size="icon" className="relative"><Bell /><span className="absolute right-2 top-2 size-1.5 rounded-full bg-blue-600" /><span className="sr-only">Notifications</span></Button><div className="ml-1 flex items-center gap-2 border-l border-slate-200 pl-3"><div className="grid size-9 place-items-center rounded-full bg-slate-900 text-sm font-semibold text-white">{currentUser?.full_name.split(/\s+/).map((part) => part[0]).slice(-2).join("").toUpperCase() ?? "CO"}</div><div className="hidden sm:block"><p className="text-sm font-semibold text-slate-800">{currentUser?.full_name ?? "CentralOps User"}</p><p className="text-xs text-slate-500">{currentUser?.roles.join(" · ") || currentUser?.role || "Demo workspace"}</p></div></div></div>
        </header>

        <main className="mx-auto max-w-[1500px] p-4 md:p-7">
          <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-sm font-medium text-blue-700">{today}</p><h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950 md:text-[30px]">{pageCopy[activeNav].title}</h1><p className="mt-1 text-sm text-slate-500">{pageCopy[activeNav].description}</p></div>{activeNav === "Overview" && apiConfigured ? <Button className="bg-blue-600 hover:bg-blue-700" onClick={() => setActiveNav("Service catalog")}>New structured request</Button> : ["Overview", "Requests"].includes(activeNav) ? <NewRequestDialog onCreate={handleCreate} /> : null}</section>

          {["Submitted requests", "Approvals"].includes(activeNav) ? (apiConfigured && currentUser
            ? <WorkflowWorkspace key={`${currentUser.id}-${activeNav}`} mode={activeNav === "Approvals" ? "approvals" : "submissions"} request={withSessionRefresh} currentUserId={currentUser.id} initialRequestId={activeNav === "Submitted requests" ? selectedSubmission : null} onEditChanges={() => setActiveNav("My drafts")} />
            : <p className="mt-6 rounded-xl border bg-white p-6 text-sm">Connect to the API and sign in to use real approval workflows.</p>) : null}
          {["Service catalog", "My drafts"].includes(activeNav) ? (apiConfigured && currentUser
            ? <CatalogWorkspace key={`${currentUser.id}-${activeNav}`} mode={activeNav === "My drafts" ? "drafts" : "catalog"} request={withSessionRefresh} beforeLeave={beforeLeaveCatalog} onBrowse={() => setActiveNav("Service catalog")} onSubmitted={(id) => { setSelectedSubmission(id); setActiveNav("Submitted requests"); }} />
            : <p className="mt-6 rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">Connect the backend and sign in to use the live service catalog. Demo mode does not save drafts.</p>
          ) : null}

          {apiConfigured && ["Overview", "Requests", "Analytics", "Automation"].includes(activeNav) ? <p className="mt-4 rounded-xl border border-blue-100 bg-blue-50 p-3 text-sm text-blue-800">These are legacy prototype metrics and requests. Track catalog-based workflows under Submitted requests and Approvals.</p> : null}

          {workspaceError ? <div role="alert" className="mt-5 flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-semibold">Live data could not be loaded</p><p className="mt-1 text-rose-700">{workspaceError}. No demo records are shown while the API is configured.</p></div><Button type="button" variant="outline" className="border-rose-300 bg-white text-rose-800 hover:bg-rose-100" onClick={() => setReloadNonce((value) => value + 1)}>Try again</Button></div> : null}

          {["Overview", "Analytics", "Automation"].includes(activeNav) ? <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard label={canViewOperationalAnalytics ? "Open requests" : "My open requests"} value={workspaceLoading ? "—" : String(metrics.open)} note="Active request workload" icon={Inbox} tone="bg-blue-50 text-blue-700" />
            <MetricCard label={canViewOperationalAnalytics ? "Pending approvals" : "My pending requests"} value={workspaceLoading ? "—" : String(metrics.pending)} note="Awaiting a human decision" icon={Clock3} tone="bg-amber-50 text-amber-700" />
            {canViewOperationalAnalytics ? <MetricCard label="Within SLA" value={workspaceLoading ? "—" : `${metrics.sla}%`} note="Measured against policy targets" icon={CircleGauge} tone="bg-emerald-50 text-emerald-700" /> : null}
            {canViewOperationalAnalytics ? <MetricCard label="AI triage coverage" value={workspaceLoading ? "—" : `${metrics.triage}%`} note="Requests with AI recommendations" icon={Sparkles} tone="bg-violet-50 text-violet-700" /> : null}
          </section> : null}

          {["Overview", "Requests", "AI assistant"].includes(activeNav) ? <section className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.8fr)]">
            {activeNav !== "AI assistant" ? <article className={`enter enter-delay-1 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(16,24,40,0.04)] ${activeNav !== "Overview" ? "xl:col-span-2" : ""}`}>
              <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div><h2 className="font-semibold text-slate-900">{activeNav === "Approvals" ? "Pending approval" : "Recent requests"}</h2><p className="mt-0.5 text-sm text-slate-500">AI-classified and routed service work</p></div>{activeNav === "Overview" ? <Button variant="ghost" size="sm" className="text-blue-700" onClick={() => setActiveNav("Requests")}>View all<ChevronRight /></Button> : null}</div>
              <Table><TableHeader><TableRow className="bg-slate-50/70 hover:bg-slate-50/70"><TableHead className="pl-5 text-xs uppercase tracking-wide text-slate-500">Request</TableHead><TableHead className="text-xs uppercase tracking-wide text-slate-500">Priority</TableHead><TableHead className="text-xs uppercase tracking-wide text-slate-500">Status</TableHead><TableHead className="pr-5 text-right text-xs uppercase tracking-wide text-slate-500">AI confidence</TableHead></TableRow></TableHeader><TableBody>
                {visibleRequests.slice(0, activeNav === "Overview" ? 6 : 50).map((request) => <TableRow key={request.id} className="group cursor-pointer"><TableCell className="max-w-[420px] py-3.5 pl-5"><div className="flex items-start gap-3"><div className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-600"><FileText className="size-4" /></div><div className="min-w-0"><p className="truncate font-medium text-slate-900">{request.title}</p><p className="mt-0.5 text-xs text-slate-500">{request.id} · {request.department} · {request.submitted}</p></div></div></TableCell><TableCell><span className={`text-sm font-medium ${priorityStyles[request.priority]}`}>{request.priority}</span></TableCell><TableCell><Badge variant="outline" className={statusStyles[request.status]}>{request.status}</Badge></TableCell><TableCell className="pr-5 text-right"><span className="font-mono text-xs font-semibold text-slate-600">{request.aiConfidence}%</span></TableCell></TableRow>)}
              </TableBody></Table>{visibleRequests.length === 0 && <div className="px-5 py-14 text-center text-sm text-slate-500">{workspaceLoading ? "Loading live requests..." : workspaceError ? "Live requests are unavailable." : "No requests match this view."}</div>}
            </article> : null}

            {["Overview", "AI assistant"].includes(activeNav) ? <article className={`enter enter-delay-2 flex min-h-[430px] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(16,24,40,0.04)] ${activeNav === "AI assistant" ? "xl:col-span-2" : ""}`}>
              <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4"><div className="grid size-10 place-items-center rounded-xl bg-gradient-to-br from-blue-600 to-violet-600 text-white"><Bot className="size-5" /></div><div><h2 className="font-semibold text-slate-900">Policy assistant</h2><p className="text-xs text-slate-500">Grounded in internal service policies</p></div><Badge className="ml-auto border-emerald-200 bg-emerald-50 text-emerald-700" variant="outline">RAG online</Badge></div>
              <div className="flex-1 space-y-4 bg-slate-50/70 p-5"><div className="flex gap-3"><div className="grid size-8 shrink-0 place-items-center rounded-lg bg-blue-600 text-white"><Bot className="size-4" /></div><div className="rounded-2xl rounded-tl-md border border-slate-200 bg-white p-3.5 text-sm leading-6 text-slate-700 shadow-sm">{assistantReply}<div className="mt-2 flex items-center gap-1 text-xs font-medium text-blue-700"><FileText className="size-3" />Service Request Policy v2.1</div></div></div><div className="grid grid-cols-2 gap-2">{["Check CSR-1048", "When is urgent?"].map((prompt) => <button key={prompt} onClick={() => setAssistantInput(prompt)} className="rounded-xl border border-slate-200 bg-white p-2.5 text-left text-xs font-medium text-slate-600 transition hover:border-blue-300 hover:text-blue-700">{prompt}</button>)}</div></div>
              <form onSubmit={askAssistant} className="flex gap-2 border-t border-slate-100 p-4"><Input value={assistantInput} onChange={(e) => setAssistantInput(e.target.value)} placeholder="Ask about a request or policy..." className="h-10" /><Button type="submit" size="icon" className="size-10 bg-blue-600 hover:bg-blue-700"><Send /><span className="sr-only">Send</span></Button></form>
            </article> : null}
          </section> : null}

          {canViewOperationalAnalytics && ["Overview", "Analytics", "Automation"].includes(activeNav) ? <section className="mt-5 grid gap-5 lg:grid-cols-3">
            <article className="rounded-2xl border border-slate-200 bg-white p-5 lg:col-span-2"><div className="flex items-start justify-between"><div><h2 className="font-semibold text-slate-900">Request volume</h2><p className="mt-1 text-sm text-slate-500">Last seven days by incoming work</p></div><Badge variant="outline">7 days</Badge></div><div className="mt-6 flex h-36 items-end gap-3 sm:gap-5">{[52, 70, 48, 82, 64, 91, 58].map((height, index) => <div key={index} className="flex flex-1 flex-col items-center gap-2"><div className="relative flex h-28 w-full max-w-10 items-end rounded-md bg-slate-100"><div className="w-full rounded-md bg-blue-600 transition-all hover:bg-blue-700" style={{ height: `${height}%` }} /></div><span className="text-xs text-slate-500">{["Fri", "Sat", "Sun", "Mon", "Tue", "Wed", "Thu"][index]}</span></div>)}</div></article>
            <article className="rounded-2xl border border-slate-200 bg-[#0b1930] p-5 text-white"><div className="flex items-center justify-between"><div><h2 className="font-semibold">Automation health</h2><p className="mt-1 text-sm text-slate-400">Past 24 hours</p></div><Activity className="size-5 text-emerald-400" /></div><div className="mt-5 flex items-end gap-3"><span className="text-4xl font-semibold tracking-tight">{metrics.automation}%</span><span className="mb-1 text-sm text-emerald-400">successful</span></div><div className="mt-5 space-y-3 text-sm"><div className="flex justify-between text-slate-300"><span>Approval workflow</span><span className="font-medium text-white">128 runs</span></div><div className="flex justify-between text-slate-300"><span>AI triage</span><span className="font-medium text-white">92 runs</span></div><div className="flex justify-between text-slate-300"><span>Notifications</span><span className="font-medium text-white">214 sent</span></div></div></article>
          </section> : null}
        </main>
      </div>
    </div>
  );
}
