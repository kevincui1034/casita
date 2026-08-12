"use client";

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
    <div className="legend">
      <strong>Errands on foot, per hex</strong>
      {rows.map(([color, label]) => (
        <div className="row" key={label}>
          <span className="swatch" style={{ background: color, opacity: 0.55 }} />
          {label}
        </div>
      ))}
      <div className="row" style={{ marginTop: 2 }}>
        Grey areas: fewer than 5 mapped places — not scored.
      </div>
      <div className="toggles">
        <button
          type="button"
          className={`chip${showHexes ? " on" : ""}`}
          onClick={() => onToggleHexes(!showHexes)}
        >
          Hexes
        </button>
        <button
          type="button"
          className={`chip${showPois ? " on" : ""}`}
          onClick={() => onTogglePois(!showPois)}
        >
          Places
        </button>
      </div>
    </div>
  );
}
