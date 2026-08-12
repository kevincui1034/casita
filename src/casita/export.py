"""Static JSON export for the web/ dashboard.

SECURITY CONTRACT — read before changing anything here.

The listings DB contains data that must never reach a public site: the five
contact_* columns, reviewer votes in their own words, and listing_status
rows that reveal the household's negotiating position (applied / declined /
…). This module therefore builds each record from an explicit ALLOWLIST —
never from row keys — and passes every free-text field through
listing_page._scrub. scripts/validate_public.py re-checks the emitted files
from the outside, and tests/test_export.py asserts the contract.

Excluded columns: contact_name, contact_phone, contact_email, contact_url,
contact_note, description, raw_json, share_token (would make private detail
URLs guessable), address_verified.
Excluded tables: votes, interactions, listing_status, attachments, actions,
pending_urls, llm_facts, llm_photo_reviews, runs. Status/votes are read only
to reproduce the site's ranking ORDER and are never serialized.

Photos are hotlinked original http(s) URLs, capped at 4 — locally mirrored
"/photos/..." paths are filtered out and never copied into web/.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from . import livability, storage, walk
from .listing_page import _scrub
from .models import Listing
from .rank import rank, score
from .walk import BAKERIES, BEACHES, SF_CENTER, TRAILS, is_marin, nearest

MAX_PHOTOS = 4


def _clean(value: str | None) -> str | None:
    return _scrub(value) if value else None


def _public_photos(L: Listing) -> list[str]:
    urls = []
    if L.image_url and L.image_url.startswith("http"):
        urls.append(L.image_url)
    for p in L.photos:
        if p.startswith("http") and p not in urls:
            urls.append(p)
    return urls[:MAX_PHOTOS]


def _walk_block(L: Listing, walk_map, drive_map) -> dict | None:
    marin = is_marin(L)
    amap = drive_map if marin and drive_map else walk_map
    if not amap:
        return None

    def _best(anchors):
        if marin and drive_map:
            best = None
            for a in anchors:
                m = drive_map.get((L.key, a.name))
                if m is None:
                    continue
                if best is None or m < best[1]:
                    best = (a, m)
            return best
        return nearest(walk_map, L.key, anchors)

    out: dict = {"mode": "drive" if marin else "walk"}
    for label, anchors in (("trail", TRAILS), ("beach", BEACHES), ("bakery", BAKERIES)):
        b = _best(anchors)
        if b:
            out[label] = {"name": b[0].short, "min": b[1]}
    if marin and drive_map:
        sf = drive_map.get((L.key, SF_CENTER[0].name))
        if sf is not None:
            out["sf"] = {"name": SF_CENTER[0].short, "min": sf}
    return out if len(out) > 1 else None


def _livability_block(L: Listing) -> dict | None:
    if L.lat is None or L.lng is None:
        return None
    p = livability.profile(L.lat, L.lng)
    return {
        "verdict": p.verdict,
        "points": p.points,
        "cats": {
            c: {
                "nearest_m": s.nearest_m,
                "name": _clean(s.nearest_name),
                "n800": s.count_800m,
            }
            for c, s in p.cats.items()
        },
    }


def _listing_record(L: Listing, rank_index: int, walk_map, drive_map) -> dict:
    quality = {
        k: v
        for k, v in (
            ("light", L.light_quality),
            ("view", L.view_quality),
            ("condition", L.condition_quality),
        )
        if v
    }
    return {
        "key": L.key,
        "source": L.source,
        "url": L.url,
        "title": _clean(L.title),
        "address": _clean(L.address),
        "hood": _clean(L.hood),
        "price": L.price,
        "beds": L.beds,
        "baths": L.baths,
        "sqft": L.sqft,
        "dog_policy": L.dog_policy,
        "parking": _clean(L.parking),
        "laundry": _clean(L.laundry),
        "has_yard": L.has_yard,
        "yard_note": _clean(L.yard_note),
        "lat": L.lat,
        "lng": L.lng,
        "is_marin": is_marin(L),
        "severity": L.llm_severity,
        "rank": rank_index,
        "score": score(L, walk_map),
        "blurb": _clean(L.share_blurb or L.llm_reason or L.visual_summary),
        "quality": quality or None,
        "photos": _public_photos(L),
        "first_seen": L.first_seen.date().isoformat() if L.first_seen else None,
        "walk": _walk_block(L, walk_map, drive_map),
        "livability": _livability_block(L),
    }


def _write_json(path: Path, obj) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=True, separators=(",", ":")),
        encoding="utf-8",
    )
    return path.stat().st_size


def export_site_data(out_dir: Path, *, source_label: str = "local-db") -> dict[str, int]:
    """Export sanitized dashboard data. Returns {file: entity count}."""
    with storage.connect() as conn:
        listings = storage.active_listings(conn)
        # Status/votes reproduce the site's ordering only — never serialized.
        status_map = {
            r["listing_key"]: r["status"]
            for r in conn.execute("SELECT listing_key, status FROM listing_status")
        }
        vote_scores = {
            r["listing_key"]: r["net"]
            for r in conn.execute(
                "SELECT listing_key,"
                " SUM(CASE direction WHEN 'up' THEN 1 ELSE -1 END) AS net"
                " FROM votes GROUP BY listing_key"
            )
        }
    walk_map = walk.populate_for(listings)
    drive_map = walk.populate_drive_for_marin(listings)
    ordered = rank(listings, walk_map, status_map=status_map, vote_scores=vote_scores)

    records = [
        _listing_record(L, i + 1, walk_map, drive_map)
        for i, L in enumerate(ordered)
    ]
    pois = list(livability.iter_pois())
    hexes = livability.hexes_geojson()
    poi_meta = livability.poi_meta()

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source_label,
        "listing_count": len(records),
        "poi_count": len(pois),
        "hex_count": len(hexes["features"]),
        "bbox": json.loads(poi_meta.get("bbox", "null")),
        "osm_data_timestamp": poi_meta.get("osm_data_timestamp"),
        "attribution": {
            "pois": poi_meta.get(
                "attribution", "(c) OpenStreetMap contributors, ODbL 1.0"
            ),
            "tiles": "OpenFreeMap (c) OpenMapTiles Data from OpenStreetMap",
        },
    }

    _write_json(out_dir / "listings.json", records)
    _write_json(out_dir / "pois.json", pois)
    _write_json(out_dir / "hexes.json", hexes)
    _write_json(out_dir / "meta.json", meta)
    return {
        "listings": len(records),
        "pois": len(pois),
        "hexes": len(hexes["features"]),
    }
