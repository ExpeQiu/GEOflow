/** 浏览器走 Next.js 同源代理 /api → FastAPI，避免跨域与 API 未启动时的错误 URL */
function resolveApiUrl(): string {
  if (typeof window !== "undefined") {
    return "";
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:18081";
}

const API_URL = resolveApiUrl();

export type AdminProfile = { id: number; username: string; name: string; role: string };

export type ApiResponse<T> = {
  success: boolean;
  data: T;
  meta?: { request_id?: string };
  detail?: string | { detail?: string };
};

async function throwApiError(res: Response, path: string): Promise<never> {
  let detail = "";
  try {
    const body = (await res.json()) as { detail?: unknown; message?: string };
    if (typeof body.detail === "string") detail = body.detail;
    else if (body.message) detail = body.message;
    else if (body.detail != null) detail = JSON.stringify(body.detail);
  } catch {
    /* ignore */
  }
  const suffix = detail ? ` · ${detail}` : "";
  throw new Error(`请求失败 ${res.status} (${path})${suffix}`);
}

function authHeaders(token?: string | null): HeadersInit {
  const headers: Record<string, string> = {};
  if (token && token !== COOKIE_AUTH) headers.Authorization = `Bearer ${token}`;
  return headers;
}

/** 同源请求带 Cookie（HttpOnly gf_token）；Bearer 作兼容回退 */
const FETCH_CREDENTIALS: RequestCredentials = "include";

export async function adminLogin(username: string, password: string) {
  const res = await fetch(`${API_URL}/api/v1/auth/admin-login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: FETCH_CREDENTIALS,
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    if (res.status === 429) throw new Error("login_locked");
    throw new Error("login_failed");
  }
  const json = (await res.json()) as ApiResponse<{
    access_token: string;
    admin: AdminProfile;
  }>;
  return json.data;
}

export async function adminLogout(token: string | null) {
  try {
    await fetch(`${API_URL}/api/v1/auth/admin-logout`, {
      method: "POST",
      headers: authHeaders(token),
      credentials: FETCH_CREDENTIALS,
    });
  } catch {
    /* ignore */
  }
}

export async function fetchAdminSession(): Promise<AdminProfile | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/auth/admin-session`, {
      headers: authHeaders(getToken()),
      credentials: FETCH_CREDENTIALS,
      cache: "no-store",
    });
    if (!res.ok) return null;
    const json = (await res.json()) as ApiResponse<{ admin: AdminProfile }>;
    markCookieSessionActive(true);
    return json.data.admin;
  } catch {
    return null;
  }
}

export async function apiGet<T>(path: string, token: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: authHeaders(token),
    credentials: FETCH_CREDENTIALS,
    cache: "no-store",
  });
  if (!res.ok) await throwApiError(res, path);
  const json = (await res.json()) as ApiResponse<T>;
  return json.data;
}

export async function apiPost<T>(path: string, token: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    credentials: FETCH_CREDENTIALS,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) await throwApiError(res, path);
  const json = (await res.json()) as ApiResponse<T>;
  return json.data;
}

export async function apiPatch<T>(path: string, token: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "PATCH",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    credentials: FETCH_CREDENTIALS,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) await throwApiError(res, path);
  const json = (await res.json()) as ApiResponse<T>;
  return json.data;
}

export async function apiPut<T>(path: string, token: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    credentials: FETCH_CREDENTIALS,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) await throwApiError(res, path);
  const json = (await res.json()) as ApiResponse<T>;
  return json.data;
}

export async function apiDelete<T>(path: string, token: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "DELETE",
    headers: authHeaders(token),
    credentials: FETCH_CREDENTIALS,
  });
  if (!res.ok) await throwApiError(res, path);
  const json = (await res.json()) as ApiResponse<T>;
  return json.data;
}

export async function apiUpload<T>(path: string, token: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: authHeaders(token),
    credentials: FETCH_CREDENTIALS,
    body: form,
  });
  if (!res.ok) await throwApiError(res, path);
  const json = (await res.json()) as ApiResponse<T>;
  return json.data;
}

/** 内存 JWT 不可用时的占位符；请求走 HttpOnly Cookie，勿作 Bearer 发送 */
export const COOKIE_AUTH = "__cookie__";

/** 内存中的 JWT：兼容 WS query；优先 HttpOnly Cookie，JS 不可读 Cookie 时用此回退 */
let memoryToken: string | null = null;
let cookieSessionActive = false;

export function markCookieSessionActive(active = true) {
  cookieSessionActive = active;
}

export function getToken(): string | null {
  if (memoryToken) return memoryToken;
  if (typeof document === "undefined") return cookieSessionActive ? COOKIE_AUTH : null;
  // 兼容旧版可读 Cookie；新登录走 HttpOnly，这里通常拿不到
  const match = document.cookie.match(/(?:^|; )gf_token=([^;]+)/);
  if (match) return decodeURIComponent(match[1]);
  return cookieSessionActive ? COOKIE_AUTH : null;
}

export function setToken(token: string) {
  memoryToken = token;
  cookieSessionActive = true;
  // 清除历史非 HttpOnly Cookie，避免双源冲突
  if (typeof document !== "undefined") {
    document.cookie = "gf_token=; path=/; max-age=0";
  }
}

export function getAdminProfile(): AdminProfile | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|; )gf_admin=([^;]+)/);
  if (!match) return decodeAdminFromJwt(getToken());
  try {
    return JSON.parse(decodeURIComponent(match[1])) as AdminProfile;
  } catch {
    return decodeAdminFromJwt(getToken());
  }
}

export function setAdminProfile(admin: AdminProfile) {
  document.cookie = `gf_admin=${encodeURIComponent(JSON.stringify(admin))}; path=/; max-age=86400; SameSite=Lax`;
}

export function clearToken() {
  memoryToken = null;
  cookieSessionActive = false;
  document.cookie = "gf_token=; path=/; max-age=0";
  document.cookie = "gf_admin=; path=/; max-age=0";
}

function decodeAdminFromJwt(token: string | null): AdminProfile | null {
  if (!token || token === COOKIE_AUTH) return null;
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const json = atob(part.replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(json) as { sub?: string; username?: string; role?: string };
    const id = Number(payload.sub) || 0;
    const username = payload.username || "admin";
    return { id, username, name: username, role: payload.role || "admin" };
  } catch {
    return null;
  }
}
