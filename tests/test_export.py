"""The export security contract: only allowlisted data reaches web/public/data.

Runs fully offline against the committed demo fixture, mirroring test_demo's
env pattern.
"""
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_public  # noqa: E402  (scripts/ is not a package)

FIXTURE = ROOT / "fixtures" / "demo.sqlite"


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    """Run the export once against a fixture copy; yield the output dir."""
    tmp = tmp_path_factory.mktemp("export")
    db = tmp / "export.sqlite"
    shutil.copy2(FIXTURE, db)
    out_dir = tmp / "data"

    import os

    from casita import export, livability

    env_updates = {
        "CASITA_DB_PATH": str(db),
        "CASITA_ROUTE_CACHE_DB": str(db),
        "CASITA_ROUTES_OFFLINE": "1",
    }
    previous = {k: os.environ.get(k) for k in env_updates}
    try:
        os.environ.update(env_updates)
        livability._profile_cached.cache_clear()
        counts = export.export_site_data(out_dir, source_label="demo-fixture")
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    return out_dir, counts


def test_export_writes_all_four_files(exported):
    out_dir, counts = exported
    for name in ("listings.json", "pois.json", "hexes.json", "meta.json"):
        assert (out_dir / name).exists(), name
    assert counts["listings"] > 100
    assert counts["pois"] > 5000
    assert counts["hexes"] > 100


def test_export_listing_keys_are_allowlisted(exported):
    out_dir, _ = exported
    records = json.loads((out_dir / "listings.json").read_text(encoding="utf-8"))
    keys: set[str] = set()
    validate_public._collect_keys(records, keys)
    assert keys <= validate_public.EXPORT_ALLOWED_KEYS
    assert not keys & validate_public.EXPORT_FORBIDDEN_KEYS


def test_export_raw_text_has_no_private_fields(exported):
    out_dir, _ = exported
    text = (out_dir / "listings.json").read_text(encoding="utf-8")
    for needle in ("contact_name", "contact_phone", "contact_email",
                   "share_token", "raw_json", '"voter"', '"status"'):
        assert needle not in text, needle
    # No phone numbers survive _scrub + the allowlist.
    phone = re.compile(
        r"(?<![\d.-])(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}(?![\d.-])"
    )
    assert not phone.search(text)


def test_export_photos_are_remote_only_and_capped(exported):
    out_dir, _ = exported
    records = json.loads((out_dir / "listings.json").read_text(encoding="utf-8"))
    with_photos = 0
    for rec in records:
        assert len(rec["photos"]) <= 4
        with_photos += bool(rec["photos"])
        for url in rec["photos"]:
            assert url.startswith("http"), url
        assert rec["url"].startswith("http")
    assert with_photos > 50  # the fixture is photo-rich; a regression here is real


def test_export_ranking_order_is_1_based_and_dense(exported):
    out_dir, _ = exported
    records = json.loads((out_dir / "listings.json").read_text(encoding="utf-8"))
    assert [r["rank"] for r in records] == list(range(1, len(records) + 1))


def test_export_hexes_meet_min_total(exported):
    out_dir, _ = exported
    fc = json.loads((out_dir / "hexes.json").read_text(encoding="utf-8"))
    assert fc["type"] == "FeatureCollection"
    for f in fc["features"]:
        assert f["properties"]["total"] >= 5


def test_export_meta_has_attribution_and_vintage(exported):
    out_dir, _ = exported
    meta = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["source"] == "demo-fixture"
    assert "OpenStreetMap" in meta["attribution"]["pois"]
    assert "OpenFreeMap" in meta["attribution"]["tiles"]
    assert meta["generated_at"]
    assert meta["listing_count"] > 100


def test_validator_catches_forbidden_key(tmp_path, monkeypatch, exported):
    """Adversarial: a contact field smuggled into the export must FAIL validation."""
    out_dir, _ = exported
    poisoned_dir = tmp_path / "data"
    poisoned_dir.mkdir()
    records = json.loads((out_dir / "listings.json").read_text(encoding="utf-8"))
    records[0]["contact_email"] = "leak@example.com"
    (poisoned_dir / "listings.json").write_text(
        json.dumps(records), encoding="utf-8"
    )
    monkeypatch.setattr(validate_public, "EXPORT_DIR", poisoned_dir)
    failures: list[str] = []
    validate_public.check_export_dir(failures)
    assert any("contact_email" in f for f in failures)
