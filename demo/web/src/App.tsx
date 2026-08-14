import { useCallback, useEffect, useState } from "react";
import { api, type Config, type RepoStats } from "./api";
import IndexView from "./views/IndexView";
import GraphView from "./views/GraphView";
import ImpactView from "./views/ImpactView";
import IssueView from "./views/IssueView";
import BenchView from "./views/BenchView";
import { ms } from "./components/bits";

export type Tab = "index" | "graph" | "impact" | "issue" | "bench";

const TABS: { id: Tab; label: string; needsIndex: boolean }[] = [
  { id: "index", label: "Repository", needsIndex: false },
  { id: "graph", label: "Graph & timeline", needsIndex: true },
  { id: "impact", label: "Impact set", needsIndex: true },
  { id: "issue", label: "Issue → files", needsIndex: true },
  { id: "bench", label: "Benchmarks", needsIndex: false },
];

const TOUR: { tab: Tab; text: string }[] = [
  { tab: "index", text: "Paste a GitHub URL. The graph is built from a bare clone: one git log pass for co-change, one tree pass for imports." },
  { tab: "graph", text: "Drag the time slider: co-change edges grow and fade with exponential decay. Watch pairs that no import connects light up." },
  { tab: "impact", text: "Pick a file and read its impact set with the evidence behind every row — this is what a lexical search cannot answer." },
  { tab: "issue", text: "Paste an issue (or load a benchmark one): BM25 vs candidates vs one small-model call, with real latency and cost." },
];

export default function App() {
  const [config, setConfig] = useState<Config | null>(null);
  const [tab, setTab] = useState<Tab>("index");
  const [indexId, setIndexId] = useState<string | null>(null);
  const [repo, setRepo] = useState<RepoStats | null>(null);
  const [file, setFile] = useState<string | null>(null);
  const [tour, setTour] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.config().then(setConfig).catch((e) => setError(String(e)));
  }, []);

  const loadRepo = useCallback(async (id: string) => {
    setIndexId(id);
    try {
      const r = await api.repo(id);
      setRepo(r);
      setFile((f) => f ?? r.top_files[0]?.file ?? null);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  const openFile = useCallback((f: string, go: Tab = "impact") => {
    setFile(f);
    setTab(go);
  }, []);

  const tourStep = tour === null ? null : TOUR[tour];

  return (
    <div className="shell">
      <header className="app">
        <h1>ChronoRepo</h1>
        <span className="tag">ICDM 2026 demo</span>
        <span className="tag">CPU-only graph · no fine-tuning · no agent loop</span>
        {config && <span className="tag">mode: {config.mode}</span>}
        <span className="spacer" />
        <button className="ghost" onClick={() => setTour(tour === null ? 0 : null)}>
          {tour === null ? "Guided tour" : "Exit tour"}
        </button>
      </header>

      <p className="sub">
        A temporal knowledge graph of a repository: import structure parsed from
        code plus co-change relations mined from git history with exponential
        decay. Candidates fuse graph propagation with lexical, path and recency
        evidence; one optional call to an off-the-shelf small model reranks
        them. <b>80.5%</b> strict Acc@5 on LocBench with a vanilla 9B call,
        against <b>78.6%</b> for a fine-tuned multi-turn 7B agent.
      </p>

      {tourStep && (
        <div className="tour">
          <span className="step">Step {tour! + 1} / {TOUR.length}</span>
          <span>{tourStep.text}</span>
          <span className="spacer" />
          <button className="ghost" disabled={tour === 0}
                  onClick={() => { const n = tour! - 1; setTour(n); setTab(TOUR[n].tab); }}>
            Back
          </button>
          <button className="primary"
                  disabled={tour === TOUR.length - 1}
                  onClick={() => { const n = tour! + 1; setTour(n); setTab(TOUR[n].tab); }}>
            Next
          </button>
        </div>
      )}

      {error && <div className="err">{error}</div>}

      <nav className="tabs">
        {TABS.map((t) => (
          <button key={t.id} className={t.id === tab ? "on" : ""}
                  disabled={t.needsIndex && !indexId}
                  onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
        <span className="spacer" />
        {repo && (
          <span className="chip" style={{ alignSelf: "center" }}>
            <b>{repo.repo}</b> @ {repo.rev.slice(0, 7)} ·{" "}
            {Number(repo.stats.py_files)} py files ·{" "}
            {Number(repo.stats.commits_in_ancestry).toLocaleString()} commits ·
            index {ms(Number(repo.stats.total_ms))}
          </span>
        )}
      </nav>

      {tab === "index" && (
        <IndexView config={config} onIndexed={loadRepo} repo={repo}
                   goto={setTab} />
      )}
      {tab === "graph" && indexId && repo && (
        <GraphView indexId={indexId} repo={repo} file={file}
                   onPick={(f) => setFile(f)} onOpen={openFile} />
      )}
      {tab === "impact" && indexId && (
        <ImpactView indexId={indexId} file={file} onPick={setFile} />
      )}
      {tab === "issue" && indexId && repo && (
        <IssueView indexId={indexId} repo={repo} config={config}
                   onOpen={openFile} onIndexed={loadRepo} />
      )}
      {tab === "bench" && <BenchView />}

      <footer className="note">
        Every ranking, timing and cost on this page is computed live by the
        engine in <span className="mono">experiments/chrono.py</span> — the same
        code that produced the paper's tables. Parity with the reported runs is
        asserted in <span className="mono">demo/tests/test_parity.py</span>.
      </footer>
    </div>
  );
}
