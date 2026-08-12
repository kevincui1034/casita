import type { Listing, Poi } from "./types";

export function listingsToGeojson(listings: Listing[]) {
  return {
    type: "FeatureCollection" as const,
    features: listings
      .filter((l) => l.lat !== null && l.lng !== null)
      .map((l) => ({
        type: "Feature" as const,
        id: l.rank,
        geometry: { type: "Point" as const, coordinates: [l.lng!, l.lat!] },
        properties: {
          key: l.key,
          price: l.price,
          severity: l.severity ?? "unranked",
          verdict: l.livability?.verdict ?? "unknown",
        },
      })),
  };
}

export function poisToGeojson(pois: Poi[]) {
  return {
    type: "FeatureCollection" as const,
    features: pois.map((p) => ({
      type: "Feature" as const,
      id: p.id,
      geometry: { type: "Point" as const, coordinates: [p.lng, p.lat] },
      properties: { cat: p.cat, name: p.name ?? "" },
    })),
  };
}

export function fmtPrice(price: number | null): string {
  return price ? `$${price.toLocaleString()}` : "$?";
}

export function walkMinutes(meters: number): number {
  // Same estimate as the Python side: 1.3 grid factor at 4.5 km/h.
  return Math.max(1, Math.round(((meters * 1.3) / 1000 / 4.5) * 60));
}

export function fmtDist(m: number | null): string {
  if (m === null) return "none nearby";
  return m < 1000 ? `${m} m` : `${(m / 1000).toFixed(1)} km`;
}
