import { useEffect, useMemo, useRef, useState } from "react";
import Graph from "graphology";
import forceAtlas2 from "graphology-layout-forceatlas2";
import Sigma from "sigma";
import type { NodeHoverDrawingFunction } from "sigma/rendering";
import { api, type GraphData, type RepoStats } from "../api";
import type { Tab } from "../App";
import { ms, short } from "../components/bits";

/* Sigma paints on a WebGL canvas and needs literals, so the two signal
   colours of styles.css (indigo = imports, vermilion = co-change) and the
   directory hues are mirrored here, once per theme. */
const DARK = window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;

const DIR_COLORS = DARK
  ? ["#6fa8dc", "#7cc08a", "#b08cb5", "#e8674a", "#d9a520",
     "#7fb3c4", "#c49a6f", "#9db56f"]
  : ["#1e4f7a", "#2f6b3a", "#6d4470", "#b4331c", "#9a6b08",
     "#3f6b7d", "#7a5230", "#4a5a2f"];
const STATIC_EDGE = DARK ? "#6fa8dcaa" : "#1e4f7aaa";
const TEMPORAL_EDGE = DARK ? "#e8674acc" : "#b4331ccc";
const IDLE_EDGE = DARK ? "#8d847166" : "#8d847188";

/* Sigma's stock hover paints a white card, which disappears on the dark
   ground; this is the same card in the page's own colours. */
const drawNodeHover: NodeHoverDrawingFunction = (ctx, data, settings) => {
  const size = settings.labelSize;
  ctx.font = `${settings.labelWeight} ${size}px ${settings.labelFont}`;
  const label = data.label ?? "";
  const r = data.size + 2;
  ctx.fillStyle = DARK ? "#1d1a15" : "#fbf9f3";
  ctx.strokeStyle = DARK ? "#f4eee1" : "#191713";
  ctx.lineWidth = 1;
  if (label) {
    const w = ctx.measureText(label).width;
    ctx.beginPath();
    ctx.rect(data.x + r, data.y - size, w + 10, size + 8);
    ctx.fill();
    ctx.stroke();
  }
  ctx.beginPath();
  ctx.arc(data.x, data.y, r, 0, Math.PI * 2);
  ctx.closePath();
  ctx.fill();
  if (label) {
    ctx.fillStyle = DARK ? "#f4eee1" : "#191713";
    ctx.fillText(label, data.x + r + 5, data.y + size / 2 + 1);
  }
};

function colorFor(dir: string) {
  let h = 0;
  for (let i = 0; i < dir.length; i++) h = (h * 31 + dir.charCodeAt(i)) | 0;
  return DIR_COLORS[Math.abs(h) % DIR_COLORS.length];
}

const DAY = 86400;
const fmt = (ts: number) =>
  new Date(ts * 1000).toLocaleDateString(undefined,
    { year: "numeric", month: "short" });

/** Decayed co-change weight at `cutoff` — the same formula the server uses
 *  in chrono.temporal_edges (verified in demo/tests/test_parity.py). */
function decayed(stamps: number[], cutoff: number, lambda: number) {
  let w = 0;
  for (let i = 0; i < stamps.length; i++) {
    const t = stamps[i];
    if (t > cutoff) break;
    w += Math.exp(-lambda * Math.max(0, (cutoff - t) / DAY));
  }
  return w;
}

export default function GraphView({ indexId, repo, file, onPick, onOpen }: {
  indexId: string;
  repo: RepoStats;
  file: string | null;
  onPick: (f: string) => void;
  onOpen: (f: string, tab: Tab) => void;
}) {
  const holder = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);

  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [limit, setLimit] = useState(120);
  const [focused, setFocused] = useState<string | null>(null);
  const [showStatic, setShowStatic] = useState(true);
  const [showTemporal, setShowTemporal] = useState(true);
  const [cutoff, setCutoff] = useState<number>(repo.base_ts);
  const [playing, setPlaying] = useState(false);
  const [tip, setTip] = useState<{ x: number; y: number; html: string } | null>(null);
  const [active, setActive] = useState(0);

  // ---- data ---------------------------------------------------------
  useEffect(() => {
    let alive = true;
    setLoading(true);
    api.graph(indexId, { focus: focused ?? undefined, limit })
      .then((d) => { if (alive) { setData(d); setCutoff(d.base_ts); setErr(null); } })
      .catch((e) => alive && setErr(String(e)))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [indexId, focused, limit]);

  const span = data?.span ?? repo.span;

  // ---- build the sigma graph ----------------------------------------
  useEffect(() => {
    if (!data || !holder.current) return;
    const g = new Graph({ multi: false, type: "undirected" });
    const n = data.nodes.length;
    data.nodes.forEach((node, i) => {
      const a = (2 * Math.PI * i) / Math.max(1, n);
      g.addNode(node.file, {
        label: short(node.file),
        x: Math.cos(a) * 10, y: Math.sin(a) * 10,
        size: 3 + 9 * Math.sqrt(node.w),
        color: colorFor(node.dir),
        dir: node.dir, changes: node.changes, imports: node.imports,
        involvement: node.w,
      });
    });
    for (const e of data.static) {
      if (g.hasNode(e.a) && g.hasNode(e.b) && !g.hasEdge(e.a, e.b))
        g.addEdge(e.a, e.b, { kind: "static", size: 1, color: STATIC_EDGE });
    }
    for (const e of data.temporal) {
      if (!g.hasNode(e.a) || !g.hasNode(e.b)) continue;
      const attrs = { kind: "temporal", count: e.count, last: e.last,
                      ts: e.ts, size: 1, color: TEMPORAL_EDGE };
      if (g.hasEdge(e.a, e.b)) {
        g.setEdgeAttribute(e.a, e.b, "kind", "both");
        g.mergeEdgeAttributes(e.a, e.b, attrs);
      } else {
        g.addEdge(e.a, e.b, attrs);
      }
    }
    forceAtlas2.assign(g, {
      iterations: n > 400 ? 120 : 260,
      settings: { ...forceAtlas2.inferSettings(g), gravity: 1.2,
                  scalingRatio: 12, slowDown: 3 },
    });

    const renderer = new Sigma(g, holder.current, {
      enableEdgeEvents: true,
      renderEdgeLabels: false,
      labelDensity: 0.5,
      labelGridCellSize: 70,
      labelRenderedSizeThreshold: 6,
      labelFont: '"IBM Plex Mono", ui-monospace, monospace',
      labelSize: 11,
      labelWeight: "500",
      labelColor: { color: DARK ? "#f4eee1" : "#191713" },
      defaultDrawNodeHover: drawNodeHover,
      defaultEdgeColor: IDLE_EDGE,
      zIndex: true,
    });
    graphRef.current = g;
    sigmaRef.current = renderer;

    // sigma reports viewport coordinates relative to its container
    const page = (e: { x: number; y: number }) => {
      const r = holder.current?.getBoundingClientRect();
      return { x: (r?.left ?? 0) + e.x, y: (r?.top ?? 0) + e.y };
    };

    renderer.on("enterNode", ({ node, event }) => {
      const a = g.getNodeAttributes(node);
      setTip({
        ...page(event),
        html: `<b>${node}</b><br/>co-change involvement ${a.involvement}` +
              ` · ${a.changes} commits · ${a.imports} import links` +
              `<br/><span class="hint">click: impact set · shift-click: focus here</span>`,
      });
    });
    renderer.on("leaveNode", () => setTip(null));
    renderer.on("enterEdge", ({ edge, event }) => {
      const a = g.getEdgeAttributes(edge);
      const [s, t] = g.extremities(edge);
      const w = a.ts ? decayed(a.ts, cutoffRef.current, data.lambda_per_day) : 0;
      setTip({
        ...page(event),
        html: `<b>${short(s)} ↔ ${short(t)}</b><br/>` +
              (a.kind === "static"
                ? "import relation (parsed from code)"
                : `co-changed ×${a.count}, last ${fmt(a.last)}<br/>` +
                  `decayed weight at cutoff: ${w.toFixed(2)}` +
                  (a.kind === "both" ? "<br/>also connected by an import" : "")),
      });
    });
    renderer.on("leaveEdge", () => setTip(null));
    renderer.on("clickNode", ({ node, event }) => {
      if (event.original.shiftKey) setFocused(node);
      else { onPick(node); onOpen(node, "impact"); }
    });

    return () => { renderer.kill(); sigmaRef.current = null; graphRef.current = null; };
  }, [data, onPick, onOpen]);

  // ---- timeline -----------------------------------------------------
  const cutoffRef = useRef(cutoff);
  useEffect(() => { cutoffRef.current = cutoff; }, [cutoff]);

  useEffect(() => {
    const g = graphRef.current;
    const renderer = sigmaRef.current;
    if (!g || !renderer || !data) return;
    let maxW = 0;
    const weights = new Map<string, number>();
    g.forEachEdge((edge, attrs) => {
      if (attrs.ts) {
        const w = decayed(attrs.ts as number[], cutoff, data.lambda_per_day);
        weights.set(edge, w);
        if (w > maxW) maxW = w;
      }
    });
    let count = 0;
    g.forEachEdge((edge, attrs) => {
      const isTemporal = attrs.kind !== "static";
      const w = weights.get(edge) ?? 0;
      if (isTemporal) {
        const alive = w > 0.05 && showTemporal;
        if (alive) count++;
        g.setEdgeAttribute(edge, "hidden",
          !alive && !(attrs.kind === "both" && showStatic));
        g.setEdgeAttribute(edge, "size", 0.6 + 4 * (maxW ? w / maxW : 0));
        g.setEdgeAttribute(edge, "color",
          attrs.kind === "both" && !alive ? STATIC_EDGE : TEMPORAL_EDGE);
      } else {
        g.setEdgeAttribute(edge, "hidden", !showStatic);
        g.setEdgeAttribute(edge, "size", 0.9);
      }
    });
    setActive(count);
    renderer.refresh();
  }, [cutoff, showStatic, showTemporal, data]);

  useEffect(() => {
    if (!playing) return;
    const step = Math.max(DAY * 20, (span[1] - span[0]) / 90);
    const id = window.setInterval(() => {
      setCutoff((c) => (c >= span[1] ? span[0] : Math.min(span[1], c + step)));
    }, 90);
    return () => window.clearInterval(id);
  }, [playing, span]);

  // ---- highlight the selected file -----------------------------------
  useEffect(() => {
    const g = graphRef.current;
    if (!g || !file || !g.hasNode(file)) return;
    g.forEachNode((n, a) => {
      g.setNodeAttribute(n, "highlighted", n === file);
      g.setNodeAttribute(n, "zIndex", n === file ? 2 : 1);
      if (n === file) g.setNodeAttribute(n, "size", Math.max(10, a.size));
    });
    sigmaRef.current?.refresh();
  }, [file, data]);

  const dirs = useMemo(() => {
    const seen = new Map<string, number>();
    for (const n of data?.nodes ?? [])
      seen.set(n.dir, (seen.get(n.dir) ?? 0) + 1);
    return [...seen.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
  }, [data]);

  return (
    <>
      <div className="card">
        <div className="row">
          <label className="check">
            <input type="checkbox" checked={showStatic}
                   onChange={(e) => setShowStatic(e.target.checked)} />
            imports
          </label>
          <label className="check">
            <input type="checkbox" checked={showTemporal}
                   onChange={(e) => setShowTemporal(e.target.checked)} />
            co-change (decayed)
          </label>
          <label className="check">
            nodes
            <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              {[60, 120, 250, 500, 900].map((v) => <option key={v}>{v}</option>)}
            </select>
          </label>
          {focused && (
            <span className="chip">
              focused on <b className="mono">{short(focused)}</b>{" "}
              <button className="ghost" style={{ padding: "0 6px" }}
                      onClick={() => setFocused(null)}>×</button>
            </span>
          )}
          <span className="spacer" />
          <span className="chip">active co-change edges <b>{active}</b></span>
          <span className="chip">subgraph in <b>{ms(data?.ms)}</b></span>
          {loading && <span className="hint">building…</span>}
        </div>

        <div className="timeline">
          <div className="row tight">
            <button className="ghost" onClick={() => setPlaying(!playing)}>
              {playing ? "❚❚ pause" : "▶ play history"}
            </button>
            <span className="chip">history up to <b>{fmt(cutoff)}</b></span>
            <span className="hint">
              weight = Σ exp(−λ·age), λ = 1/90 per day — the same decay the
              engine uses
            </span>
          </div>
          <input type="range" min={span[0]} max={span[1]} step={DAY}
                 value={cutoff}
                 onChange={(e) => { setPlaying(false); setCutoff(Number(e.target.value)); }} />
          <div className="marks">
            <span>{fmt(span[0])}</span><span>{fmt(span[1])}</span>
          </div>
        </div>

        <div className="graph-wrap" style={{ marginTop: 12 }}>
          <div className="graph-canvas" ref={holder} />
          <div className="graph-legend">
            <span><span className="sw" />import edge</span>
            <span><span className="sw t" />co-change edge (width = decayed weight)</span>
            <span>node size = co-change involvement</span>
            {dirs.map(([d, c]) => (
              <span key={d} style={{ color: colorFor(d) }}>■ {d || "/"} ({c})</span>
            ))}
          </div>
        </div>
        {err && <div className="err">{err}</div>}
        <div className="hint" style={{ marginTop: 8 }}>
          Click a node for its impact set, shift-click to re-centre the graph on
          its neighbourhood. Every edge here is mined from this repository —
          imports parsed from the tree at{" "}
          <span className="mono">{repo.rev.slice(0, 7)}</span>, co-change from
          the commits in that revision's ancestry.
        </div>
      </div>
      {tip && (
        <div className="tooltip" style={{ left: tip.x + 14, top: tip.y + 12 }}
             dangerouslySetInnerHTML={{ __html: tip.html }} />
      )}
    </>
  );
}
