# Livability

Casita ranks how easy daily life is around a listing — groceries, parks,
cafes, transit — from a committed OpenStreetMap index, fully offline.

## The Errands Test

`livability.profile(lat, lng)` computes, for eleven amenity categories, the
nearest instance and the count within 800 m (roughly a ten-minute walk),
then scores four points:

- a real grocery within 800 m (supermarkets and grocers — corner liquor
  stores don't count),
- a park within 800 m (the dogs),
- a cafe cluster — at least three cafes or bakeries within 800 m,
- a transit stop within 400 m.

Four or three points reads `walkable`, two `mixed`, fewer `car-dependent`.
The verdict is phrased as a consequence ("4/4 errands on foot"), not an
adjective, and the detail page shows the named nearest places so the number
can always be interrogated.

## Where It Feeds

- **Deterministic rank** (`rank.score`): a bonus capped at +12 — level with
  the `large_ok` dog bonus and below the doubled trail term. Livability
  breaks ties between viable homes; it never decides which homes are viable
  (a no-dogs listing stays gated at -1000 regardless, and a regression test
  enforces it).
- **LLM ranking brief**: one compact clause per listing.
- **Detail pages and cards**: errands rows and a "Walkable errands" chip;
  the verdict is a searchable token in the card haystack.
- **`casita livability <key>`**: a read-only CLI table for one listing or a
  raw coordinate.
- **`casita export` → `web/`**: the map dashboard renders the same data as
  an H3 hex layer.

## Marin Is Different On Purpose

Driving is normal in Mill Valley and Sausalito, and the ranking policy
already forbids penalizing Marin listings for distance. Marin listings get
the profile *descriptively* — rows render neutral with a "drive-normal
area" suffix — and the score bonus is suppressed entirely.

## The Data

`scripts/build_poi_index.py` (dev-only, `make poi`) pulls the SF + southern
Marin bounding box from the Overpass API and writes
`src/casita/data/poi_index.sqlite` (~1.5 MB, committed): 11 categories with
an R-tree for radius queries, plus a precomputed H3 resolution-8 hex
aggregation. Hex cells with fewer than five places are suppressed — which
also masks open water for free. POI names are sanitized against
`validate_public.py`'s private-string patterns at build time.

The committed index is the same pattern as the fixture's `walk_cache`: the
demo path stays credentials-free and no runtime network call exists to
fail. Unlike the route cache there is deliberately **no cache layer at
all** — livability is a pure function over committed data, so the
cache-staleness bugs that can bite `llm_facts` and the route cache cannot
occur here.

Data is © OpenStreetMap contributors (ODbL); see
`src/casita/data/ATTRIBUTION.md`.

## Ways This Could Go Further

- Real walk isochrones (Valhalla) instead of radius circles — the shape of
  a 10-minute walk in SF is nothing like a circle.
- Elevation: a listing at the foot of a 100 m climb walks differently than
  the flats; free USGS data resolves SF hills well.
- Freshness: the index is a point-in-time OSM snapshot; `make poi` rebuilds
  it, but nothing warns when it drifts stale.
