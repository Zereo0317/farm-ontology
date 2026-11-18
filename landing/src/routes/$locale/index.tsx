import { createFileRoute } from "@tanstack/react-router";
import { LandingPage } from "@/components/landing-page";
import { alternateLinks, isLocale } from "@/lib/locale";
import { getLiveLedger } from "@/lib/live.functions";
import { VISION, type Audience } from "@/lib/vision";

type AudienceSearch = { for?: Audience };

export const Route = createFileRoute("/$locale/")({
  validateSearch: (search: Record<string, unknown>): AudienceSearch => {
    if (search.for === "hunger" || search.for === "farmer") return { for: search.for };
    return {};
  },
  loader: () => getLiveLedger(),
  head: ({ params, match }) => {
    const locale = isLocale(params.locale) ? params.locale : "en";
    const vision = VISION[locale];
    const hunger = match.search.for === "hunger";
    return {
      meta: [
        { title: `${hunger ? vision.hungerTitle : vision.farmerTitle} — Seges` },
        { name: "description", content: hunger ? vision.hungerDeck : vision.farmerDeck },
      ],
      links: alternateLinks(""),
    };
  },
  component: Home,
});

function Home() {
  const ledger = Route.useLoaderData();
  const audience = Route.useSearch().for === "hunger" ? "hunger" : "farmer";
  return <LandingPage ledger={ledger} audience={audience} />;
}
