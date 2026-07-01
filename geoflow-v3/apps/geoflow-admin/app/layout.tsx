import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GEOFlow Admin v3",
  description: "GEO 内容工程管理后台",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
