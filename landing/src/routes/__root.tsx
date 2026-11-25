import { createRootRoute, HeadContent, Outlet, Scripts, useRouterState } from "@tanstack/react-router";
import { AuthProvider } from "@/lib/auth/provider";
import { htmlLangForPath } from "@/lib/locale";
import { SOCIAL_PREVIEW, socialImage, socialMeta } from "@/lib/social-preview";
import appCss from "../styles.css?url";

const defaultPreview = SOCIAL_PREVIEW.en.farmer;
const defaultImage = socialImage("en", "farmer");

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: defaultPreview.title },
      { name: "theme-color", content: "#f7f5f2" },
      { name: "description", content: defaultPreview.description },
      { property: "og:site_name", content: "Seges" },
      { property: "og:type", content: "website" },
      { property: "og:locale", content: "en_US" },
      ...socialMeta({
        title: defaultPreview.title,
        description: defaultPreview.description,
        image: defaultImage,
        imageAlt: defaultPreview.imageAlt,
        imageWidth: defaultPreview.imageWidth,
        imageHeight: defaultPreview.imageHeight,
        url: "https://seges.ai/en/?for=farmer",
      }),
    ],
    links: [
      { rel: "icon", type: "image/svg+xml", href: "/favicon.svg" },
      { rel: "preload", href: appCss, as: "style" },
      { rel: "stylesheet", href: appCss },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Sarabun:wght@400;500;600&family=Noto+Serif+Thai:wght@400;600&display=swap",
        media: "print",
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
        <script
          dangerouslySetInnerHTML={{
            __html:
              "var fl=function(){var l=document.querySelector('link[href*=\\'fonts.googleapis\\']');if(l&&l.media==='print')l.media='all';};if(document.readyState==='complete')fl();else addEventListener('load',fl,true);",
          }}
        />
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
