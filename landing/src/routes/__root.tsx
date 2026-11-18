import { createRootRoute, HeadContent, Outlet, Scripts, useRouterState } from "@tanstack/react-router";
import { AuthProvider } from "@/lib/auth/provider";
import { htmlLangForPath } from "@/lib/locale";
import appCss from "../styles.css?url";

const APP_NAME = "Seges";

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: APP_NAME },
      { name: "theme-color", content: "#f7f5f2" },
      { name: "description", content: "Seges — every farm data point carries its birth certificate. Sensors, decisions and positions in one tamper-evident ledger." },
      { property: "og:site_name", content: "Seges" },
      { property: "og:title", content: "Seges — 每一筆農地數據，都自帶出生證明" },
      { property: "og:description", content: "衛星、氣象、感測器與授權，全部寫進同一本防竄改帳本。" },
      { property: "og:type", content: "website" },
      { property: "og:url", content: "https://seges.ai" },
      { property: "og:image", content: "https://seges.ai/og-card.png" },
      { property: "og:image:width", content: "1200" },
      { property: "og:image:height", content: "630" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:title", content: "Seges — 每一筆農地數據，都自帶出生證明" },
      { name: "twitter:image", content: "https://seges.ai/og-card.png" },
    ],
    links: [
      { rel: "icon", type: "image/svg+xml", href: "/favicon.svg" },
      { rel: "stylesheet", href: appCss },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Sarabun:wght@400;500;600&family=Noto+Serif+Thai:wght@400;600&display=swap",
      },
    ],
  }),
  component: RootDocument,
});

function RootDocument() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const lang = htmlLangForPath(pathname);
  return (
    <html lang={lang} className="antialiased" suppressHydrationWarning>
      <head>
        <HeadContent />
      </head>
      <body>
        <AuthProvider>
          <Outlet />
        </AuthProvider>
        <Scripts />
      </body>
    </html>
  );
}
