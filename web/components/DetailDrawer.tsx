"use client";

import { ExternalLink, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import type { Listing } from "@/lib/types";
import { DOG_LABELS } from "@/lib/types";
import { fmtDist, fmtPrice, walkMinutes } from "@/lib/toGeojson";

const LIV_ROWS: Array<[string, string[]]> = [
  ["grocery", ["supermarket", "grocery"]],
  ["park", ["park", "dog_park"]],
  ["transit", ["transit"]],
  ["pharmacy", ["pharmacy"]],
];

function KeyCell({ children }: { children: React.ReactNode }) {
  return (
    <TableCell className="w-24 py-2 pr-2 pl-0 align-top text-[10px] font-semibold tracking-wider whitespace-nowrap text-muted-foreground uppercase">
      {children}
    </TableCell>
  );
}

function ValCell({ children }: { children: React.ReactNode }) {
  return <TableCell className="px-0 py-1.5 text-[13px]">{children}</TableCell>;
}

export default function DetailDrawer({
  listing: l,
  onClose,
}: {
  listing: Listing;
  onClose: () => void;
}) {
  const liv = l.livability;
  const cafes = liv
    ? (liv.cats.cafe?.n800 ?? 0) + (liv.cats.bakery?.n800 ?? 0)
    : 0;

  return (
    <aside
      data-drawer
      className="absolute inset-y-0 right-0 z-30 w-[min(430px,92vw)] border-l bg-card shadow-xl"
      aria-label="Listing detail"
    >
      <Button
        type="button"
        variant="outline"
        size="icon"
        onClick={onClose}
        aria-label="Close"
        className="absolute top-3 right-4 z-10 size-8 rounded-full bg-card"
      >
        <X />
      </Button>
      <ScrollArea className="h-full">
        <div className="flex flex-col gap-3 p-4">
          <h2 className="pr-10 text-lg leading-snug font-semibold">
            {fmtPrice(l.price)}/mo — {l.address ?? l.title ?? l.key}
          </h2>
          {l.photos.length > 0 && (
            <div className="flex snap-x gap-1.5 overflow-x-auto">
              {l.photos.map((p) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={p}
                  src={p}
                  alt=""
                  loading="lazy"
                  referrerPolicy="no-referrer"
                  className="h-42 snap-start rounded-md bg-muted"
                />
              ))}
            </div>
          )}
          {l.blurb && (
            <p className="text-[13.5px] text-muted-foreground">{l.blurb}</p>
          )}
          <Table>
            <TableBody>
              <TableRow>
                <KeyCell>size</KeyCell>
                <ValCell>
                  {[
                    l.beds ? `${l.beds} bd` : null,
                    l.baths ? `${l.baths} ba` : null,
                    l.sqft ? `${l.sqft.toLocaleString()} sqft` : null,
                  ]
                    .filter(Boolean)
                    .join(" · ") || "?"}
                </ValCell>
              </TableRow>
              {l.dog_policy && (
                <TableRow>
                  <KeyCell>dogs</KeyCell>
                  <ValCell>
                    <Badge
                      className={cn(
                        "border-transparent px-1.5 py-0 text-[10px] font-semibold uppercase",
                        l.dog_policy === "no_dogs"
                          ? "bg-red-100 text-red-700"
                          : "bg-emerald-100 text-emerald-700",
                      )}
                    >
                      {DOG_LABELS[l.dog_policy]}
                    </Badge>
                  </ValCell>
                </TableRow>
              )}
              {l.parking && (
                <TableRow>
                  <KeyCell>parking</KeyCell>
                  <ValCell>{l.parking}</ValCell>
                </TableRow>
              )}
              {l.laundry && (
                <TableRow>
                  <KeyCell>laundry</KeyCell>
                  <ValCell>{l.laundry}</ValCell>
                </TableRow>
              )}
              {(l.has_yard || l.yard_note) && (
                <TableRow>
                  <KeyCell>yard</KeyCell>
                  <ValCell>{l.yard_note ?? "yes"}</ValCell>
                </TableRow>
              )}
              {l.quality && (
                <TableRow>
                  <KeyCell>photos say</KeyCell>
                  <ValCell>
                    {Object.entries(l.quality)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(" · ")}
                  </ValCell>
                </TableRow>
              )}
              {l.walk &&
                (["trail", "beach", "bakery", "sf"] as const).map(
                  (k) =>
                    l.walk?.[k] && (
                      <TableRow key={k}>
                        <KeyCell>{k === "sf" ? "to SF" : k}</KeyCell>
                        <ValCell>
                          {l.walk[k]!.min} min {l.walk.mode} · {l.walk[k]!.name}
                        </ValCell>
                      </TableRow>
                    ),
                )}
            </TableBody>
          </Table>

          {liv && (
            <>
              <h3 className="text-sm font-semibold">
                Errands: {liv.points}/4 on foot · {liv.verdict}
                {l.is_marin ? " (drive-normal area)" : ""}
              </h3>
              <Table>
                <TableBody>
                  {LIV_ROWS.map(([label, cats]) => {
                    const best = cats
                      .map((c) => liv.cats[c])
                      .filter((s) => s && s.nearest_m !== null)
                      .sort((a, b) => a.nearest_m! - b.nearest_m!)[0];
                    if (!best) return null;
                    return (
                      <TableRow key={label}>
                        <KeyCell>{label}</KeyCell>
                        <ValCell>
                          {fmtDist(best.nearest_m)} (~{walkMinutes(best.nearest_m!)}{" "}
                          min){best.name ? ` · ${best.name}` : ""}
                        </ValCell>
                      </TableRow>
                    );
                  })}
                  {cafes > 0 && (
                    <TableRow>
                      <KeyCell>cafes</KeyCell>
                      <ValCell>{cafes} within a 10 min walk</ValCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </>
          )}

          <Button asChild variant="outline" className="mt-1 w-full">
            <a href={l.url} target="_blank" rel="noopener noreferrer">
              View on {l.source} <ExternalLink />
            </a>
          </Button>
        </div>
      </ScrollArea>
    </aside>
  );
}
