"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { LocaleSwitcher } from "@/components/admin/LocaleSwitcher";
import { adminLogin, setToken } from "@/lib/api-client";
import { useI18n } from "@/lib/i18n";

export default function LoginPage() {
  const router = useRouter();
  const { messages: zh } = useI18n();
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
      setError(zh.login.error);
    }
  }

  return (
    <div className="login-page flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="login-form rounded-2xl p-8">
          <div className="mb-8 text-center">
            <div className="login-badge mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full">
              <ShieldCheck className="h-8 w-8 text-white" />
            </div>
            <h1 className="mb-2 text-2xl font-bold text-gray-900">{zh.login.title}</h1>
            <p className="text-gray-600">{zh.login.subtitle}</p>
            <div className="mt-4 flex justify-center">
              <LocaleSwitcher />
            </div>
          </div>

          {error && <FlashAlert variant="error">{error}</FlashAlert>}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="username" className="mb-2 block text-sm font-medium text-gray-700">
                {zh.login.username}
              </label>
              <input
                id="username"
                className="block w-full rounded-lg border border-gray-300 px-3 py-3 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
              />
            </div>
            <div>
              <label htmlFor="password" className="mb-2 block text-sm font-medium text-gray-700">
                {zh.login.password}
              </label>
              <input
                id="password"
                type="password"
                className="block w-full rounded-lg border border-gray-300 px-3 py-3 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            <button
              type="submit"
              className="w-full rounded-lg bg-blue-600 px-4 py-3 font-medium text-white hover:bg-blue-700"
            >
              {zh.login.submit}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
