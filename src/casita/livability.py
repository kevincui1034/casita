"""Neighborhood livability from a committed OpenStreetMap POI index.

Answers "what is around this listing?" — nearest grocery / park / cafe /
transit and counts within a 10-minute walk — from
src/casita/data/poi_index.sqlite (built by scripts/build_poi_index.py, data
(c) OpenStreetMap contributors, ODbL; see data/ATTRIBUTION.md).

Deliberately a pure function over committed data: stdlib-only (sqlite3 +
math), no network, no cache DB. Route times in walk.py need a paid API and
therefore a cache; POI lookups are free, so the whole class of
cache-staleness bugs is designed out. The demo path stays credentials-free.

Scoring stance: livability breaks ties between viable homes — it never
decides which homes are viable. The bonus is capped at +12 (level with
rank.py's large_ok bonus, below the doubled trail term) and is not applied
to Marin listings, where driving is normal and the ranking policy already
forbids distance penalties (see llm._RANK_SYSTEM "DISTANCE MODES").
"""
import json
import math
import os
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterator

CATEGORIES = (
    "supermarket", "grocery", "convenience", "bakery", "cafe",
    "restaurant", "park", "dog_park", "transit", "pharmacy", "school",
)
GROCERY_CATS = ("supermarket", "grocery")
PARK_CATS = ("park", "dog_park")
CAFE_CATS = ("cafe", "bakery")

RADIUS_M = 800          # ~10 minute walk; counts use this
TRANSIT_NEAR_M = 400    # transit must be closer to count as an errand point
CAFE_CLUSTER_MIN = 3    # a "cafe cluster" = at least this many cafes+bakeries
_WINDOW_DEG_LAT = 0.02  # R-tree prefilter window (~2.2 km) for nearest-lookups
_WINDOW_DEG_LNG = 0.025

_DEFAULT_DB = Path(__file__).parent / "data" / "poi_index.sqlite"

_connection: sqlite3.Connection | None = None
_connection_path: Path | None = None


def db_path() -> Path:
    """Resolve the POI index path, allowing CASITA_POI_DB to redirect (tests)."""
    return Path(os.environ.get("CASITA_POI_DB", str(_DEFAULT_DB)))


def _conn() -> sqlite3.Connection:
    global _connection, _connection_path
    path = db_path()
    if _connection is None or _connection_path != path:
        if _connection is not None:
            _connection.close()
        _connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        _connection_path = path
    return _connection


def _haversine_m(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    # Same formula as walk._haversine_km; private copy keeps this module free
    # of walk.py's httpx/dotenv imports so the demo path stays stdlib-only.
    r = 6371000.0
    dlat = math.radians(b_lat - a_lat)
    dlng = math.radians(b_lng - a_lng)
    s = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(a_lat))
        * math.cos(math.radians(b_lat))
        * math.sin(dlng / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(s))


def walk_minutes(meters: float) -> int:
    """Rough walk-time estimate matching walk.py's grid factor and speed."""
    return max(1, round((meters * 1.30 / 1000) / 4.5 * 60))


@dataclass(frozen=True)
class CategoryStat:
    nearest_m: int | None   # None = nothing inside the ~2 km query window
    nearest_name: str | None
    count_800m: int


@dataclass(frozen=True)
class Profile:
    cats: dict[str, CategoryStat]   # every category in CATEGORIES is present
    points: int                      # 0-4 errands-on-foot score
    verdict: str                     # walkable | mixed | car-dependent

    def summary(self) -> str:
        """One-line human summary, e.g. for the CLI."""
        bits = []
        g = min(
            (self.cats[c] for c in GROCERY_CATS if self.cats[c].nearest_m is not None),
            key=lambda s: s.nearest_m, default=None,
        )
        if g:
            bits.append(f"grocery {g.nearest_m}m")
        p = min(
            (self.cats[c] for c in PARK_CATS if self.cats[c].nearest_m is not None),
            key=lambda s: s.nearest_m, default=None,
        )
        if p:
            bits.append(f"park {p.nearest_m}m")
        cafes = sum(self.cats[c].count_800m for c in CAFE_CATS)
        if cafes:
            bits.append(f"{cafes} cafes")
        t = self.cats["transit"]
        if t.nearest_m is not None:
            bits.append(f"transit {t.nearest_m}m")
        return f"{self.points}/4 errands on foot ({self.verdict})" + (
            f" — {', '.join(bits)}" if bits else ""
        )


def _verdict(points: int) -> str:
    if points >= 3:
        return "walkable"
    if points == 2:
        return "mixed"
    return "car-dependent"


@lru_cache(maxsize=2048)
def _profile_cached(lat4: float, lng4: float) -> Profile:
    rows = _conn().execute(
        """SELECT p.category, p.name, p.lat, p.lng FROM pois p
           JOIN pois_rtree r ON p.id = r.id
           WHERE r.min_lat >= ? AND r.max_lat <= ?
             AND r.min_lng >= ? AND r.max_lng <= ?""",
        (
            lat4 - _WINDOW_DEG_LAT, lat4 + _WINDOW_DEG_LAT,
            lng4 - _WINDOW_DEG_LNG, lng4 + _WINDOW_DEG_LNG,
        ),
    ).fetchall()

    nearest: dict[str, tuple[float, str | None]] = {}
    counts: dict[str, int] = {c: 0 for c in CATEGORIES}
    for category, name, plat, plng in rows:
        d = _haversine_m(lat4, lng4, plat, plng)
        if d <= RADIUS_M:
            counts[category] = counts.get(category, 0) + 1
        cur = nearest.get(category)
        if cur is None or d < cur[0]:
            nearest[category] = (d, name)

    cats = {
        c: CategoryStat(
            nearest_m=round(nearest[c][0]) if c in nearest else None,
            nearest_name=nearest[c][1] if c in nearest else None,
            count_800m=counts.get(c, 0),
        )
        for c in CATEGORIES
    }

    points = 0
    if any(cats[c].nearest_m is not None and cats[c].nearest_m <= RADIUS_M
           for c in GROCERY_CATS):
        points += 1
    if any(cats[c].nearest_m is not None and cats[c].nearest_m <= RADIUS_M
           for c in PARK_CATS):
        points += 1
    if sum(cats[c].count_800m for c in CAFE_CATS) >= CAFE_CLUSTER_MIN:
        points += 1
    t = cats["transit"]
    if t.nearest_m is not None and t.nearest_m <= TRANSIT_NEAR_M:
        points += 1

    return Profile(cats=cats, points=points, verdict=_verdict(points))


def profile(lat: float, lng: float) -> Profile:
    """Livability profile for a coordinate. ~10 m grid via 4dp rounding."""
    return _profile_cached(round(lat, 4), round(lng, 4))


def score_bonus(lat: float, lng: float) -> int:
    """Deterministic-rank bonus, 0..12 by construction.

    Callers gate on Marin themselves (rank.score) — this function is
    location-blind on purpose so it stays testable.
    """
    p = profile(lat, lng)
    bonus = 0
    if any(p.cats[c].nearest_m is not None and p.cats[c].nearest_m <= RADIUS_M
           for c in GROCERY_CATS):
        bonus += 4
    if any(p.cats[c].nearest_m is not None and p.cats[c].nearest_m <= RADIUS_M
           for c in PARK_CATS):
        bonus += 3   # the dogs
    if sum(p.cats[c].count_800m for c in CAFE_CATS) >= CAFE_CLUSTER_MIN:
        bonus += 3
    t = p.cats["transit"]
    if t.nearest_m is not None and t.nearest_m <= TRANSIT_NEAR_M:
        bonus += 2
    return bonus


def verdict(lat: float, lng: float) -> str:
    return profile(lat, lng).verdict


def brief(lat: float, lng: float, *, marin: bool = False) -> str:
    """One compact clause for the LLM ranking brief."""
    p = profile(lat, lng)
    core = p.summary()
    if marin:
        return f"errands profile (drive-normal area, do not penalize): {core}"
    return core


# ---------- export surface (read by casita export) ----------


def iter_pois() -> Iterator[dict]:
    for pid, cat, name, lat, lng in _conn().execute(
        "SELECT id, category, name, lat, lng FROM pois ORDER BY id"
    ):
        yield {"id": pid, "cat": cat, "name": name, "lat": lat, "lng": lng}


def hexes_geojson() -> dict:
    features = []
    for h3_id, boundary_json, counts_json, total, points, vdt in _conn().execute(
        "SELECT h3, boundary_json, counts_json, total, points, verdict FROM hexes"
    ):
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": json.loads(boundary_json)},
            "properties": {
                "h3": h3_id,
                "total": total,
                "points": points,
                "verdict": vdt,
                "counts": json.loads(counts_json),
            },
        })
    return {"type": "FeatureCollection", "features": features}


def poi_meta() -> dict[str, str]:
    return dict(_conn().execute("SELECT key, value FROM meta"))
