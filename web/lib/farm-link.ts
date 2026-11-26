import { validateFarmId } from "@/lib/auth/membership";

const COORDS_PATTERN = /^(-?\d{1,3}(?:\.\d+)?),(-?\d{1,3}(?:\.\d+)?)$/;

export type FarmLinkTarget =
  | { farmId: string; latitude?: string; longitude?: string }
  | null;

/** Resolve an opaque farm QR path or a legacy coordinate path with farm identity. */
export function resolveFarmLink(rawSegment: string, queryFarmId = ""): FarmLinkTarget {
  let segment: string;
  try {
    segment = decodeURIComponent(rawSegment);
  } catch {
    return null;
  }
  if (validateFarmId(segment)) return { farmId: segment };

  const match = COORDS_PATTERN.exec(segment);
  if (!match) return null;
  // A bare coordinate path (no explicit farm_id) resolves to the operator
  // farm — the single-farm deployment's pin IS the farm identity here; the
  // membership check down-route still gates every read.
  const farmId = validateFarmId(queryFarmId) ? queryFarmId : 'biratori-hokkaido';
  const latitude = Number(match[1]);
  const longitude = Number(match[2]);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) {
    return null;
  }
  return { farmId, latitude: match[1], longitude: match[2] };
}
