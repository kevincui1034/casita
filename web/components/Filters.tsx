"use client";

import { Button } from "@/components/ui/button";
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
    <Button
      type="button"
      size="sm"
      variant={on ? "default" : "outline"}
      className="h-7 rounded-full px-3 text-xs font-medium"
      onClick={onClick}
    >
      {label}
    </Button>
  );
}

function GroupLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="mr-0.5 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
      {children}
    </span>
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
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-b bg-muted/40 px-4 py-2">
      <span className="inline-flex items-center gap-1.5">
        <GroupLabel>fit</GroupLabel>
        <Chip on={filters.severity === "ok"} label="Strong fit" onClick={() => toggle("severity", "ok")} />
        <Chip on={filters.severity === "concerns"} label="Has concerns" onClick={() => toggle("severity", "concerns")} />
        <Chip on={filters.severity === "filtered"} label="Show gated" onClick={() => toggle("severity", "filtered")} />
      </span>
      <span className="inline-flex items-center gap-1.5">
        <GroupLabel>dogs</GroupLabel>
        <Chip on={filters.dogPolicy === "large_ok"} label="Large dogs OK" onClick={() => toggle("dogPolicy", "large_ok")} />
        <Chip on={filters.dogPolicy === "dogs_ok"} label="Dogs OK" onClick={() => toggle("dogPolicy", "dogs_ok")} />
      </span>
      <span className="inline-flex items-center gap-1.5">
        <GroupLabel>price</GroupLabel>
        {PRICE_STOPS.map((p) => (
          <Chip
            key={p}
            on={filters.maxPrice === p}
            label={`≤ $${p / 1000}k`}
            onClick={() => toggle("maxPrice", p)}
          />
        ))}
      </span>
      <span className="inline-flex items-center gap-1.5">
        <GroupLabel>errands</GroupLabel>
        <Chip on={filters.verdict === "walkable"} label="Walkable" onClick={() => toggle("verdict", "walkable")} />
        <Chip on={filters.verdict === "mixed"} label="Mixed" onClick={() => toggle("verdict", "mixed")} />
      </span>
    </div>
  );
}
