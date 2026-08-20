import { useEffect, useState } from "react";
import { api, type ImpactData } from "../api";
import { EvidenceChips, Path, ms } from "../components/bits";

/** R@10 from the paper's impact-set experiment (2,309 held-out commits,
 *  12 projects). ROSE winning is a reported negative result, not a bug. */
const PAPER_R10: Record<string, { label: string; r10: string; note?: string }> = {
  rose: { label: "ROSE (raw co-change)", r10: "0.629" },
  temporal_ppr: { label: "propagation over history", r10: "0.577",
                  note: "personalized propagation, temporal layer only" },
  static_ppr: { label: "propagation over imports", r10: "0.396",
                note: "structure only: history dominates it" },
  hybrid_a25: { label: "propagation, both layers", r10: "—",
                note: "α = 0.25 mix of the two layers" },
  freq: { label: "most-changed files", r10: "—",
          note: "frequency baseline, ignores the seed entirely" },
};

const ORDER = ["rose", "temporal_ppr", "hybrid_a25", "static_ppr", "freq"];

export default function ImpactView({ indexId, file, onPick }: {
  indexId: string; file: string | null; onPick: (f: string) => void;
}) {
  const [data, setData] = useState<ImpactData | null>(null);
  const [method, setMethod] = useState("rose");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!file) return;
    setBusy(true);
    api.impact(indexId, file, 15)
      .then((d) => { setData(d); setErr(null); })
      .catch((e) => setErr(String(e)))
      .finally(() => setBusy(false));
  }, [indexId, file]);

  useEffect(() => {
    if (query.length < 2) { setHits([]); return; }
    let alive = true;
    api.search(indexId, query).then((r) => alive && setHits(r.files)).catch(() => {});
    return () => { alive = false; };
  }, [indexId, query]);

  const rows = data?.methods[method] ?? [];

  return (
    <div className="card">
      <div className="row">
        <span>If you edit</span>
        <input type="search" value={query} placeholder={file ?? "search a file…"}
               onChange={(e) => setQuery(e.target.value)} />
        <span className="hint">which files will you likely have to touch too?</span>
        <span className="spacer" />
        {data && (
          <span className="chip">
            propagation <b>{ms(Object.values(data.timings_ms)
              .reduce((a, b) => a + b, 0))}</b> on one CPU core
          </span>
        )}
      </div>

      {hits.length > 0 && (
        <div className="chips">
          {hits.slice(0, 12).map((h) => (
            <button className="chip mono" key={h}
                    onClick={() => { onPick(h); setQuery(""); setHits([]); }}>
              {h}
            </button>
          ))}
        </div>
      )}

      {file && (
        <div className="row" style={{ marginTop: 12 }}>
          <span className="mono"><b>{file}</b></span>
        </div>
      )}

      <div className="chips" style={{ marginTop: 12 }}>
        {ORDER.map((m) => (
          <button key={m} className={`chip${m === method ? " win" : ""}`}
                  onClick={() => setMethod(m)}>
            {PAPER_R10[m].label}
            {PAPER_R10[m].r10 !== "—" && <> · R@10 <b>{PAPER_R10[m].r10}</b></>}
          </button>
        ))}
      </div>
      {PAPER_R10[method].note && (
        <div className="hint" style={{ marginTop: 6 }}>{PAPER_R10[method].note}</div>
      )}

      {err && <div className="err">{err}</div>}
      {busy && <div className="hint" style={{ marginTop: 10 }}>propagating…</div>}

      <table className="rank" style={{ marginTop: 12 }}>
        <thead>
          <tr><th>#</th><th>file</th><th>score</th><th>evidence</th></tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.file}>
              <td className="num">{i + 1}</td>
              <td>
                <a href="#" onClick={(e) => { e.preventDefault(); onPick(r.file); }}>
                  <Path file={r.file} />
                </a>
              </td>
              <td className="num">{r.score.toFixed(3)}</td>
              <td><EvidenceChips chips={r.evidence} /></td>
            </tr>
          ))}
          {!rows.length && !busy && (
            <tr><td colSpan={4} className="hint">
              No co-change partners for this file in the mined history.
            </td></tr>
          )}
        </tbody>
      </table>

      <div className="chips">
        <span className="chip">lexical retrieval cannot answer this: the
          coupling is not textual</span>
        <span className="chip">history-only signal, no parser, transfers to any
          language</span>
      </div>
    </div>
  );
}
