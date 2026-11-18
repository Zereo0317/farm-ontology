import { Suspense } from "react";

import { Advisories } from "./advisories";
import { FieldSheet } from "./field-sheet";

function AdvisoriesFallback() {
  return (
    <section className="advisories" aria-busy="true">
      <p className="kicker">諮詢 Advisories</p>
      <p className="caption">後端資料載入中… loading advisories…</p>
    </section>
  );
}

export default function Page() {
  return (
    <>
      <FieldSheet />
      <Suspense fallback={<AdvisoriesFallback />}>
        <Advisories />
      </Suspense>
    </>
  );
}
