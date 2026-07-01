/** 浏览器走 Next.js 同源代理 /api → FastAPI，避免跨域与 API 未启动时的错误 URL */
function resolveApiUrl(): string {
  if (typeof window !== "undefined") {
    return "";
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:18081";
}

const API_URL = resolveApiUrl();

export type ApiResponse<T> = {
  success: boolean;
  data: T;
  meta?: { request_id?: string };
};

export async function adminLogin(username: string, password: string) {
  const res = await fetch(`${API_URL}/api/v1/auth/admin-login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error("login_failed");
  const json = (await res.json()) as ApiResponse<{ access_token: string; admin: { name: string } }>;
  return json.data;
}

export async function apiGet<T>(path: string, token: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`api_error:${res.status}`);
  const json = (await res.json()) as ApiResponse<T>;
  return json.data;
}

export async function apiPost<T>(path: string, token: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`api_error:${res.status}`);
  const json = (await res.json()) as ApiResponse<T>;
  return json.data;
}

export async function apiPatch<T>(path: string, token: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`api_error:${res.status}`);
  const json = (await res.json()) as ApiResponse<T>;
  return json.data;
}

export async function apiPut<T>(path: string, token: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`api_error:${res.status}`);
  const json = (await res.json()) as ApiResponse<T>;
  return json.data;
}

export async function apiDelete<T>(path: string, token: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`api_error:${res.status}`);
  const json = (await res.json()) as ApiResponse<T>;
  return json.data;
}

export function getToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|; )gf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function setToken(token: string) {
  document.cookie = `gf_token=${encodeURIComponent(token)}; path=/; max-age=86400; SameSite=Lax`;
}

export function clearToken() {
  document.cookie = "gf_token=; path=/; max-age=0";
}
