import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "大豆田紀錄",
  description: "Local soybean field record. Class C stays closed.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-TW">
      <body>{children}</body>
    </html>
  );
}
