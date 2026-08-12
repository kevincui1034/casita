# Decision: No Crime-Based Safety Score

A "is this area safe?" layer was on the wishlist for the livability work. It
was deliberately scoped out, for two independent reasons — either alone
would be sufficient.

## The data cannot support it here

San Francisco publishes ~1M geocoded police incidents with roughly a
one-day lag (DataSF `wg3w-h783`). Marin's open dataset (`ahxi-5nsc`)
contains **Sheriff's Office incidents only** — Mill Valley PD and Sausalito
PD run their own departments and appear nowhere in it. A cross-county score
would rank the two Marin towns Casita searches as extraordinarily safe
purely because their data is structurally missing. That is a data artifact
presented as a fact, in exactly the towns where it would matter.

## The industry already retreated from this

Realtor.com removed its crime map in December 2021; Redfin publicly refused
to add crime data the same day and urged the industry to drop it; Trulia
phased its layer out in early 2022. Their stated reasoning: most crime is
unreported, reported incidents are often not crimes, and incident density
tracks historical redlining and policing intensity rather than actual risk
— so a neutral-looking score can become a proxy for race.

Ordering or filtering listings by such a score is *steering* under the Fair
Housing Act, and disparate-impact liability does not require intent. HUD's
2024 guidance places algorithmic tools squarely in scope, including tools
sourced from third-party vendors.

## What serves the underlying need instead

Amenity-access signals — the livability profile this repo ships — describe
*infrastructure presence* (groceries, parks, transit, lighting-adjacent
street life) rather than encoding assumptions about the people who live in
a place. If descriptive public-safety data is ever surfaced, it should be
raw, inspectable, SF-only-labeled counts — never a normalized score, and
never an input to ranking or filtering.
