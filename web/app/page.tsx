import { Suspense } from "react";
import { cookies } from "next/headers";

import { Advisories } from "./advisories";
import { FieldSheet } from "./field-sheet";

/**
 * The field sheet is the client component that owns the language chooser
 * and mirrors its choice into the `farm-locale` cookie; the server-side
 * advisories panel reads that cookie so both halves speak one language.
 */
async function currentLocale(): Promise<"zh-TW" | "zh-CN" | "en" | "ja" | "th"> {
  const jar = await cookies();
  const saved = jar.get("farm-locale")?.value;
  return saved === "zh-TW" || saved === "zh-CN" || saved === "ja" || saved === "th"
    ? saved
    : "en";
}

async function AdvisoriesLocaleBound({ farmId }: { farmId: string }) {
  const locale = await currentLocale();
  return <Advisories locale={locale} farmId={farmId} />;
}

function AdvisoriesFallback() {
  return (
    <section className="advisories" aria-busy="true">
      <p className="kicker">Advisories</p>
      <p className="caption">loading advisories…</p>
    </section>
  );
}

export default async function Page(props: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await props.searchParams;
  const farmId = typeof params.farm_id === "string" ? params.farm_id : "";
  return (
    <>
      <FieldSheet initialFarmId={farmId} />
      <Suspense fallback={<AdvisoriesFallback />}>
        <AdvisoriesLocaleBound farmId={farmId} />
      </Suspense>
    </>
  );
}
