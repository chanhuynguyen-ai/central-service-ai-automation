export type SessionUser = {
  id: number;
  email: string;
  full_name: string;
  department: string;
  role: string;
  roles: string[];
};

export type StoredSession = {
  accessToken: string;
  refreshToken: string;
  user: SessionUser;
};

const ACCESS_TOKEN_KEY = "centralops_access_token";
const REFRESH_TOKEN_KEY = "centralops_refresh_token";
const USER_KEY = "centralops_user";

export function normalizeRole(role: string): string {
  return role.trim().replaceAll("-", "_").replaceAll(" ", "_").toUpperCase();
}

export function userRoleCodes(user: SessionUser | null): Set<string> {
  if (!user) return new Set();
  return new Set([user.role, ...user.roles].filter(Boolean).map(normalizeRole));
}

export function userHasAnyRole(user: SessionUser | null, ...roles: string[]): boolean {
  const actual = userRoleCodes(user);
  return roles.some((role) => actual.has(normalizeRole(role)));
}

export function saveSession(session: StoredSession): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, session.accessToken);
  sessionStorage.setItem(REFRESH_TOKEN_KEY, session.refreshToken);
  sessionStorage.setItem(USER_KEY, JSON.stringify(session.user));
  sessionStorage.removeItem("centralops_token");
}

export function getStoredSession(): StoredSession | null {
  const accessToken = sessionStorage.getItem(ACCESS_TOKEN_KEY);
  const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_KEY);
  const rawUser = sessionStorage.getItem(USER_KEY);
  if (!accessToken || !refreshToken || !rawUser) return null;

  try {
    const user = JSON.parse(rawUser) as SessionUser;
    if (!user.email || !user.full_name) return null;
    return { accessToken, refreshToken, user };
  } catch {
    return null;
  }
}

export function clearSession(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
  sessionStorage.removeItem("centralops_token");
}
