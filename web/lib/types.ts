// Mirrors the export schema in src/casita/export.py exactly.
// A field added there must be added here AND to the validator allowlist.

export type Verdict = "walkable" | "mixed" | "car-dependent";
export type Severity = "ok" | "concerns" | "filtered" | null;
export type DogPolicy = "large_ok" | "dogs_ok" | "small_only" | "no_dogs" | null;

export interface CategoryStat {
  nearest_m: number | null;
  name: string | null;
  n800: number;
}

export interface Livability {
  verdict: Verdict;
  points: number;
  cats: Record<string, CategoryStat>;
}

export interface WalkAnchor {
  name: string;
  min: number;
}

export interface WalkBlock {
  mode: "walk" | "drive";
  trail?: WalkAnchor;
  beach?: WalkAnchor;
  bakery?: WalkAnchor;
  sf?: WalkAnchor;
}

export interface Listing {
  key: string;
  source: string;
  url: string;
  title: string | null;
  address: string | null;
  hood: string | null;
  price: number | null;
  beds: number | null;
  baths: number | null;
  sqft: number | null;
  dog_policy: DogPolicy;
  parking: string | null;
  laundry: string | null;
  has_yard: boolean | null;
  yard_note: string | null;
  lat: number | null;
  lng: number | null;
  is_marin: boolean;
  severity: Severity;
  rank: number;
  score: number;
  blurb: string | null;
  quality: { light?: string; view?: string; condition?: string } | null;
  photos: string[];
  first_seen: string | null;
  walk: WalkBlock | null;
  livability: Livability | null;
}

export interface Poi {
  id: number;
  cat: string;
  name: string | null;
  lat: number;
  lng: number;
}

export interface HexProperties {
  h3: string;
  total: number;
  points: number;
  verdict: Verdict;
  counts: Record<string, number>;
}

export interface Meta {
  generated_at: string;
  source: string;
  listing_count: number;
  poi_count: number;
  hex_count: number;
  bbox: [number, number, number, number] | null;
  osm_data_timestamp: string | null;
  attribution: { pois: string; tiles: string };
}

export interface Filters {
  severity: string | null; // "ok" | "concerns" | null=all (filtered always hidden by default)
  dogPolicy: string | null; // "large_ok" | "dogs_ok" | null=all
  maxPrice: number | null;
  verdict: Verdict | null;
}

export const DOG_LABELS: Record<string, string> = {
  large_ok: "Large dogs OK",
  dogs_ok: "Dogs OK",
  small_only: "Small dogs only",
  no_dogs: "No dogs",
};
