"use client";

import { useEffect, useRef } from "react";
import type { Listing } from "@/lib/types";
import ListingCard from "./ListingCard";

export default function ListingPanel({
  listings,
  selectedKey,
  hoverKey,
  onSelect,
  onHover,
}: {
  listings: Listing[];
  selectedKey: string | null;
  hoverKey: string | null;
  onSelect: (key: string | null) => void;
  onHover: (key: string | null) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  // Keep the selected card in view when selection comes from the map.
  useEffect(() => {
    if (!selectedKey || !ref.current) return;
    ref.current
      .querySelector(`[data-key="${CSS.escape(selectedKey)}"]`)
      ?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selectedKey]);

  return (
    <aside className="panel" ref={ref}>
      <div className="count-line">
        {listings.length} listing{listings.length === 1 ? "" : "s"}, ranked
      </div>
      {listings.map((l) => (
        <ListingCard
          key={l.key}
          listing={l}
          selected={l.key === selectedKey}
          hovered={l.key === hoverKey}
          onClick={() => onSelect(l.key === selectedKey ? null : l.key)}
          onHover={onHover}
        />
      ))}
    </aside>
  );
}
