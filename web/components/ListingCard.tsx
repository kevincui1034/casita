"use client";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Listing } from "@/lib/types";
import { DOG_LABELS } from "@/lib/types";
import { fmtPrice } from "@/lib/toGeojson";

const SEV_STYLES: Record<string, string> = {
  ok: "bg-emerald-100 text-emerald-700",
  concerns: "bg-amber-100 text-amber-700",
  filtered: "bg-red-100 text-red-700",
};

const tag = "border-transparent px-1.5 py-0 text-[10px] font-semibold tracking-wide uppercase";

export default function ListingCard({
  listing: l,
  selected,
  hovered,
  onClick,
  onHover,
}: {
  listing: Listing;
  selected: boolean;
  hovered: boolean;
  onClick: () => void;
  onHover: (key: string | null) => void;
}) {
  const bb = [
    l.beds ? `${l.beds} bd` : null,
    l.baths ? `${l.baths} ba` : null,
    l.sqft ? `${l.sqft.toLocaleString()} sqft` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  const dogStyle =
    l.dog_policy === "no_dogs"
      ? "bg-red-100 text-red-700"
      : l.dog_policy === "large_ok" || l.dog_policy === "dogs_ok"
        ? "bg-emerald-100 text-emerald-700"
        : "bg-muted text-muted-foreground";

  const walkBit = l.walk?.trail
    ? `${l.walk.trail.min} min ${l.walk.mode} · ${l.walk.trail.name}`
    : null;

  return (
    <Card
      data-key={l.key}
      onClick={onClick}
      onMouseEnter={() => onHover(l.key)}
      onMouseLeave={() => onHover(null)}
      className={cn(
        "flex-row gap-3 rounded-lg p-2.5 shadow-none transition-colors",
        "cursor-pointer hover:border-primary/60",
        (hovered || selected) && "border-primary/60",
        selected && "border-primary ring-1 ring-primary",
      )}
    >
      {l.photos[0] ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={l.photos[0]}
          alt=""
          loading="lazy"
          referrerPolicy="no-referrer"
          className="size-23 shrink-0 rounded-md bg-muted object-cover"
        />
      ) : (
        <div className="size-23 shrink-0 rounded-md bg-muted" />
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <div className="text-[15px] font-bold">
          #{l.rank} · {fmtPrice(l.price)}
          <span className="font-medium text-muted-foreground">/mo</span>
        </div>
        <div className="truncate text-xs text-muted-foreground">
          {l.address ?? l.title ?? l.key}
        </div>
        <div className="truncate text-xs text-muted-foreground">
          {[bb, l.hood].filter(Boolean).join(" — ")}
        </div>
        {walkBit && (
          <div className="truncate text-xs text-muted-foreground">{walkBit}</div>
        )}
        <div className="mt-1 flex flex-wrap gap-1">
          {l.severity && (
            <Badge className={cn(tag, SEV_STYLES[l.severity])}>{l.severity}</Badge>
          )}
          {l.dog_policy && (
            <Badge className={cn(tag, dogStyle)}>{DOG_LABELS[l.dog_policy]}</Badge>
          )}
          {l.livability?.verdict === "walkable" && !l.is_marin && (
            <Badge className={cn(tag, "bg-emerald-100 text-emerald-700")}>
              {l.livability.points}/4 errands on foot
            </Badge>
          )}
        </div>
      </div>
    </Card>
  );
}
