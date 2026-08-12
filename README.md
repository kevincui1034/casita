# Casita

[![Documentation](https://img.shields.io/badge/docs-casita-0b6e4f?style=for-the-badge)](https://matin.github.io/casita/)

Casita is a personal rental-search tool published as a public repo.

It started as a small script for a time-boxed San Francisco rental search with
two large dogs: scrape Zillow, Craigslist, Zumper, and Redfin; enrich the
listings; rank them; and render a static page that was easier to review than
four open browser tabs.

This is not a product or service. It is published as-is, under MIT, as a
personal-use codebase for an interview loop. The interesting part is what a
candidate chooses to improve.

## Demo

The demo is credentials-free and uses a sanitized SQLite fixture with cached
route times and precomputed LLM enrichment.

```bash
uv sync
uv run playwright install chromium
uv run casita demo
```

Then open <http://127.0.0.1:8765/>.

The demo does not scrape, call Vertex, deploy to Firebase, read GCS, or call the
Google Maps Routes API. It does use Playwright's local Chromium browser to
render Open Graph preview images from listing photos and facts. Live `search` /
`enrich` / `publish` paths still exist for private use and are controlled by
environment variables; see `.env.example`.

## What It Does

- Scrapes active rental listings from Zillow, Craigslist, Zumper, and Redfin.
- Normalizes listing facts into SQLite.
- Classifies dog policy and enriches details from listing pages.
- Uses Gemini for fact extraction, photo review, share blurbs, and ranking.
- Computes walking and driving times to curated SF / Marin anchors.
- Renders a static, mobile-friendly site with index and detail pages.
- Records votes and passes so future ranking can learn from reviewer feedback.

The domain assumptions are intentionally personal: large dogs, San Francisco
walkability, Marin driving context, trails, beaches, and good bakeries nearby.
That is the point of a personal tool.

## What this fork adds

**Live at <https://casita-phi.vercel.app/>**

I wanted to answer a question the original tool never asked. A listing can
look great on paper and still be a bad place to live. My goal was to
understand how livable each rental actually is. Is the area walkable? Is
there a real grocery store nearby, or only a corner liquor store? Are there
parks for the dogs, cafes worth walking to, fun things around, a transit
stop close enough to skip the car?

So I built livability scoring on top of the existing pipeline, and a map to
see it.

- `src/casita/livability.py` scores an "errands on foot" profile for every
  listing, built from a committed OpenStreetMap index of 8,528 places. It
  runs fully offline. It feeds the deterministic rank (capped so it can
  never outweigh dog policy), the LLM ranking brief, the detail pages, and
  a new `uv run casita livability <key>` verb. The thinking lives in
  `docs/how-it-works/livability.md`.
- `uv run casita export --fixture fixtures/demo.sqlite` writes sanitized
  JSON into `web/public/data/`. It's a strict allowlist. Contact info,
  votes, and funnel status never leave the database, and
  `scripts/validate_public.py` now checks the export from the outside.
- `web/` is a static Next.js + MapLibre dashboard over that JSON. Ranked
  listings, an H3 hex layer showing which blocks are genuinely walkable,
  clickable OSM places, and real 5/10/15 minute walksheds computed with
  Valhalla. In San Francisco a ten-minute walk is nothing like a circle,
  and the map shows it. No API keys, no database, nothing that can run up
  a bill. `cd web && npm install && npm run build` deploys anywhere static.

The two renderers are scoped on purpose. The Python static site stays the
credentials-free demo and CRM surface. The dashboard is the map and
analysis view.

### How the ranking works

Every listing is scored twice. Gemini reads each listing's brief, orders the
board, and flags a severity (that's the "fit" you see on cards). A
deterministic score in `rank.py` breaks ties and orders the map. The page
itself sorts in buckets, active conversations first, then net-upvoted
favorites, then the Gemini order, then new listings that haven't been ranked
yet, with hard-gated ones at the bottom.

Dog policy is the gate, and that's deliberate. A no-dogs listing scores
-1000 and no amount of charm buys that back. Everything else is a bonus.

| Signal | Points |
| --- | --- |
| Large dogs welcome | +12 |
| Dogs allowed, size unstated | +6 |
| Small dogs only | -30 |
| No dogs | gated at -1000 |
| Walk to a trail or Presidio gate | up to +30 (doubled, it's the stated priority) |
| Walk to a beach | up to +15 |
| Target neighborhood | up to +6 |
| 3+ bedrooms, 1.5+ baths | +4, +5 |
| In-unit laundry | +3 |
| Parking, garage best | up to +4 |
| Livability | up to +12 |

The livability bonus is my addition, and it's capped on purpose. It sits
level with the large-dog bonus and below the trail term, so a great
neighborhood breaks ties between viable homes but never outranks the dogs.

| Livability signal | Points |
| --- | --- |
| Real grocery within 800 m | +4 |
| Park within 800 m (the dogs) | +3 |
| Cafe cluster, 3+ cafes or bakeries within 800 m | +3 |
| Transit stop within 400 m | +2 |

The same four checks produce the errands verdict on cards and hexes. Three
or four points reads walkable, two reads mixed, less is car-dependent.
Distances are straight-line to the nearest place, and walk minutes assume
4.5 km/h with a 1.3 grid factor. The walkshed you see when you select a
listing is the real thing, a Valhalla isochrone over the street network.
Marin listings show the full profile but skip the bonus entirely. Driving
is normal there, and the ranking policy already forbids punishing Mill
Valley for distance.

The dashboard filters map straight onto these fields. "Fit" is the Gemini
severity, where "show gated" reveals the hard-filtered listings that are
hidden by default. "Dogs" filters the dog policy. "Price" caps monthly
rent. "Errands" filters the livability verdict.

One thing I chose not to build. A crime-based safety score was on my own
wishlist, and I cut it. Marin's open crime data only covers the Sheriff's
Office, so a cross-county score would call Mill Valley safe simply because
its data is missing. The industry also walked away from crime layers in
2021 over fair-housing risk. The reasoning is in
`docs/decisions/no-safety-score.md`.

## Docs

The [documentation site](https://matin.github.io/casita/) explains the systems
without turning them into assigned tasks. To run it locally instead:

```bash
uv run zensical serve
```

Start at `docs/index.md`, or run `uv run zensical build` to generate the site.

## Checks

```bash
make check
```

This compiles the Python modules, runs the pytest suite, runs the public leak
validator, builds the docs, builds the Python package artifacts, and checks
that the CLI imports.

## Contributing

Read `CONTRIBUTING.md`. The short version: fork the repo, pick something you
think makes Casita better, and explain why you chose it.
