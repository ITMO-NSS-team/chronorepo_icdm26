import { useEffect, useRef, useState } from "react";
import { api, streamIndex, type Config, type IndexEvent, type RepoStats } from "../api";
import type { Tab } from "../App";
import { ms } from "../components/bits";

type Line = { text: string; cls?: string };

function describe(e: IndexEvent): Line | null {
  const n = (k: string) => Number(e[k] ?? 0).toLocaleString();
  switch (e.stage) {
    case "queue":
      return { text: `waiting: ${e.message}`, cls: "warn" };
    case "clone":
      if (e.status === "start")
        return { text: `$ git clone --bare --no-tags --single-branch ${e.repo}` +
                       (e.size_mb ? `   (~${e.size_mb} MB)` : "") };
      if (e.status === "progress")
        return { text: `  ${e.phase}: ${e.percent}%` };
      return { text: `  ${e.action} done in ${ms(Number(e.ms))}, ${e.mb} MB on disk` };
    case "cache":
      return { text: `index restored from ${e.source}`, cls: "ok" };
    case "resolve":
      return { text: `revision ${String(e.rev).slice(0, 12)} · ` +
                     `${n("commits_in_ancestry")} commits in its ancestry ` +
                     `(exact rev-list cutoff, no future leakage)` };
    case "history":
      return { text: `git log --numstat: ${n("commits")} commits mined ` +
                     `(bulk commits >30 files dropped) in ${ms(Number(e.ms))}` };
    case "tree":
      return { text: `tree at revision: ${n("files")} text files, ` +
                     `${n("py_files")} python` };
    case "blobs":
      if (e.status === "progress") return null;
      return { text: `blob contents fetched and tokenized in ${ms(Number(e.ms))}` };
    case "bm25":
      return { text: `BM25 index: ${n("docs")} docs, ${n("terms")} terms` };
    case "imports":
      return { text: `static layer: ${n("edges")} import edges in ${ms(Number(e.ms))}` };
    case "temporal":
      return { text: `temporal layer: ${n("edges")} co-change pairs ` +
                     `(exponential decay, λ = 1/90 per day) in ${ms(Number(e.ms))}` };
    case "ready":
      return { text: `✓ ready in ${ms(Number(e.total_ms))}` +
                     (e.rss_mb ? ` · RSS ${e.rss_mb} MB` : "") +
                     ` — queries now answered in milliseconds`, cls: "ok" };
    case "traceback":
      return { text: String(e.text), cls: "warn" };
    default:
      return null;
  }
}

export default function IndexView({ config, onIndexed, repo, goto }: {
  config: Config | null;
  onIndexed: (indexId: string) => void;
  repo: RepoStats | null;
  goto: (t: Tab) => void;
}) {
  const [url, setUrl] = useState("pallets/flask");
  const [lines, setLines] = useState<Line[]>([]);
  const [pct, setPct] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [known, setKnown] = useState<{ repo: string; rev: string }[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.repos().then((r) => setKnown(r.snapshots)).catch(() => {});
  }, [repo]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [lines]);

  async function start(target?: string) {
    const wanted = (target ?? url).trim();
    if (!wanted || busy) return;
    setBusy(true); setErr(null); setLines([]); setPct(0);
    try {
      const { job_id } = await api.startIndex(wanted);
      streamIndex(job_id, (e) => {
        if (e.stage === "blobs" && e.status === "progress") {
          setPct(Math.round((Number(e.done) / Number(e.total)) * 100));
        } else if (e.stage === "clone" && e.status === "progress") {
          setPct(Number(e.percent));
        }
        const line = describe(e);
        if (line) setLines((prev) => [...prev, line]);
      }, (end) => {
        setBusy(false); setPct(100);
        if (end.state === "error" || !end.index_id) {
          setErr(end.error || "indexing failed");
        } else {
          onIndexed(end.index_id);
        }
      });
    } catch (e) {
      setBusy(false);
      setErr(String(e));
    }
  }

  return (
    <>
      <div className="card">
        <div className="row">
          <input type="text" value={url} spellCheck={false}
                 placeholder="https://github.com/owner/repo"
                 onChange={(e) => setUrl(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && start()} />
          <button className="primary" disabled={busy} onClick={() => start()}>
            {busy ? "Indexing…" : "Index repository"}
          </button>
          <span className="hint">
            first run clones the repository; re-indexing only touches changed
            blobs
          </span>
        </div>

        <div className="chips" style={{ marginTop: 12 }}>
          <span className="hint">or start with one of these — one click, ~1 s:</span>
          <span className="repo-suggestions">
            {(config?.bundled_repos ?? []).map((r) => (
              <button key={r} className="ghost" disabled={busy}
                      onClick={() => { setUrl(r); start(r); }}>{r}</button>
            ))}
          </span>
        </div>
        {known.length > 0 && (
          <div className="chips">
            <span className="hint">prebuilt snapshots:</span>
            {known.map((s) => (
              <button key={s.repo + s.rev} className="ghost" disabled={busy}
                      onClick={() => { setUrl(s.repo); start(s.repo); }}>
                {s.repo} @ {s.rev.slice(0, 7)}
              </button>
            ))}
          </div>
        )}

        {(busy || lines.length > 0) && (
          <>
            <div className="bar"><i style={{ width: `${pct}%` }} /></div>
            <div className="log" ref={logRef}>
              {lines.map((l, i) => (
                <div key={i} className={l.cls}>{l.text}</div>
              ))}
            </div>
          </>
        )}
        {err && <div className="err">{err}</div>}
      </div>

      {repo && (
        <div className="card">
          <div className="row">
            <h3 style={{ margin: 0 }}>{repo.repo}</h3>
            <span className="mono hint">@ {repo.rev.slice(0, 12)}</span>
            <span className="spacer" />
            <button className="ghost" onClick={() => goto("graph")}>
              02 Graph →
            </button>
            <button className="ghost" onClick={() => goto("issue")}>
              04 Localize an issue →
            </button>
          </div>
          <div className="chips">
            <span className="chip"><b>{Number(repo.stats.files).toLocaleString()}</b> text files</span>
            <span className="chip"><b>{Number(repo.stats.py_files).toLocaleString()}</b> python files</span>
            <span className="chip"><b>{Number(repo.stats.commits_mined).toLocaleString()}</b> commits mined</span>
            <span className="chip"><b>{Number(repo.stats.commits_in_ancestry).toLocaleString()}</b> in ancestry</span>
            <span className="chip"><b>{Number(repo.stats.import_edges).toLocaleString()}</b> import edges</span>
            <span className="chip"><b>{Number(repo.stats.cochange_pairs).toLocaleString()}</b> co-change pairs</span>
            <span className="chip">index <b>{ms(Number(repo.stats.total_ms))}</b></span>
            {repo.stats.rss_mb ? (
              <span className="chip">RSS <b>{Number(repo.stats.rss_mb)}</b> MB</span>
            ) : null}
          </div>
          <div className="chips">
            <span className="hint">stage breakdown:</span>
            {["history_ms", "tree_ms", "blobs_ms", "bm25_ms", "imports_ms",
              "temporal_ms", "rows_ms"].map((k) => (
              <span className="chip" key={k}>
                {k.replace("_ms", "")} <b>{ms(Number(repo.stats[k]))}</b>
              </span>
            ))}
          </div>
          <div className="chips">
            <span className="hint">most co-changed files:</span>
            {repo.top_files.slice(0, 8).map((f) => (
              <span className="chip mono" key={f.file}>
                {f.file.split("/").pop()} <b>{f.involvement}</b>
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
