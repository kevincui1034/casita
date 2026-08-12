"use client";

import type { Filters as FiltersT } from "@/lib/types";

const PRICE_STOPS = [4000, 6000, 8000];

function Chip({
  on,
  label,
  onClick,
}: {
  on: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button type="button" className={`chip${on ? " on" : ""}`} onClick={onClick}>
      {label}
    </button>
  );
}

export default function FilterBar({
  filters,
  onChange,
}: {
  filters: FiltersT;
  onChange: (f: FiltersT) => void;
}) {
  const toggle = <K extends keyof FiltersT>(key: K, value: FiltersT[K]) =>
    onChange({ ...filters, [key]: filters[key] === value ? null : value });

  return (
    <div className="filters">
      <span className="chip-group">
        <span className="label">fit</span>
        <Chip on={filters.severity === "ok"} label="Strong fit" onClick={() => toggle("severity", "ok")} />
        <Chip on={filters.severity === "concerns"} label="Has concerns" onClick={() => toggle("severity", "concerns")} />
        <Chip on={filters.severity === "filtered"} label="Show gated" onClick={() => toggle("severity", "filtered")} />
      </span>
      <span className="chip-group">
        <span className="label">dogs</span>
        <Chip on={filters.dogPolicy === "large_ok"} label="Large dogs OK" onClick={() => toggle("dogPolicy", "large_ok")} />
        <Chip on={filters.dogPolicy === "dogs_ok"} label="Dogs OK" onClick={() => toggle("dogPolicy", "dogs_ok")} />
      </span>
      <span className="chip-group">
        <span className="label">price</span>
        {PRICE_STOPS.map((p) => (
          <Chip
            key={p}
            on={filters.maxPrice === p}
            label={`≤ $${p / 1000}k`}
            onClick={() => toggle("maxPrice", p)}
          />
        ))}
      </span>
      <span className="chip-group">
        <span className="label">errands</span>
        <Chip on={filters.verdict === "walkable"} label="Walkable" onClick={() => toggle("verdict", "walkable")} />
        <Chip on={filters.verdict === "mixed"} label="Mixed" onClick={() => toggle("verdict", "mixed")} />
      </span>
    </div>
  );
}
