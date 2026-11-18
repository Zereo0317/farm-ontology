import { createFileRoute } from "@tanstack/react-router";
import { ReportPage } from "@/components/report-page";
import { COPY } from "@/lib/copy";
import { alternateLinks, isLocale } from "@/lib/locale";

export const Route = createFileRoute("/$locale/report")({
  head: ({ params }) => {
    const locale = isLocale(params.locale) ? params.locale : "en";
    const copy = COPY[locale];
    return {
      meta: [
        { title: copy.reportMetaTitle },
        { name: "description", content: copy.reportMetaDescription },
      ],
      links: alternateLinks("/report"),
    };
  },
  component: ReportPage,
});
