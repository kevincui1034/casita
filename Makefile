.PHONY: install check docs demo clean poi

install:
	uv sync

poi:  # dev-only, network: rebuild the committed OSM POI index (ODbL, see data/ATTRIBUTION.md)
	uv run --with h3 python scripts/build_poi_index.py

check:
	uv run python -m compileall src scripts
	uv run pytest
	uv run python scripts/validate_public.py
	uv run zensical build --clean
	uv build
	uv run casita --help >/dev/null

docs:
	uv run zensical serve

demo:
	uv run casita demo

clean:
	rm -rf .cache dist site tmp
