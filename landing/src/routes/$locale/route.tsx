import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { LocaleProvider } from "@/components/locale-context";
import { SiteFooter, SiteHeader } from "@/components/site-chrome";
import { isLocale } from "@/lib/locale";

export const Route = createFileRoute("/$locale")({
  beforeLoad: ({ params }) => {
    if (!isLocale(params.locale)) {
      throw redirect({ to: "/$locale", params: { locale: "en" } });
    }
  },
  component: LocaleShell,
});

function LocaleShell() {
  const { locale } = Route.useParams();
  const safe = isLocale(locale) ? locale : "en";
  return (
    <LocaleProvider locale={safe}>
      <SiteHeader />
      <main id="content">
        <Outlet />
      </main>
      <SiteFooter />
    </LocaleProvider>
  );
}
