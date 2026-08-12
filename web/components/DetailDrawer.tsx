"use client";

import type { Listing } from "@/lib/types";
import { DOG_LABELS } from "@/lib/types";
import { fmtDist, fmtPrice, walkMinutes } from "@/lib/toGeojson";

const LIV_ROWS: Array<[string, string[]]> = [
  ["grocery", ["supermarket", "grocery"]],
  ["park", ["park", "dog_park"]],
  ["transit", ["transit"]],
  ["pharmacy", ["pharmacy"]],
];

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
    <section className="drawer" aria-label="Listing detail">
      <button type="button" className="close" onClick={onClose} aria-label="Close">
        ×
      </button>
      <h2>
        {fmtPrice(l.price)}/mo — {l.address ?? l.title ?? l.key}
      </h2>
      {l.photos.length > 0 && (
        <div className="photos">
          {l.photos.map((p) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img key={p} src={p} alt="" loading="lazy" referrerPolicy="no-referrer" />
          ))}
        </div>
      )}
      {l.blurb && <p className="blurb">{l.blurb}</p>}
      <table>
        <tbody>
          <tr>
            <td className="k">size</td>
            <td>
              {[
                l.beds ? `${l.beds} bd` : null,
                l.baths ? `${l.baths} ba` : null,
                l.sqft ? `${l.sqft.toLocaleString()} sqft` : null,
              ]
                .filter(Boolean)
                .join(" · ") || "?"}
            </td>
          </tr>
          {l.dog_policy && (
            <tr>
              <td className="k">dogs</td>
              <td>{DOG_LABELS[l.dog_policy]}</td>
            </tr>
          )}
          {l.parking && (
            <tr>
              <td className="k">parking</td>
              <td>{l.parking}</td>
            </tr>
          )}
          {l.laundry && (
            <tr>
              <td className="k">laundry</td>
              <td>{l.laundry}</td>
            </tr>
          )}
          {(l.has_yard || l.yard_note) && (
            <tr>
              <td className="k">yard</td>
              <td>{l.yard_note ?? "yes"}</td>
            </tr>
          )}
          {l.quality && (
            <tr>
              <td className="k">photos say</td>
              <td>
                {Object.entries(l.quality)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(" · ")}
              </td>
            </tr>
          )}
          {l.walk &&
            (["trail", "beach", "bakery", "sf"] as const).map(
              (k) =>
                l.walk?.[k] && (
                  <tr key={k}>
                    <td className="k">{k === "sf" ? "to SF" : k}</td>
                    <td>
                      {l.walk[k]!.min} min {l.walk.mode} · {l.walk[k]!.name}
                    </td>
                  </tr>
                ),
            )}
        </tbody>
      </table>

      {liv && (
        <>
          <h2 style={{ fontSize: 14.5 }}>
            Errands: {liv.points}/4 on foot · {liv.verdict}
            {l.is_marin ? " (drive-normal area)" : ""}
          </h2>
          <table>
            <tbody>
              {LIV_ROWS.map(([label, cats]) => {
                const best = cats
                  .map((c) => liv.cats[c])
                  .filter((s) => s && s.nearest_m !== null)
                  .sort((a, b) => a.nearest_m! - b.nearest_m!)[0];
                if (!best) return null;
                return (
                  <tr key={label}>
                    <td className="k">{label}</td>
                    <td>
                      {fmtDist(best.nearest_m)} (~{walkMinutes(best.nearest_m!)} min)
                      {best.name ? ` · ${best.name}` : ""}
                    </td>
                  </tr>
                );
              })}
              {cafes > 0 && (
                <tr>
                  <td className="k">cafes</td>
                  <td>{cafes} within a 10 min walk</td>
                </tr>
              )}
            </tbody>
          </table>
        </>
      )}

      <a
        className="src-link"
        href={l.url}
        target="_blank"
        rel="noopener noreferrer"
      >
        View on {l.source} ↗
      </a>
    </section>
  );
}
