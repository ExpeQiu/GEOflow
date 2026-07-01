"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { adminLogin, setToken } from "@/lib/api-client";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("password");
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const data = await adminLogin(username, password);
      setToken(data.access_token);
      router.push("/dashboard");
    } catch {
      setError("登录失败，请检查账号密码");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <form onSubmit={handleSubmit} className="bg-white border rounded-lg p-8 w-full max-w-md shadow-sm">
        <h1 className="text-xl font-bold mb-1">GEOFlow Admin</h1>
        <p className="text-sm text-[var(--muted)] mb-6">v3 · Next.js + FastAPI</p>
        {error && <p className="text-red-600 text-sm mb-4">{error}</p>}
        <label className="block text-sm mb-1">用户名</label>
        <input
          className="w-full border rounded px-3 py-2 mb-4"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <label className="block text-sm mb-1">密码</label>
        <input
          type="password"
          className="w-full border rounded px-3 py-2 mb-6"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" className="w-full bg-[var(--primary)] text-white rounded py-2 font-medium">
          登录
        </button>
      </form>
    </div>
  );
}
