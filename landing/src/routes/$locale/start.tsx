import { createFileRoute } from "@tanstack/react-router";
import { StartFlow } from "@/components/start-flow";
import { COPY } from "@/lib/copy";
import { alternateLinks, isLocale } from "@/lib/locale";
import { SOCIAL_PREVIEW, socialImage, socialMeta } from "@/lib/social-preview";

export const Route = createFileRoute("/$locale/start")({
  head: ({ params }) => {
    const locale = isLocale(params.locale) ? params.locale : "en";
    const copy = COPY[locale];
    const preview = SOCIAL_PREVIEW[locale].farmer;
    return {
      meta: [
        { title: copy.startMetaTitle },
        { name: "description", content: copy.startMetaDescription },
        ...socialMeta({
          title: copy.startMetaTitle,
          description: copy.startMetaDescription,
          image: socialImage(locale, "farmer"),
          imageAlt: preview.imageAlt,
          imageWidth: preview.imageWidth,
          imageHeight: preview.imageHeight,
          url: `https://seges.ai/${locale}/start`,
        }),
      ],
      links: alternateLinks("/start"),
    };
  },
  component: StartFlow,
});
