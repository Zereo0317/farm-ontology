import { createFileRoute } from "@tanstack/react-router";
import { LandingPage } from "@/components/landing-page";
import { alternateLinks, isLocale } from "@/lib/locale";
import { getLiveLedger } from "@/lib/live.functions";
import type { Audience } from "@/lib/vision";
import { OG_LOCALE, SOCIAL_PREVIEW, socialImage, socialMeta } from "@/lib/social-preview";

type AudienceSearch = { for?: Audience };

export const Route = createFileRoute("/$locale/")({
  validateSearch: (search: Record<string, unknown>): AudienceSearch => {
    if (search.for === "research" || search.for === "hunger") return { for: "research" };
    if (search.for === "finance") return { for: "finance" };
    if (search.for === "farmer") return { for: "farmer" };
    return {};
  },
  loader: () => getLiveLedger(),
  head: ({ params, match }) => {
    const locale = isLocale(params.locale) ? params.locale : "en";
    const audience = (match.search as AudienceSearch).for ?? "farmer";
    const preview = SOCIAL_PREVIEW[locale][audience];
    const image = socialImage(locale, audience);
    return {
      meta: [
        { title: preview.title },
        { name: "description", content: preview.description },
        { property: "og:locale", content: OG_LOCALE[locale] },
        ...socialMeta({
          title: preview.title,
          description: preview.description,
          image,
          imageAlt: preview.imageAlt,
          imageWidth: preview.imageWidth,
          imageHeight: preview.imageHeight,
          url: `https://seges.ai/${locale}/?for=${audience}`,
        }),
      ],
      links: alternateLinks(""),
    };
  },
  component: Home,
});

function Home() {
  const ledger = Route.useLoaderData();
  const audience = Route.useSearch().for ?? "farmer";
  return <LandingPage ledger={ledger} audience={audience} />;
}
