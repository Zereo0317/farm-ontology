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
  if (!match || !validateFarmId(queryFarmId)) return null;
  const latitude = Number(match[1]);
  const longitude = Number(match[2]);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) {
    return null;
  }
  return { farmId: queryFarmId, latitude: match[1], longitude: match[2] };
}
