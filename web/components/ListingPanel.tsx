"use client";

import { useEffect, useRef } from "react";
import type { Listing } from "@/lib/types";
import ListingCard from "./ListingCard";

export default function ListingPanel({
  listings,
  selectedKey,
  hoverKey,
  onSelectKey,
  onHoverKey,
}: {
  listings: Listing[];
  selectedKey: string | null;
  hoverKey: string | null;
  onSelectKey: (key: string) => void;
  onHoverKey: (key: string | null) => void;
}) {
  const ref = useRef<HTMLElement>(null);

  // Keep the selected card in view when selection comes from the map.
  useEffect(() => {
    if (!selectedKey || !ref.current) return;
    ref.current
      .querySelector(`[data-key="${CSS.escape(selectedKey)}"]`)
      ?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selectedKey]);

  // Native overflow scroll on purpose. The shadcn/Radix ScrollArea positions
  // its thumb from JS scroll events, which visibly lags on a long list; the
  // global thin-scrollbar CSS keeps the minimal look at native speed.
  return (
    <aside
      ref={ref}
      className="flex w-100 min-w-75 flex-col border-r bg-background max-md:h-[45%] max-md:w-full max-md:border-t max-md:border-r-0"
    >
      <div className="px-3.5 pt-2.5 pb-1 text-xs text-muted-foreground">
        {listings.length} listing{listings.length === 1 ? "" : "s"}, ranked
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="flex flex-col gap-2.5 p-2.5 pt-1">
          {listings.map((l) => (
            <ListingCard
              key={l.key}
              listing={l}
              selected={l.key === selectedKey}
              hovered={l.key === hoverKey}
              onSelectKey={onSelectKey}
              onHoverKey={onHoverKey}
            />
          ))}
        </div>
      </div>
    </aside>
  );
}
