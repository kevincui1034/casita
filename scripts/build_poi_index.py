"""Build the committed OpenStreetMap POI index for livability scoring.

Dev-only, network-using. Run as:

    uv run --with h3 python scripts/build_poi_index.py

Fetches points of interest for the SF + southern Marin bounding box from the
Overpass API, precomputes the H3 resolution-8 hex aggregation, and writes
src/casita/data/poi_index.sqlite. The sqlite file is COMMITTED so that the
runtime module (src/casita/livability.py) and the demo path stay fully
offline and credentials-free.

Data is (c) OpenStreetMap contributors, ODbL 1.0 — see
src/casita/data/ATTRIBUTION.md. Re-run this script only to refresh the data;
runtime code never imports it.

Water masking note: hex cells are suppressed when they hold fewer than 5
POIs, which also removes open-water cells for free (they have ~0 POIs), so
no separate coastline geometry is needed.
"""
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_public  # noqa: E402 — sibling script, shares the ban patterns

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "casita" / "data" / "poi_index.sqlite"


def _sanitize_name(name: str | None) -> str | None:
    """Drop POI names that collide with the repo's private-string bans.

    OSM is public data, but the public-repo contract bans certain strings
    (e.g. the author's street) from the tree outright — a Mill Valley POI
    named after that street would otherwise smuggle the string back in via
    the committed index and the web export. The POI itself is kept; only the
    display name is dropped. Found by validate_public's export scan.
    """
    if not name:
        return name
    for pattern in validate_public.PRIVATE_PATTERNS.values():
        if pattern.search(name):
            return None
    if validate_public.PERSONAL_NAME_PATTERN.search(name):
        return None
    return name

# (south, west, north, east) — SF + southern Marin, matching the search area.
BBOX = (37.70, -122.57, 37.96, -122.36)

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

H3_RES = 8
MIN_POIS_PER_HEX = 5

# OSM selector -> casita category. Each entry is (category, overpass filter).
# Kept as explicit query lines so the mapping is auditable against the wiki.
SELECTORS: list[tuple[str, str]] = [
    ("supermarket", '["shop"="supermarket"]'),
    ("grocery", '["shop"~"^(greengrocer|health_food)$"]'),
    ("convenience", '["shop"="convenience"]'),
    ("bakery", '["shop"="bakery"]'),
    ("cafe", '["amenity"="cafe"]'),
    ("restaurant", '["amenity"="restaurant"]'),
    ("park", '["leisure"="park"]'),
    ("dog_park", '["leisure"="dog_park"]'),
    ("transit", '["highway"="bus_stop"]'),
    ("transit", '["railway"~"^(station|tram_stop)$"]'),
    ("transit", '["amenity"="ferry_terminal"]'),
    ("pharmacy", '["amenity"="pharmacy"]'),
    ("pharmacy", '["healthcare"="pharmacy"]'),
    ("school", '["amenity"="school"]'),
]

# The errands test evaluated at each hex center mirrors livability.profile():
# grocery-ish, park, cafe cluster, transit. Categories that count toward each.
GROCERY_CATS = {"supermarket", "grocery"}
PARK_CATS = {"park", "dog_park"}
CAFE_CATS = {"cafe", "bakery"}

SCHEMA = """
CREATE TABLE pois (
  id INTEGER PRIMARY KEY,
  osm_type TEXT NOT NULL,
  osm_id INTEGER NOT NULL,
  category TEXT NOT NULL,
  name TEXT,
  lat REAL NOT NULL,
  lng REAL NOT NULL
);
CREATE UNIQUE INDEX idx_pois_osm ON pois (osm_type, osm_id, category);
CREATE INDEX idx_pois_cat ON pois (category);

CREATE VIRTUAL TABLE pois_rtree USING rtree(
  id, min_lat, max_lat, min_lng, max_lng
);

CREATE TABLE hexes (
  h3 TEXT PRIMARY KEY,
  center_lat REAL NOT NULL,
  center_lng REAL NOT NULL,
  boundary_json TEXT NOT NULL,
  counts_json TEXT NOT NULL,
  total INTEGER NOT NULL,
  points INTEGER NOT NULL,
  verdict TEXT NOT NULL
);

CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def _overpass_query() -> str:
    s, w, n, e = BBOX
    lines = "".join(
        f'  nwr{flt}({s},{w},{n},{e});\n' for _, flt in SELECTORS
    )
    return f"[out:json][timeout:180];\n(\n{lines});\nout center tags;\n"


def fetch_overpass() -> tuple[list[dict], str]:
    """Return (elements, osm_timestamp). Tries each endpoint with retries."""
    query = _overpass_query()
    last_err: Exception | None = None
    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(3):
            try:
                print(f"  overpass: {endpoint} (attempt {attempt + 1})")
                r = httpx.post(
                    endpoint,
                    data={"data": query},
                    headers={"User-Agent": "casita-poi-index/0.1"},
                    timeout=240,
                )
                r.raise_for_status()
                payload = r.json()
                return payload["elements"], payload.get("osm3s", {}).get(
                    "timestamp_osm_base", ""
                )
            except Exception as e:  # noqa: BLE001 — dev script, retry then move on
                last_err = e
                print(f"    failed: {e}")
                time.sleep(10 * (attempt + 1))
    raise SystemExit(
        f"All Overpass endpoints failed ({last_err}). Fallback: download the "
        "Geofabrik norcal extract and adapt this script to read it with pyrosm."
    )


def _categorize(tags: dict) -> list[str]:
    """Map OSM tags to categories. One element can satisfy several selectors."""
    cats = []
    shop = tags.get("shop")
    amenity = tags.get("amenity")
    leisure = tags.get("leisure")
    if shop == "supermarket":
        cats.append("supermarket")
    if shop in ("greengrocer", "health_food"):
        cats.append("grocery")
    if shop == "convenience":
        cats.append("convenience")
    if shop == "bakery":
        cats.append("bakery")
    if amenity == "cafe":
        cats.append("cafe")
    if amenity == "restaurant":
        cats.append("restaurant")
    if leisure == "park":
        cats.append("park")
    if leisure == "dog_park":
        cats.append("dog_park")
    if (
        tags.get("highway") == "bus_stop"
        or tags.get("railway") in ("station", "tram_stop")
        or amenity == "ferry_terminal"
    ):
        cats.append("transit")
    if amenity == "pharmacy" or tags.get("healthcare") == "pharmacy":
        cats.append("pharmacy")
    if amenity == "school":
        cats.append("school")
    return cats


def extract_pois(elements: list[dict]) -> list[dict]:
    pois = []
    for el in elements:
        tags = el.get("tags") or {}
        if "center" in el:
            lat, lng = el["center"]["lat"], el["center"]["lon"]
        elif "lat" in el:
            lat, lng = el["lat"], el["lon"]
        else:
            continue
        for cat in _categorize(tags):
            pois.append(
                {
                    "osm_type": el["type"],
                    "osm_id": el["id"],
                    "category": cat,
                    "name": _sanitize_name(tags.get("name")),
                    "lat": lat,
                    "lng": lng,
                }
            )
    return pois


def _errands_points(counts: dict[str, int]) -> int:
    """The 4-point errands test, mirrored from livability.profile()."""
    points = 0
    if any(counts.get(c) for c in GROCERY_CATS):
        points += 1
    if any(counts.get(c) for c in PARK_CATS):
        points += 1
    if sum(counts.get(c, 0) for c in CAFE_CATS) >= 3:
        points += 1
    if counts.get("transit"):
        points += 1
    return points


def _verdict(points: int) -> str:
    if points >= 3:
        return "walkable"
    if points == 2:
        return "mixed"
    return "car-dependent"


def build_hexes(pois: list[dict]) -> list[dict]:
    import h3  # dev-only dependency, provided via `uv run --with h3`

    cells: dict[str, dict[str, int]] = {}
    for p in pois:
        cell = h3.latlng_to_cell(p["lat"], p["lng"], H3_RES)
        cells.setdefault(cell, {})
        cells[cell][p["category"]] = cells[cell].get(p["category"], 0) + 1

    out = []
    for cell, counts in cells.items():
        total = sum(counts.values())
        if total < MIN_POIS_PER_HEX:
            continue  # sparse cells suppressed; also masks water for free
        lat, lng = h3.cell_to_latlng(cell)
        # GeoJSON ring: [ [lng, lat], ... ], closed.
        ring = [[b, a] for a, b in h3.cell_to_boundary(cell)]
        ring.append(ring[0])
        points = _errands_points(counts)
        out.append(
            {
                "h3": cell,
                "center_lat": lat,
                "center_lng": lng,
                "boundary_json": json.dumps([ring]),
                "counts_json": json.dumps(counts, sort_keys=True),
                "total": total,
                "points": points,
                "verdict": _verdict(points),
            }
        )
    return out


def build_db(pois: list[dict], hexes: list[dict], osm_timestamp: str) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    conn = sqlite3.connect(OUT)
    conn.executescript(SCHEMA)
    for p in pois:
        cur = conn.execute(
            "INSERT OR IGNORE INTO pois (osm_type, osm_id, category, name, lat, lng)"
            " VALUES (?,?,?,?,?,?)",
            (p["osm_type"], p["osm_id"], p["category"], p["name"], p["lat"], p["lng"]),
        )
        if cur.lastrowid and cur.rowcount:
            conn.execute(
                "INSERT INTO pois_rtree (id, min_lat, max_lat, min_lng, max_lng)"
                " VALUES (?,?,?,?,?)",
                (cur.lastrowid, p["lat"], p["lat"], p["lng"], p["lng"]),
            )
    conn.executemany(
        "INSERT INTO hexes (h3, center_lat, center_lng, boundary_json,"
        " counts_json, total, points, verdict) VALUES"
        " (:h3, :center_lat, :center_lng, :boundary_json, :counts_json,"
        " :total, :points, :verdict)",
        hexes,
    )
    meta = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bbox": json.dumps(BBOX),
        "osm_data_timestamp": osm_timestamp,
        "h3_resolution": str(H3_RES),
        "min_pois_per_hex": str(MIN_POIS_PER_HEX),
        "attribution": "(c) OpenStreetMap contributors, ODbL 1.0",
    }
    conn.executemany(
        "INSERT INTO meta (key, value) VALUES (?,?)", list(meta.items())
    )
    conn.commit()
    conn.close()


def main() -> None:
    print("fetching POIs from Overpass...")
    elements, osm_timestamp = fetch_overpass()
    pois = extract_pois(elements)
    print(f"  {len(elements)} elements -> {len(pois)} categorized POIs")
    by_cat: dict[str, int] = {}
    for p in pois:
        by_cat[p["category"]] = by_cat.get(p["category"], 0) + 1
    for cat, n in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        print(f"    {cat:<12} {n}")
    print("aggregating H3 hexes...")
    hexes = build_hexes(pois)
    print(f"  {len(hexes)} hexes with >= {MIN_POIS_PER_HEX} POIs")
    build_db(pois, hexes, osm_timestamp)
    size_mb = OUT.stat().st_size / 1024 / 1024
    print(f"wrote {OUT} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    sys.exit(main())
