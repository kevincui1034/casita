"use client";

import type { Listing } from "@/lib/types";
import { DOG_LABELS } from "@/lib/types";
import { fmtPrice } from "@/lib/toGeojson";

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

  const dogClass =
    l.dog_policy === "no_dogs"
      ? "bad"
      : l.dog_policy === "large_ok" || l.dog_policy === "dogs_ok"
        ? "good"
        : "";

  const walkBit = l.walk?.trail
    ? `${l.walk.trail.min} min ${l.walk.mode} · ${l.walk.trail.name}`
    : null;

  return (
    <article
      className={`card${selected ? " selected" : ""}${hovered ? " hover" : ""}`}
      data-key={l.key}
      onClick={onClick}
      onMouseEnter={() => onHover(l.key)}
      onMouseLeave={() => onHover(null)}
    >
      {l.photos[0] ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={l.photos[0]}
          alt=""
          loading="lazy"
          referrerPolicy="no-referrer"
        />
      ) : (
        <div className="noimg" />
      )}
      <div className="body">
        <div className="price">
          #{l.rank} · {fmtPrice(l.price)}
          <small>/mo</small>
        </div>
        <div className="addr">{l.address ?? l.title ?? l.key}</div>
        <div className="addr">
          {[bb, l.hood].filter(Boolean).join(" — ")}
        </div>
        {walkBit && <div className="addr">{walkBit}</div>}
        <div className="tags">
          {l.severity && <span className={`badge sev-${l.severity}`}>{l.severity}</span>}
          {l.dog_policy && (
            <span className={`badge dog ${dogClass}`}>{DOG_LABELS[l.dog_policy]}</span>
          )}
          {l.livability?.verdict === "walkable" && !l.is_marin && (
            <span className="badge liv">
              {l.livability.points}/4 errands on foot
            </span>
          )}
        </div>
      </div>
    </article>
  );
}
