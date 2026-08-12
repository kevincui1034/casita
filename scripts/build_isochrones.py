"""Precompute walk isochrones for exported listings via a local Valhalla.

Dev-only, optional. The dashboard tolerates the output being absent — this
enriches it with the real 5/10/15-minute walkshed shape, which in San
Francisco is nothing like a circle (hills, parks, the Presidio fence).

One-time local setup (the container downloads norcal and builds its graph):

    docker run -d --name casita-valhalla -p 8002:8002 \
      -v <scratch>:/custom_files \
      -e tile_urls=https://download.geofabrik.de/north-america/us/california/norcal-latest.osm.pbf \
      ghcr.io/valhalla/valhalla-scripted:latest

Then:  uv run python scripts/build_isochrones.py

Notes that came out of measurement rather than docs:
- ONE request returns all three contours (Valhalla runs a single expansion
  to the widest band) — never issue three requests per listing.
- Valhalla's default generalization is already ~25 m tolerance; no
  post-simplification stage is worth building.
- The six styling properties Valhalla injects per feature are dropped and
  coordinates rounded to 5 dp (~1 m) — ~21% smaller for free.
"""
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
LISTINGS = ROOT / "web" / "public" / "data" / "listings.json"
OUT_DIR = ROOT / "web" / "public" / "data" / "isochrones"
VALHALLA = "http://127.0.0.1:8002"
CONTOURS_MIN = [5, 10, 15]

# Listing keys are "source:id"; ':' is not a valid filename character on
# Windows. The dashboard applies the same mapping (lib/toGeojson.ts isoPath).
def key_to_filename(key: str) -> str:
    return key.replace(":", "__") + ".json"


def fetch_isochrone(client: httpx.Client, lat: float, lng: float) -> dict | None:
    body = {
        "locations": [{"lat": lat, "lon": lng}],
        "costing": "pedestrian",
        "contours": [{"time": m} for m in CONTOURS_MIN],
        "polygons": True,
        "denoise": 1,
    }
    r = client.post(f"{VALHALLA}/isochrone", json=body, timeout=30)
    r.raise_for_status()
    return r.json()


def slim(fc: dict) -> dict:
    """Strip styling props, keep contour minutes, round coords to 5 dp."""
    out_features = []
    for f in fc.get("features", []):
        geom = f["geometry"]
        rounded = [
            [[round(x, 5), round(y, 5)] for x, y in ring]
            for ring in geom["coordinates"]
        ]
        out_features.append(
            {
                "type": "Feature",
                "geometry": {"type": geom["type"], "coordinates": rounded},
                "properties": {"contour": f["properties"]["contour"]},
            }
        )
    return {"type": "FeatureCollection", "features": out_features}


def main() -> int:
    listings = json.loads(LISTINGS.read_text(encoding="utf-8"))
    coords = [
        (r["key"], r["lat"], r["lng"])
        for r in listings
        if r.get("lat") is not None and r.get("lng") is not None
    ]
    print(f"{len(coords)} listings with coordinates")

    with httpx.Client() as client:
        # Wait for the service (the graph build can take a while on first run).
        try:
            status = client.get(f"{VALHALLA}/status", timeout=5)
            status.raise_for_status()
        except Exception as e:  # noqa: BLE001
            print(f"Valhalla not ready at {VALHALLA}: {e}")
            return 1

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        done = failed = 0
        for key, lat, lng in coords:
            try:
                fc = fetch_isochrone(client, lat, lng)
                (OUT_DIR / key_to_filename(key)).write_text(
                    json.dumps(slim(fc), separators=(",", ":")),
                    encoding="utf-8",
                )
                done += 1
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"  {key}: {e}")
        dt = time.time() - t0
    total = sum(f.stat().st_size for f in OUT_DIR.glob("*.json"))
    print(
        f"wrote {done} isochrones ({failed} failed) in {dt:.1f}s "
        f"-> {OUT_DIR} ({total / 1024:.0f} KB total)"
    )
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
