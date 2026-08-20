import { useCallback, useEffect, useState } from "react";
import { api, type Config, type RepoStats } from "./api";
import IndexView from "./views/IndexView";
import GraphView from "./views/GraphView";
import ImpactView from "./views/ImpactView";
import IssueView from "./views/IssueView";
import BenchView from "./views/BenchView";
import { ms } from "./components/bits";

export type Tab = "index" | "graph" | "impact" | "issue" | "bench";

type Step = {
  id: Tab;
  n: string;
  label: string;
  needsIndex: boolean;
  title: string;
  brief: string;
  /** why the visitor should press "next" from here */
  lead: string;
};

/** The demo is one scenario read top to bottom: take a repository, build its
 *  temporal graph, ask the two questions the graph answers, check the numbers.
 *  The rail, the brief and the footer all address the same order. */
const STEPS: Step[] = [
  {
    id: "index", n: "01", label: "Index", needsIndex: false,
    title: "Index a repository",
    brief: "Paste any GitHub URL. One bare clone, one git log pass for " +
           "co-change, one tree pass for imports — the log below is the " +
           "pipeline reporting its own stages, not a canned animation.",
    lead: "See the graph that was just built",
  },
  {
    id: "graph", n: "02", label: "Graph", needsIndex: true,
    title: "Watch the graph age",
    brief: "Two layers over the same files: imports parsed from the tree, " +
           "co-change mined from history and weighted by exponential decay. " +
           "Drag the slider — old couplings fade, and pairs no import " +
           "connects light up.",
    lead: "Ask what changes together with one file",
  },
  {
    id: "impact", n: "03", label: "Impact set", needsIndex: true,
    title: "Ask for an impact set",
    brief: "Pick a file: which files will you likely have to touch with it? " +
           "Every row carries the evidence behind it. This is the question " +
           "lexical search cannot answer — the coupling is not textual.",
    lead: "Point the same graph at a real issue",
  },
  {
    id: "issue", n: "04", label: "Localize an issue", needsIndex: true,
    title: "Localize an issue",
    brief: "The main event: paste an issue, or load a benchmark one. BM25, " +
           "then our candidates, then one call to an off-the-shelf small " +
           "model — side by side, with real latency and real cost.",
    lead: "Check these numbers against the paper",
  },
  {
    id: "bench", n: "05", label: "Results", needsIndex: false,
    title: "Where this lands",
    brief: "The tables from the paper, produced by the same engine that " +
           "just answered your issue: LocBench, SWE-bench Lite, the " +
           "ablations, and the cost/accuracy frontier.",
    lead: "Index another repository",
  },
];

const idx = (t: Tab) => STEPS.findIndex((s) => s.id === t);

export default function App() {
  const [config, setConfig] = useState<Config | null>(null);
  const [tab, setTab] = useState<Tab>("index");
  const [indexId, setIndexId] = useState<string | null>(null);
  const [repo, setRepo] = useState<RepoStats | null>(null);
  const [file, setFile] = useState<string | null>(null);
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

  const go = useCallback((t: Tab) => {
    setTab(t);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const openFile = useCallback((f: string, target: Tab = "impact") => {
    setFile(f);
    go(target);
  }, [go]);

  const here = idx(tab);
  const step = STEPS[here];
  const prev = here > 0 ? STEPS[here - 1] : null;
  const next = STEPS[(here + 1) % STEPS.length];   // wraps back to step 01
  const nextBlocked = next.needsIndex && !indexId;

  return (
    <div className="shell">
      <header className="app">
        <h1>Chrono<em>Repo</em></h1>
        <span className="tag mark">ICDM 2026 demo</span>
        {config && <span className="tag">mode {config.mode}</span>}
      </header>

      <p className="sub">
        A temporal knowledge graph of a repository: import structure parsed from
        code plus co-change relations mined from git history with exponential
        decay. Candidates fuse graph propagation with lexical, path and recency
        evidence; one optional call to an off-the-shelf small model reranks
        them. <b>80.5%</b> strict Acc@5 on LocBench with a vanilla 9B call,
        against <b>78.6%</b> for a fine-tuned multi-turn 7B agent.
      </p>

      <div className="lede">
        <span>the demo in one line:</span>
        <b>index a repo</b><span className="arrow">→</span>
        <b>graph ages</b><span className="arrow">→</span>
        <b>impact set</b><span className="arrow">→</span>
        <b>issue → files</b><span className="arrow">→</span>
        <b>the paper's numbers</b>
        <span className="spacer" />
        <span>~3 minutes, five steps</span>
      </div>

      {error && <div className="err">{error}</div>}

      <nav className="steps">
        {STEPS.map((s, i) => (
          <button key={s.id}
                  className={`${s.id === tab ? "on " : ""}${i < here ? "done" : ""}`}
                  disabled={s.needsIndex && !indexId}
                  onClick={() => go(s.id)}>
            <span className="n">{s.n}</span>{s.label}
          </button>
        ))}
      </nav>

      {repo && (
        <div className="indexline">
          <span className="chip">
            working on <b>{repo.repo}</b> @ {repo.rev.slice(0, 7)} ·{" "}
            {Number(repo.stats.py_files)} py files ·{" "}
            {Number(repo.stats.commits_in_ancestry).toLocaleString()} commits ·
            indexed in {ms(Number(repo.stats.total_ms))}
          </span>
        </div>
      )}

      <div className="brief">
        <h2><span className="n">Step {step.n} of 05</span>{step.title}</h2>
        <p>{step.brief}</p>
      </div>

      {tab === "index" && (
        <IndexView config={config} onIndexed={loadRepo} repo={repo} goto={go} />
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

      <div className="stepbar">
        {prev && (
          <button className="ghost back" onClick={() => go(prev.id)}>
            {prev.n} {prev.label}
          </button>
        )}
        <span className="why">{step.lead}</span>
        <span className="spacer" />
        {nextBlocked && (
          <span className="blocked">index a repository first</span>
        )}
        <button className="primary" disabled={nextBlocked}
                onClick={() => go(next.id)}>
          Next · {next.n} {next.label}
        </button>
      </div>

      <footer className="note">
        Every ranking, timing and cost on this page is computed live by the
        engine in <span className="mono">experiments/chrono.py</span> — the same
        code that produced the paper's tables. Parity with the reported runs is
        asserted in <span className="mono">demo/tests/test_parity.py</span>.
      </footer>
    </div>
  );
}
