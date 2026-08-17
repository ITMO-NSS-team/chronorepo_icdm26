import type { Chip } from "../api";

export const short = (p: string) => p.split("/").pop() || p;

export function Path({ file }: { file: string }) {
  const i = file.lastIndexOf("/");
  return (
    <span className="path">
      {i >= 0 && <span className="dim">{file.slice(0, i + 1)}</span>}
      {file.slice(i + 1)}
    </span>
  );
}

export function EvidenceChips({ chips }: { chips: Chip[] }) {
  if (!chips?.length) return <span className="hint">—</span>;
  return (
    <span className="row tight">
      {chips.map((c, i) => {
        if (c.kind === "cochange")
          return (
            <span className="chip flat" key={i} title="mined from git history">
              co-changed with <b>{short(c.with)}</b> ×{c.count}
              {c.last ? `, last ${c.last}` : ""}
            </span>
          );
        if (c.kind === "import")
          return (
            <span className="chip flat" key={i} title="parsed from imports">
              import link to <b>{short(c.with)}</b>
            </span>
          );
        if (c.kind === "bridge")
          return (
            <span className="chip flat" key={i} title="two-hop path in the graph">
              bridge via <b>{short(c.via)}</b> ×{c.count}
            </span>
          );
        return (
          <span className="chip flat" key={i} title="personalized propagation">
            graph score <b>{c.score.toFixed(2)}</b>
          </span>
        );
      })}
    </span>
  );
}

export function Meter({ label, value, unit, tone }: {
  label: string; value: string | number; unit?: string; tone?: "win" | "warn";
}) {
  return (
    <span className={`chip${tone ? " " + tone : ""}`}>
      {label} <b>{value}</b>{unit ? ` ${unit}` : ""}
    </span>
  );
}

export function ms(v?: number) {
  if (v === undefined || v === null) return "–";
  return v >= 1000 ? `${(v / 1000).toFixed(1)} s` : `${Math.round(v)} ms`;
}

export function usd(v?: number | null) {
  if (v === null || v === undefined) return "n/a";
  if (v === 0) return "$0";
  if (v < 0.001) return `$${v.toFixed(5)}`;
  return `$${v.toFixed(4)}`;
}

export function Spinner({ label }: { label: string }) {
  return <span className="hint">{label}…</span>;
}
