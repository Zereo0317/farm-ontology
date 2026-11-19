import { cookies } from "next/headers";

import { BoundaryWalker } from "./boundary-walker";

export const metadata = {
  title: "田界步行 · ほ場ウォーク · Boundary walk",
};

const LOCALES = new Set(["zh-TW", "zh-CN", "en", "ja", "th"]);

/** I1: SSR the walker in the visitor's locale — the farm-locale cookie is
 * negotiated by middleware, so the first paint is already in their language
 * instead of defaulting to zh-TW until hydration. */
export default async function WalkPage() {
  const store = await cookies();
  const saved = store.get("farm-locale")?.value ?? "";
  const initialLang = (LOCALES.has(saved) ? saved : "zh-TW") as
    | "zh-TW"
    | "zh-CN"
    | "en"
    | "ja"
    | "th";
  return (
    <main style={{ maxWidth: "32rem", margin: "0 auto", padding: "1.5rem 1.2rem 4rem" }}>
      <BoundaryWalker initialLang={initialLang} />
    </main>
  );
}
