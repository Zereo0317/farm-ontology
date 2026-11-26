import { redirect } from "next/navigation";

/**
 * /farm without coordinates answers with the operator farm's known pin so
 * the QR deep link (`/farm/<lat>,<lon>`) and the apex `/farm` entry both
 * land on the same field sheet. The pin is build-time constant for the
 * single-farm deployment (per docs/backend-live.md); multi-farm routing
 * arrives with tenant onboarding.
 */
const LAT = "42.7018152";
const LON = "142.4071291";

export default function FarmIndex() {
  redirect("/farm/biratori-hokkaido");
}
