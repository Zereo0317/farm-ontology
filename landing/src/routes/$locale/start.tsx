import { createFileRoute } from "@tanstack/react-router";
import { StartFlow } from "@/components/start-flow";
import { COPY } from "@/lib/copy";
import { alternateLinks, isLocale } from "@/lib/locale";

export const Route = createFileRoute("/$locale/start")({
  head: ({ params }) => {
    const locale = isLocale(params.locale) ? params.locale : "en";
    const copy = COPY[locale];
    return {
      meta: [
        { title: copy.startMetaTitle },
        { name: "description", content: copy.startMetaDescription },
      ],
      links: alternateLinks("/start"),
    };
  },
  component: StartFlow,
});
