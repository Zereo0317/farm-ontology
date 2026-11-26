import { redirect } from "next/navigation";

import { resolveFarmLink } from "@/lib/farm-link";
import { FieldSheet } from "../../field-sheet";

export const metadata = {
  title: "這塊田 · Open this farm",
};

/** Farm QR deep link: /farm/<farm_id> loads the authorized farm without exposing coordinates. */
export default async function FarmCoordinatesPage(props: {
  params: Promise<{ coords: string }>;
  searchParams: Promise<{ farm_id?: string }>;
}) {
  const { coords: rawSegment } = await props.params;
  const query = await props.searchParams;
  const target = resolveFarmLink(rawSegment, query.farm_id ?? "");
  if (!target) redirect("/");
  return (
    <FieldSheet
      initialLat={target.latitude}
      initialLon={target.longitude}
      initialFarmId={target.farmId}
    />
  );
}
