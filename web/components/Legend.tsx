"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function Legend({
  hexColors,
  showHexes,
  showPois,
  onToggleHexes,
  onTogglePois,
}: {
  hexColors: string[];
  showHexes: boolean;
  showPois: boolean;
  onToggleHexes: (v: boolean) => void;
  onTogglePois: (v: boolean) => void;
}) {
  const rows: Array<[string, string]> = [
    [hexColors[3], "4/4 errands on foot"],
    [hexColors[2], "3/4 — walkable"],
    [hexColors[1], "2/4 — mixed"],
    [hexColors[0], "0–1 — car-dependent"],
  ];
  return (
    <Card className="absolute bottom-7 left-2.5 z-20 max-w-60 gap-1.5 rounded-lg p-3 text-[11.5px] text-muted-foreground shadow-md">
      <div className="font-semibold text-foreground">Errands on foot, per hex</div>
      {rows.map(([color, label]) => (
        <div className="flex items-center gap-2" key={label}>
          <span
            className="size-3 shrink-0 rounded-[3px] opacity-60"
            style={{ background: color }}
          />
          {label}
        </div>
      ))}
      <div className="mt-0.5">
        Grey areas: fewer than 5 mapped places — not scored.
      </div>
      <div className="mt-1 flex flex-wrap gap-1.5">
        <Button
          type="button"
          size="sm"
          variant={showHexes ? "default" : "outline"}
          className="h-6.5 rounded-full px-2.5 text-[11px]"
          onClick={() => onToggleHexes(!showHexes)}
        >
          Hexes
        </Button>
        <Button
          type="button"
          size="sm"
          variant={showPois ? "default" : "outline"}
          className="h-6.5 rounded-full px-2.5 text-[11px]"
          onClick={() => onTogglePois(!showPois)}
        >
          Places
        </Button>
      </div>
    </Card>
  );
}
