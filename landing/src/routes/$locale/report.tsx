import { createFileRoute } from "@tanstack/react-router";
import { ReportPage } from "@/components/report-page";
import { COPY } from "@/lib/copy";
import { alternateLinks, isLocale } from "@/lib/locale";
import { SOCIAL_PREVIEW, socialImage, socialMeta } from "@/lib/social-preview";

export const Route = createFileRoute("/$locale/report")({
  head: ({ params }) => {
    const locale = isLocale(params.locale) ? params.locale : "en";
    const copy = COPY[locale];
    const preview = SOCIAL_PREVIEW[locale].research;
    return {
      meta: [
        { title: copy.reportMetaTitle },
        { name: "description", content: copy.reportMetaDescription },
        ...socialMeta({
          title: copy.reportMetaTitle,
          description: copy.reportMetaDescription,
          image: socialImage(locale, "research"),
          imageAlt: preview.imageAlt,
          imageWidth: preview.imageWidth,
          imageHeight: preview.imageHeight,
          url: `https://seges.ai/${locale}/report`,
        }),
      ],
      links: alternateLinks("/report"),
    };
  },
  component: ReportPage,
});
