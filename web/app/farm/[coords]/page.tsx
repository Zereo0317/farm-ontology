import { redirect } from "next/navigation";

import { FieldSheet } from "../../field-sheet";

const COORDS_PATTERN = /^(-?\d{1,3}(?:\.\d+)?),(-?\d{1,3}(?:\.\d+)?)$/;

export const metadata = {
  title: "這塊田 · Open this farm",
};

/** QR "open this farm" deep link: /farm/<lat>,<lon> preloads the coordinates. */
export default async function FarmCoordinatesPage(props: {
  params: Promise<{ coords: string }>;
}) {
  // Dynamic params arrive URL-encoded (the comma becomes %2C) — decode first.
  const { coords: rawCoords } = await props.params;
  const coords = decodeURIComponent(rawCoords);
  const match = COORDS_PATTERN.exec(coords);

  if (!match || Math.abs(Number(match[1])) > 90 || Math.abs(Number(match[2])) > 180) {
    redirect("/");
  }

  return <FieldSheet initialLat={match[1]} initialLon={match[2]} />;
}
