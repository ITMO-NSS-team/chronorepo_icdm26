import { useEffect, useMemo, useState } from "react";
import { api, streamIndex, type Candidate, type Config, type Instance,
         type LocalizeResult, type RepoStats } from "../api";
import type { Tab } from "../App";
import { EvidenceChips, ms, usd } from "../components/bits";

function RankColumn({ title, note, files, gold, selected, onSelect }: {
  title: string; note: string; files: string[]; gold: string[];
  selected: string | null; onSelect: (f: string) => void;
}) {
  const goldSet = new Set(gold);
  return (
    <div className="col">
      <h3>{title} <span className="m">{note}</span></h3>
      <ol className="files">
        {files.slice(0, 10).map((f) => (
          <li key={f}
              className={`${goldSet.has(f) ? "gold " : ""}${selected === f ? "sel" : ""}`}
              onClick={() => onSelect(f)} title={f}>
            {f}
          </li>
        ))}
        {!files.length && <li className="hint">—</li>}
      </ol>
    </div>
  );
}

function Why({ cand }: { cand: Candidate }) {
  const max = Math.max(...cand.sources.map((s) => s.contrib), 1e-9);
  return (
    <div className="why">
      <h4>Why <span className="mono">{cand.file}</span> is rank {cand.rank}</h4>
      {cand.sources.map((s) => (
        <div className="contrib" key={s.list}>
          <span className="name">{s.label}</span>
          <span className="track"><i style={{ width: `${(s.contrib / max) * 100}%` }} /></span>
          <span className="val">#{s.rank} → +{s.contrib.toFixed(4)}</span>
        </div>
      ))}
      <div className="row tight" style={{ marginTop: 8 }}>
        <span className="chip">fused score <b>{cand.rrf.toFixed(4)}</b></span>
        <EvidenceChips chips={cand.evidence} />
      </div>
      {!cand.sources.length && (
        <div className="hint">This file entered the basket from a single list.</div>
      )}
    </div>
  );
}

export default function IssueView({ indexId, repo, config, onOpen, onIndexed }: {
  indexId: string; repo: RepoStats; config: Config | null;
  onOpen: (f: string, t: Tab) => void;
  onIndexed: (indexId: string) => void;
}) {
  const [instances, setInstances] = useState<Instance[]>([]);
  const [instanceId, setInstanceId] = useState<string>("");
  const [issue, setIssue] = useState("");
  const [gold, setGold] = useState<string[]>([]);
  const [depth, setDepth] = useState(50);
  const [useLlm, setUseLlm] = useState(true);
  const [model, setModel] = useState(config?.llm.default ?? "");
  const [res, setRes] = useState<LocalizeResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [baseCommit, setBaseCommit] = useState<string | null>(null);
  const [reindexing, setReindexing] = useState(false);

  const staleRevision =
    !!baseCommit && baseCommit.slice(0, 12) !== repo.rev.slice(0, 12);

  async function indexBaseCommit() {
    if (!baseCommit || reindexing) return;
    setReindexing(true);
    try {
      const { job_id } = await api.startIndex(repo.repo, baseCommit);
      streamIndex(job_id, () => {}, (end) => {
        setReindexing(false);
        if (end.index_id) { onIndexed(end.index_id); setRes(null); setErr(null); }
        else setErr(end.error || "indexing failed");
      });
    } catch (e) {
      setReindexing(false);
      setErr(String(e));
    }
  }

  useEffect(() => { if (config && !model) setModel(config.llm.default); },
            [config, model]);

  // Land on a real issue for this repository: the booth visitor should be one
  // click away from an answer, not staring at an empty textarea. A pasted or
  // already-chosen issue is never overwritten.
  useEffect(() => {
    let alive = true;
    api.instances(repo.repo).then((r) => {
      if (!alive) return;
      setInstances(r.instances);
      if (!issue.trim() && !instanceId && r.instances.length) {
        const pick = r.instances.find((i) => i.featured) ?? r.instances[0];
        loadInstance(pick.id).catch(() => {});
      }
    }).catch(() => {});
    return () => { alive = false; };
  }, [repo.repo]);

  async function loadInstance(iid: string) {
    setInstanceId(iid);
    setRes(null); setSel(null); setErr(null);
    if (!iid) { setIssue(""); setGold([]); setBaseCommit(null); return; }
    const inst = await api.instance(iid);
    setIssue(inst.issue);
    setGold(inst.gold);
    setBaseCommit(inst.base_commit);
  }

  async function run() {
    if (issue.trim().length < 12) { setErr("Paste an issue first"); return; }
    setBusy(true); setErr(null); setSel(null);
    try {
      const r = await api.localize(indexId, {
        issue, depth,
        llm: { enabled: useLlm && !!config?.llm.enabled, model },
      });
      r.gold = gold.length ? gold : r.gold;
      setRes(r);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  const candidate = useMemo(
    () => res?.candidates.find((c) => c.file === sel) ?? null, [res, sel]);

  const rankOf = (list: string[] | undefined, g: string[]) =>
    (list ?? []).map((f, i) => (g.includes(f) ? i + 1 : 0)).filter(Boolean);

  const t = res?.timings_ms ?? {};
  const cheapMs = ["bm25", "grep", "paths", "propagate", "fuse", "evidence"]
    .reduce((a, k) => a + (t[k] ?? 0), 0);

  return (
    <>
      <div className="card">
        <div className="row">
          <select value={instanceId} onChange={(e) => loadInstance(e.target.value)}>
            <option value="">— paste your own issue —</option>
            {instances.map((i) => (
              <option key={i.id} value={i.id}>
                {i.featured ? "★ " : ""}{i.id}: {i.title.slice(0, 70)}
              </option>
            ))}
          </select>
          <label className="check">
            depth
            <select value={depth} onChange={(e) => setDepth(Number(e.target.value))}>
              {[25, 50, 100].map((d) => <option key={d}>{d}</option>)}
            </select>
          </label>
          <label className="check">
            <input type="checkbox" checked={useLlm} disabled={!config?.llm.enabled}
                   onChange={(e) => setUseLlm(e.target.checked)} />
            one LLM call
          </label>
          <select value={model} disabled={!useLlm || !config?.llm.enabled}
                  onChange={(e) => setModel(e.target.value)}>
            {config?.llm.models.map((m) => (
              <option key={m.id} value={m.id}>{m.label} — {m.note}</option>
            ))}
          </select>
          <button className="primary" onClick={run} disabled={busy}>
            {busy ? "Localizing…" : "Localize"}
          </button>
        </div>

        <textarea value={issue} spellCheck={false} style={{ marginTop: 10 }}
                  placeholder="Paste a GitHub issue: title, description, traceback…"
                  onChange={(e) => { setIssue(e.target.value); setGold([]); setInstanceId(""); }} />

        {staleRevision && (
          <div className="row tight" style={{ marginTop: 10 }}>
            <span className="chip warn">
              index is at <b className="mono">{repo.rev.slice(0, 7)}</b>, this
              issue was filed against <b className="mono">{baseCommit!.slice(0, 7)}</b>
            </span>
            <button className="ghost" onClick={indexBaseCommit} disabled={reindexing}>
              {reindexing ? "indexing that revision…"
                          : "index the pre-fix revision (leakage-free)"}
            </button>
            <span className="hint">
              the graph is then built only from commits in that commit's ancestry —
              exactly the protocol the paper's numbers use
            </span>
          </div>
        )}

        <div className="stage-strip">
          <span className="srcbox">BM25</span><span>+</span>
          <span className="srcbox">propagation (BM25 seed)</span><span>+</span>
          <span className="srcbox">propagation (identifier seed)</span><span>+</span>
          <span className="srcbox">recency</span><span>+</span>
          <span className="srcbox">path tokens</span><span>+</span>
          <span className="srcbox">paths quoted in the issue</span>
          <span>→ rank fusion (RRF, k={config?.rrf_k ?? 40}) → {config?.candidate_depth ?? 100} candidates
            → top {depth} to one call</span>
        </div>
        {err && <div className="err">{err}</div>}
      </div>

      {res && (
        <div className="card">
          <div className="cols">
            <RankColumn title="1 · BM25" note="lexical only"
                        files={res.bm25} gold={res.gold} selected={sel}
                        onSelect={setSel} />
            <RankColumn title="2 · ChronoRepo candidates" note="no LLM, ~$0"
                        files={res.candidate_paths} gold={res.gold}
                        selected={sel} onSelect={setSel} />
            <RankColumn title={`3 · + one ${res.llm ? res.llm.model.split("/").pop() : "LLM"} call`}
                        note={res.llm ? usd(res.llm.usd) : "not run"}
                        files={res.final ?? []} gold={res.gold}
                        selected={sel} onSelect={setSel} />
          </div>

          <div className="chips">
            <span className="chip">candidates <b>{ms(cheapMs)}</b></span>
            {Object.entries(t).filter(([k]) => k !== "llm").map(([k, v]) => (
              <span className="chip" key={k}>{k} <b>{ms(v)}</b></span>
            ))}
            {res.llm && (
              <>
                <span className="chip">LLM <b>{ms(res.llm.ms)}</b></span>
                <span className="chip">
                  tokens <b>{res.llm.prompt_tokens}</b> in / <b>{res.llm.completion_tokens}</b> out
                </span>
                <span className="chip win">cost <b>{usd(res.llm.usd)}</b> per issue</span>
              </>
            )}
            {res.llm_error && <span className="chip warn">LLM: {res.llm_error}</span>}
          </div>

          {res.gold.length > 0 && (
            <div className="chips">
              <span className="chip">✓ gold = files touched by the real fix</span>
              <span className="chip">
                gold rank — BM25 <b>{rankOf(res.bm25, res.gold).join(", ") || "—"}</b>
                {" · "}candidates <b>{rankOf(res.candidate_paths, res.gold).join(", ") || "—"}</b>
                {res.final && <> · after the call <b>{rankOf(res.final, res.gold).join(", ") || "—"}</b></>}
              </span>
              <span className="chip">reference: fine-tuned 7B agent 78.6% ·
                Claude-3.5 agent 83.4% (≈$0.66/issue)</span>
            </div>
          )}

          {candidate ? <Why cand={candidate} /> : (
            <div className="hint" style={{ marginTop: 10 }}>
              Click any file to see which of the six fused lists put it there.
            </div>
          )}
          {sel && (
            <div className="row tight" style={{ marginTop: 8 }}>
              <button className="ghost" onClick={() => onOpen(sel, "impact")}>
                impact set of {sel.split("/").pop()} →
              </button>
              <button className="ghost" onClick={() => onOpen(sel, "graph")}>
                show in graph →
              </button>
            </div>
          )}
        </div>
      )}
    </>
  );
}
