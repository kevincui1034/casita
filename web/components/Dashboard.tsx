"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { Filters as FiltersT, Listing, Meta, Poi } from "@/lib/types";
import FilterBar from "./Filters";
import ListingPanel from "./ListingPanel";
import MapView from "./MapView";
import DetailDrawer from "./DetailDrawer";

interface Data {
  listings: Listing[];
  pois: Poi[];
  hexes: GeoJSON.FeatureCollection;
  meta: Meta;
}

export default function Dashboard() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [hoverKey, setHoverKey] = useState<string | null>(null);
  const [showHexes, setShowHexes] = useState(true);
  const [showPois, setShowPois] = useState(true);
  const [filters, setFilters] = useState<FiltersT>({
    severity: null,
    dogPolicy: null,
    maxPrice: null,
    verdict: null,
  });

  useEffect(() => {
    Promise.all(
      ["listings", "pois", "hexes", "meta"].map((n) =>
        fetch(`data/${n}.json`).then((r) => {
          if (!r.ok) throw new Error(`${n}.json: HTTP ${r.status}`);
          return r.json();
        }),
      ),
    )
      .then(([listings, pois, hexes, meta]) =>
        setData({ listings, pois, hexes, meta }),
      )
      .catch((e) => setError(String(e)));
  }, []);

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.listings.filter((l) => {
      // "filtered" (hard-gated: no dogs, dead pages) stays hidden unless
      // the user explicitly asks for it via the severity chip.
      if (filters.severity) {
        if (l.severity !== filters.severity) return false;
      } else if (l.severity === "filtered") {
        return false;
      }
      if (filters.dogPolicy && l.dog_policy !== filters.dogPolicy) return false;
      if (filters.maxPrice && (l.price ?? Infinity) > filters.maxPrice) return false;
      if (filters.verdict && l.livability?.verdict !== filters.verdict) return false;
      return true;
    });
  }, [data, filters]);

  const selected = useMemo(
    () => filtered.find((l) => l.key === selectedKey) ?? null,
    [filtered, selectedKey],
  );

  // Stable handlers so memoized cards don't re-render on every hover change.
  const handleSelectKey = useCallback(
    (key: string) => setSelectedKey((cur) => (cur === key ? null : key)),
    [],
  );
  const handleHoverKey = useCallback((key: string | null) => setHoverKey(key), []);

  if (error) {
    return (
      <div className="grid h-dvh place-items-center px-6 text-center text-muted-foreground">
        Failed to load data: {error}. Run `casita export` first.
      </div>
    );
  }
  if (!data) {
    return (
      <div className="grid h-dvh place-items-center text-muted-foreground">
        Loading listings…
      </div>
    );
  }

  const generated = data.meta.generated_at.slice(0, 10);

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex flex-wrap items-baseline gap-x-3.5 gap-y-1 border-b bg-card px-4 py-2.5">
        <h1 className="text-lg font-semibold tracking-tight">
          <span className="text-primary">casita</span> · livability map
        </h1>
        <span className="text-xs text-muted-foreground">
          {data.meta.listing_count} listings · data as of {generated} ·{" "}
          {data.meta.source}
        </span>
      </header>
      <FilterBar filters={filters} onChange={setFilters} />
      <div className="flex min-h-0 flex-1 max-md:flex-col-reverse">
        <ListingPanel
          listings={filtered}
          selectedKey={selectedKey}
          hoverKey={hoverKey}
          onSelectKey={handleSelectKey}
          onHoverKey={handleHoverKey}
        />
        <div className="relative min-w-0 flex-1">
          <MapView
            listings={filtered}
            pois={data.pois}
            hexes={data.hexes}
            attribution={data.meta.attribution}
            selectedKey={selectedKey}
            hoverKey={hoverKey}
            showHexes={showHexes}
            showPois={showPois}
            onSelect={setSelectedKey}
            onHover={setHoverKey}
            onToggleHexes={setShowHexes}
            onTogglePois={setShowPois}
          />
          {selected && (
            <DetailDrawer listing={selected} onClose={() => setSelectedKey(null)} />
          )}
        </div>
      </div>
    </div>
  );
}
