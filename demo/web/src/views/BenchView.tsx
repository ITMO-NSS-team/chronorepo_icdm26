import { useEffect, useMemo, useState } from "react";
import { api } from "../api";

type Point = { label: string; acc5: number; usd: number; ours: boolean };

/* Two-series categorical palette, validated for both themes
   (light #2a78d6/#eb6834, dark #3987e5/#d95926): CVD ΔE ≥ 24, contrast ≥ 3:1.
   Identity is carried by shape and direct labels as well as hue. */
function Pareto({ title, caption, points }: {
  title: string; caption: string; points: Point[];
}) {
  const [hover, setHover] = useState<Point | null>(null);
  const W = 720, H = 360, M = { t: 16, r: 18, b: 46, l: 46 };
  const FLOOR = 0.0004;                     // "~$0" lives on the left edge
  const xs = (v: number) => Math.log10(Math.max(v || FLOOR, FLOOR));
  const x0 = xs(FLOOR), x1 = Math.log10(1);
  const px = (v: number) =>
    M.l + ((xs(v) - x0) / (x1 - x0)) * (W - M.l - M.r);
  const py = (v: number) => M.t + (1 - (v - 30) / 60) * (H - M.t - M.b);

  const ticks = [FLOOR, 0.001, 0.01, 0.1, 1];
  const tickLabel = (v: number) =>
    v === FLOOR ? "~$0" : v < 0.01 ? `$${v.toFixed(3)}` :
    v < 1 ? `$${v.toFixed(2)}` : "$1";

  return (
    <div className="card">
      <h3 style={{ margin: "0 0 4px" }}>{title}</h3>
      <p className="hint" style={{ margin: "0 0 10px" }}>{caption}</p>
      <div style={{ overflowX: "auto" }}>
        <svg className="pareto" viewBox={`0 0 ${W} ${H}`} role="img"
             aria-label={title} style={{ minWidth: 620 }}>
          {[40, 50, 60, 70, 80, 90].map((v) => (
            <g key={v}>
              <line x1={M.l} x2={W - M.r} y1={py(v)} y2={py(v)}
                    stroke="var(--grid)" strokeWidth="1" />
              <text x={M.l - 8} y={py(v) + 4} textAnchor="end"
                    fontSize="11" fill="var(--muted)">{v}</text>
            </g>
          ))}
          {ticks.map((t) => (
            <text key={t} x={px(t)} y={H - M.b + 18} textAnchor="middle"
                  fontSize="11" fill="var(--muted)">{tickLabel(t)}</text>
          ))}
          <text x={(W - M.l) / 2} y={H - 8} textAnchor="middle" fontSize="11.5"
                fill="var(--ink-2)">cost per issue (log scale)</text>
          <text x={14} y={M.t + 8} fontSize="11.5" fill="var(--ink-2)"
                transform={`rotate(-90 14 ${M.t + 8})`}
                textAnchor="end">strict Acc@5, %</text>

          {points.map((p) => {
            const cx = px(p.usd), cy = py(p.acc5);
            const color = p.ours ? "var(--blue)" : "var(--orange)";
            const right = cx < W - 190;
            return (
              <g key={p.label}
                 onMouseEnter={() => setHover(p)} onMouseLeave={() => setHover(null)}>
                <circle cx={cx} cy={cy} r={hover === p ? 8 : 6} fill={color}
                        stroke="var(--surface)" strokeWidth="2"
                        fillOpacity={p.ours ? 1 : 0.35} />
                <text x={right ? cx + 11 : cx - 11} y={cy + 4} fontSize="11.5"
                      textAnchor={right ? "start" : "end"}
                      fill={hover === p ? "var(--ink)" : "var(--ink-2)"}>
                  {p.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="chips">
        <span className="chip"><b style={{ color: "var(--blue)" }}>●</b> ChronoRepo (training-free)</span>
        <span className="chip"><b style={{ color: "var(--orange)" }}>○</b> published systems</span>
        {hover && (
          <span className="chip win">
            {hover.label}: Acc@5 <b>{hover.acc5}</b>,{" "}
            {hover.usd ? `$${hover.usd}` : "~$0"} per issue
          </span>
        )}
      </div>
    </div>
  );
}

export default function BenchView() {
  const [data, setData] = useState<Record<string, any> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.benchmarks().then(setData).catch((e) => setErr(String(e)));
  }, []);

  const lanes = useMemo(
    () => (data ? ["locbench_small", "locbench_heavy"] : []), [data]);

  if (err) return <div className="err">{err}</div>;
  if (!data) return <div className="card hint">loading…</div>;

  return (
    <>
      <Pareto title={data.pareto.title} caption={data.pareto.caption}
              points={data.pareto.points} />

      {lanes.map((k) => (
        <div className="card" key={k}>
          <h3 style={{ margin: "0 0 4px" }}>{data[k].title}</h3>
          <p className="hint" style={{ margin: "0 0 10px" }}>{data[k].caption}</p>
          <table className="bench-table">
            <thead>
              <tr><th>method</th><th className="n">Acc@5</th>
                  <th className="n">Acc@10</th><th>cost / issue</th></tr>
            </thead>
            <tbody>
              {data[k].rows.map((r: any) => (
                <tr key={r.name} className={r.ours ? "ours" : ""}>
                  <td>{r.name}</td>
                  <td className="n">{r.acc5.toFixed(1)}</td>
                  <td className="n">{r.acc10.toFixed(1)}</td>
                  <td>{r.cost}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      <div className="card">
        <h3 style={{ margin: "0 0 4px" }}>{data.swebench.title}</h3>
        <p className="hint" style={{ margin: "0 0 10px" }}>{data.swebench.caption}</p>
        <table className="bench-table">
          <thead>
            <tr><th>method</th>
              {data.swebench.columns.map((c: string) => (
                <th className="n" key={c}>{c}</th>))}
            </tr>
          </thead>
          <tbody>
            {data.swebench.rows.map((r: any) => (
              <tr key={r.name} className={r.ours ? "ours" : ""}>
                <td>{r.name}</td>
                {r.values.map((v: number, i: number) => (
                  <td className="n" key={i}>{v.toFixed(1)}</td>))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3 style={{ margin: "0 0 4px" }}>{data.ablation.title}</h3>
        <p className="hint" style={{ margin: "0 0 10px" }}>{data.ablation.caption}</p>
        <table className="bench-table">
          <thead>
            <tr><th>configuration</th><th className="n">Δ Acc@5</th>
                <th className="n">p</th></tr>
          </thead>
          <tbody>
            {data.ablation.rows.map((r: any) => (
              <tr key={r.name}>
                <td>{r.name}</td>
                <td className="n">{r.delta.toFixed(1)}</td>
                <td className="n">{r.p}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3 style={{ margin: "0 0 4px" }}>{data.impact.title}</h3>
        <p className="hint" style={{ margin: "0 0 10px" }}>{data.impact.caption}</p>
        <table className="bench-table">
          <thead><tr><th>method</th><th className="n">R@10</th></tr></thead>
          <tbody>
            {data.impact.rows.map((r: any) => (
              <tr key={r.name}>
                <td>{r.name}</td>
                <td className="n">{r.r10.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="hint">{data.source}</p>
    </>
  );
}
