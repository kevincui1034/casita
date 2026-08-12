"use client";

import { useEffect, useRef } from "react";
// MapLibre v6 dropped the default export — namespace import is required.
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

// v6 resolves its web worker relative to import.meta.url, which Next.js does
// not emit — the 404 is silent and the style never finishes loading. The
// worker is vendored into public/maplibre/ by scripts/copy-worker.mjs.
maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
import type { Listing, Meta, Poi } from "@/lib/types";
import { fmtPrice, listingsToGeojson, poisToGeojson } from "@/lib/toGeojson";
import Legend from "./Legend";

// OpenFreeMap: keyless, no rate limits, commercial use permitted.
const STYLE_URL = "https://tiles.openfreemap.org/styles/positron";

const SEVERITY_COLORS: Record<string, string> = {
  ok: "#355c43",
  concerns: "#9c7321",
  filtered: "#a8504a",
  unranked: "#8a8a8a",
};

// Hex fill by errands points — 4 discrete steps, muted so pins stay primary.
// "Absence reads faster than presence": car-dependent cells get the warm warn
// tone rather than simply fading out.
const HEX_COLORS = ["#a8504a", "#c98d51", "#7fa06a", "#355c43"]; // 0-1, 2, 3, 4 points

const POI_COLORS: Record<string, string> = {
  supermarket: "#355c43",
  grocery: "#355c43",
  convenience: "#7fa06a",
  bakery: "#9c7321",
  cafe: "#9c7321",
  restaurant: "#c98d51",
  park: "#4a7d5c",
  dog_park: "#4a7d5c",
  transit: "#4a6a8f",
  pharmacy: "#8f4a6a",
  school: "#6a5c8f",
};

// TS can't infer MapLibre's expression tuple types through a spread —
// build the match expressions once and cast.
const POI_COLOR_EXPR = [
  "match",
  ["get", "cat"],
  ...Object.entries(POI_COLORS).flat(),
  "#8a8a8a",
] as unknown as maplibregl.ExpressionSpecification;

const SEVERITY_COLOR_EXPR = [
  "match",
  ["get", "severity"],
  ...Object.entries(SEVERITY_COLORS).flat(),
  "#8a8a8a",
] as unknown as maplibregl.ExpressionSpecification;

interface Props {
  listings: Listing[];
  pois: Poi[];
  hexes: GeoJSON.FeatureCollection;
  attribution: Meta["attribution"];
  selectedKey: string | null;
  hoverKey: string | null;
  showHexes: boolean;
  showPois: boolean;
  onSelect: (key: string | null) => void;
  onHover: (key: string | null) => void;
  onToggleHexes: (v: boolean) => void;
  onTogglePois: (v: boolean) => void;
}

export default function MapView(props: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const loadedRef = useRef(false);
  // Latest props for use inside map event handlers without re-binding.
  const propsRef = useRef(props);
  propsRef.current = props;

  // ---- init (once) ----
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URL,
      center: [-122.46, 37.8],
      zoom: 11.2,
      attributionControl: {
        compact: false,
        customAttribution: `${propsRef.current.attribution.tiles} · POIs ${propsRef.current.attribution.pois}`,
      },
    });
    mapRef.current = map;
    // Debug hook for automated tests; harmless in production.
    (window as unknown as Record<string, unknown>).__casitaMap = map;
    map.on("error", (e) => console.error("[maplibre error]", e.error?.message ?? e));
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }));

    map.on("load", () => {
      // --- hex layer (below pins) ---
      map.addSource("hexes", { type: "geojson", data: propsRef.current.hexes });
      map.addLayer({
        id: "hexes-fill",
        type: "fill",
        source: "hexes",
        paint: {
          "fill-color": [
            "step",
            ["get", "points"],
            HEX_COLORS[0],
            2, HEX_COLORS[1],
            3, HEX_COLORS[2],
            4, HEX_COLORS[3],
          ],
          "fill-opacity": 0.22,
        },
      });
      map.addLayer({
        id: "hexes-line",
        type: "line",
        source: "hexes",
        paint: { "line-color": "#00000022", "line-width": 0.5 },
      });

      // --- POI layer (clustered, visible when zoomed in) ---
      map.addSource("pois", {
        type: "geojson",
        data: poisToGeojson(propsRef.current.pois),
        cluster: true,
        clusterRadius: 36,
        clusterMaxZoom: 14,
      });
      map.addLayer({
        id: "pois-clusters",
        type: "circle",
        source: "pois",
        filter: ["has", "point_count"],
        minzoom: 12.5,
        paint: {
          "circle-color": "#9a9282",
          "circle-opacity": 0.55,
          "circle-radius": ["step", ["get", "point_count"], 8, 25, 12, 100, 16],
        },
      });
      map.addLayer({
        id: "pois-dots",
        type: "circle",
        source: "pois",
        filter: ["!", ["has", "point_count"]],
        minzoom: 12.5,
        paint: {
          "circle-color": POI_COLOR_EXPR,
          "circle-radius": 4,
          "circle-opacity": 0.85,
          "circle-stroke-width": 1,
          "circle-stroke-color": "#ffffff",
        },
      });

      // --- listings (on top) ---
      map.addSource("listings", {
        type: "geojson",
        data: listingsToGeojson(propsRef.current.listings),
        promoteId: "key",
      });
      map.addLayer({
        id: "listing-pins",
        type: "circle",
        source: "listings",
        paint: {
          "circle-color": SEVERITY_COLOR_EXPR,
          "circle-radius": [
            "case",
            ["boolean", ["feature-state", "active"], false],
            10,
            6.5,
          ],
          "circle-stroke-width": [
            "case",
            ["boolean", ["feature-state", "active"], false],
            2.5,
            1.5,
          ],
          "circle-stroke-color": "#ffffff",
        },
      });

      // --- interactions ---
      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        offset: 12,
      });

      map.on("mouseenter", "listing-pins", (e) => {
        map.getCanvas().style.cursor = "pointer";
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties as { key: string; price: number | null };
        propsRef.current.onHover(p.key);
        const l = propsRef.current.listings.find((x) => x.key === p.key);
        popup
          .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setHTML(
            `<strong>${fmtPrice(l?.price ?? null)}/mo</strong><br/>${
              l?.hood ?? ""
            }`,
          )
          .addTo(map);
      });
      map.on("mouseleave", "listing-pins", () => {
        map.getCanvas().style.cursor = "";
        propsRef.current.onHover(null);
        popup.remove();
      });
      map.on("click", "listing-pins", (e) => {
        const key = (e.features?.[0]?.properties as { key?: string })?.key;
        if (key) propsRef.current.onSelect(key);
      });
      map.on("click", "pois-dots", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties as { cat: string; name: string };
        new maplibregl.Popup({ offset: 8 })
          .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setHTML(`<strong>${p.name || p.cat}</strong><br/>${p.cat}`)
          .addTo(map);
      });

      loadedRef.current = true;
      syncData(map, propsRef.current);
    });

    return () => {
      loadedRef.current = false;
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- data + visibility sync ----
  useEffect(() => {
    const map = mapRef.current;
    if (map && loadedRef.current) syncData(map, props);
  }, [props.listings, props.showHexes, props.showPois]);

  // ---- selection / hover highlighting + flyTo ----
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    map.removeFeatureState({ source: "listings" });
    const active = props.selectedKey ?? props.hoverKey;
    if (active) {
      map.setFeatureState({ source: "listings", id: active }, { active: true });
    }
    if (props.selectedKey) {
      const l = props.listings.find((x) => x.key === props.selectedKey);
      if (l?.lat && l?.lng) {
        map.flyTo({ center: [l.lng, l.lat], zoom: Math.max(map.getZoom(), 13.5) });
      }
    }
  }, [props.selectedKey, props.hoverKey, props.listings]);

  return (
    <>
      <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />
      <Legend
        hexColors={HEX_COLORS}
        showHexes={props.showHexes}
        showPois={props.showPois}
        onToggleHexes={props.onToggleHexes}
        onTogglePois={props.onTogglePois}
      />
    </>
  );
}

function syncData(map: maplibregl.Map, props: Props) {
  (map.getSource("listings") as maplibregl.GeoJSONSource | undefined)?.setData(
    listingsToGeojson(props.listings),
  );
  for (const id of ["hexes-fill", "hexes-line"]) {
    if (map.getLayer(id)) {
      map.setLayoutProperty(id, "visibility", props.showHexes ? "visible" : "none");
    }
  }
  for (const id of ["pois-clusters", "pois-dots"]) {
    if (map.getLayer(id)) {
      map.setLayoutProperty(id, "visibility", props.showPois ? "visible" : "none");
    }
  }
}
