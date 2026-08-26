import type { Metadata } from "next";
import "./globals.css";
import { AppProviders } from "./providers";

export const metadata: Metadata = {
  title: "GEOFlow Admin v3",
  description: "GEO 内容工程管理后台",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
