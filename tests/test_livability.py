"""Livability profile math against the committed POI index.

These run fully offline against src/casita/data/poi_index.sqlite — the same
credentials-free contract as the demo tests.
"""
from casita import livability

# Arsicault's corner in the Inner Richmond — dense, well-mapped, stable.
INNER_RICHMOND = (37.7834, -122.4593)
# Open water mid-strait, well inside the index bbox (note: NOT near Alcatraz,
# whose ferry terminal is a mapped transit POI).
BAY_WATER = (37.826, -122.455)


def test_profile_inner_richmond_is_walkable():
    p = livability.profile(*INNER_RICHMOND)
    assert p.verdict == "walkable"
    assert p.points >= 3
    # A dense corner: cafes+bakeries form a cluster, transit is close.
    assert sum(p.cats[c].count_800m for c in livability.CAFE_CATS) >= 3
    assert p.cats["transit"].nearest_m is not None
    assert p.cats["transit"].nearest_m <= livability.TRANSIT_NEAR_M


def test_profile_returns_every_category():
    p = livability.profile(*INNER_RICHMOND)
    assert set(p.cats) == set(livability.CATEGORIES)


def test_profile_over_water_is_car_dependent():
    p = livability.profile(*BAY_WATER)
    assert p.verdict == "car-dependent"
    assert p.points <= 1
    assert all(s.count_800m == 0 for s in p.cats.values())


def test_score_bonus_never_exceeds_cap():
    # Sweep a coarse grid over the index bbox — the cap must hold everywhere.
    lat0, lng0, lat1, lng1 = 37.70, -122.57, 37.96, -122.36
    steps = 8
    for i in range(steps + 1):
        for j in range(steps + 1):
            lat = lat0 + (lat1 - lat0) * i / steps
            lng = lng0 + (lng1 - lng0) * j / steps
            assert 0 <= livability.score_bonus(lat, lng) <= 12


def test_score_bonus_dense_corner_beats_water():
    assert livability.score_bonus(*INNER_RICHMOND) > livability.score_bonus(*BAY_WATER)


def test_profile_cache_hits_on_nearby_coords():
    livability._profile_cached.cache_clear()
    livability.profile(37.78341, -122.45932)
    livability.profile(37.78339, -122.45928)  # same 4dp cell
    info = livability._profile_cached.cache_info()
    assert info.hits == 1
    assert info.misses == 1


def test_brief_marin_mentions_drive_normal():
    s = livability.brief(37.9061, -122.5450, marin=True)  # downtown Mill Valley
    assert "drive-normal" in s
    assert "penalize" in s


def test_walk_minutes_matches_walk_module_constants():
    # 800m at 4.5 km/h with the 1.3 grid factor ≈ 14 min — same formula walk.py uses.
    assert livability.walk_minutes(800) == 14
    assert livability.walk_minutes(1) == 1


def test_hexes_geojson_all_features_meet_min_total():
    fc = livability.hexes_geojson()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) > 100
    for f in fc["features"]:
        assert f["properties"]["total"] >= 5
        assert f["properties"]["verdict"] in ("walkable", "mixed", "car-dependent")
        ring = f["geometry"]["coordinates"][0]
        assert ring[0] == ring[-1]  # closed ring


def test_poi_meta_carries_attribution():
    meta = livability.poi_meta()
    assert "OpenStreetMap" in meta["attribution"]
    assert meta["h3_resolution"] == "8"


# ---------- rank.score() integration ----------

def _listing(**kw):
    from casita.models import Listing
    defaults = dict(source="manual", source_id="t1", url="https://x.test/1")
    defaults.update(kw)
    return Listing(**defaults)


def test_score_no_dogs_stays_gated_despite_walkable_location():
    from casita.rank import score
    L = _listing(dog_policy="no_dogs", lat=INNER_RICHMOND[0], lng=INNER_RICHMOND[1])
    assert score(L) == -1000


def test_score_dogs_ok_always_outranks_no_dogs():
    from casita.rank import score
    # A no-dogs listing at the most walkable corner in the index must never
    # outrank a dogs-ok listing at the least walkable coordinate.
    best_loc_no_dogs = _listing(dog_policy="no_dogs",
                                lat=INNER_RICHMOND[0], lng=INNER_RICHMOND[1])
    worst_loc_dogs_ok = _listing(dog_policy="dogs_ok",
                                 lat=BAY_WATER[0], lng=BAY_WATER[1])
    assert score(worst_loc_dogs_ok) > score(best_loc_no_dogs)


def test_score_marin_listing_gets_no_livability_bonus(monkeypatch):
    from casita.rank import score
    # If Marin were not suppressed, this monkeypatched bonus would add 12.
    monkeypatch.setattr(livability, "score_bonus", lambda lat, lng: 12)
    marin = _listing(dog_policy="dogs_ok", lat=37.9061, lng=-122.5450)
    sf = _listing(dog_policy="dogs_ok", lat=37.7834, lng=-122.4593)
    marin_before = score(marin)
    monkeypatch.setattr(livability, "score_bonus", lambda lat, lng: 0)
    assert score(marin) == marin_before               # Marin: bonus never applied
    monkeypatch.setattr(livability, "score_bonus", lambda lat, lng: 12)
    sf_with = score(sf)
    monkeypatch.setattr(livability, "score_bonus", lambda lat, lng: 0)
    assert sf_with == score(sf) + 12                  # SF: bonus applied


def test_listing_brief_includes_livability_clause():
    from casita.llm import _listing_brief
    L = _listing(price=4000, beds=2, baths=1)
    brief = _listing_brief(L, "WALKING (SF)", livability="3/4 errands on foot (walkable)")
    assert "livability: 3/4 errands on foot (walkable)" in brief
    # And the historical-example call shape (positional, no livability) still works.
    assert "livability:" not in _listing_brief(L, "")
