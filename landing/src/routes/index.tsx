import { createFileRoute, redirect } from "@tanstack/react-router";
import { preferredLocale } from "@/lib/locale.functions";
import { localeFromAcceptLanguage, readClientLocale } from "@/lib/locale";

export const Route = createFileRoute("/")({
  beforeLoad: async () => {
    const locale =
      typeof document !== "undefined"
        ? (readClientLocale() ?? localeFromAcceptLanguage(navigator.language))
        : await preferredLocale();
    throw redirect({ to: "/$locale", params: { locale } });
  },
  component: Gate,
});

function Gate() {
  return (
    <main className="px-6 py-16">
      <h1 className="font-display text-3xl">Seges</h1>
    </main>
  );
}
