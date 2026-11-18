import type { Metadata, Viewport } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "大豆田紀錄 · Soybean field record · บันทึกแปลงถั่วเหลือง",
  description:
    "Local soybean field record. Class C stays closed. 現場大豆田紀錄，類別 C 關閉。 บันทึกแปลงถั่วเหลืองในท้องถิ่น",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

/**
 * The static lang attribute is a neutral default; the client field sheet
 * reflects the user's active locale onto <html> at runtime
 * (document.documentElement.lang = localeHtmlLang[locale]).
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="und">
      <body>{children}</body>
    </html>
  );
}
