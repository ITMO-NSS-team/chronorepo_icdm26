/** Typed client for the demo API. Every number here is computed by the
 *  Python engine (experiments/chrono.py); nothing is faked in the browser. */

export type Config = {
  mode: string;
  llm: { enabled: boolean; default: string;
         models: { id: string; label: string; note: string }[] };
  bundled_repos: string[];
  lambda_per_day: number;
  alpha: number;
  rrf_k: number;
  candidate_depth: number;
};

export type IndexEvent = {
  stage: string; status: string; t: number; [k: string]: unknown;
};

export type RepoStats = {
  index_id: string; repo: string; rev: string; base_ts: number;
  span: [number, number];
  stats: Record<string, number | string | Record<string, unknown>>;
  top_files: { file: string; involvement: number; changes: number }[];
};

export type GraphNode = {
  file: string; dir: string; w: number; changes: number; imports: number;
};
export type TemporalEdge = {
  a: string; b: string; count: number; decayed: number; last: number;
  ts: number[];
};
export type GraphData = {
  nodes: GraphNode[];
  static: { a: string; b: string }[];
  temporal: TemporalEdge[];
  focus: string | null;
  lambda_per_day: number;
  base_ts: number;
  span: [number, number];
  ms: number;
};

export type Chip =
  | { kind: "cochange"; with: string; count: number; last: string | null;
      decayed?: number }
  | { kind: "import"; with: string }
  | { kind: "graph"; score: number }
  | { kind: "bridge"; via: string; count: number };

export type ImpactRow = { file: string; score: number; evidence: Chip[] };
export type ImpactData = {
  seed: string;
  methods: Record<string, ImpactRow[]>;
  timings_ms: Record<string, number>;
};

export type Candidate = {
  file: string; rank: number; rrf: number;
  sources: { list: string; label: string; rank: number; contrib: number }[];
  evidence: Chip[];
  evidence_text: string;
};

export type LocalizeResult = {
  bm25: string[];
  candidates: Candidate[];
  candidate_paths: string[];
  final?: string[];
  timings_ms: Record<string, number>;
  n_candidates: number;
  seed_files: string[];
  gold: string[];
  depth: number;
  instance_id?: string | null;
  llm?: {
    model: string; ms: number; prompt_tokens: number;
    completion_tokens: number; usd: number | null; n_candidates: number;
    raw: string;
  };
  llm_error?: string;
};

export type Instance = {
  id: string; repo: string; base_commit: string; title: string;
  gold: string[]; featured: boolean; n_recorded_candidates: number;
};

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json() as Promise<T>;
}

async function post<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json() as Promise<T>;
}

export const api = {
  config: () => get<Config>("/api/config"),
  repos: () => get<{ loaded: { index_id: string; repo: string }[];
                     snapshots: { repo: string; rev: string }[];
                     suggested: string[] }>("/api/repos"),
  startIndex: (repo: string, rev?: string) =>
    post<{ job_id: string; repo: string }>("/api/index", { repo, rev }),
  repo: (id: string) => get<RepoStats>(`/api/repos/${id}`),
  graph: (id: string, p: { focus?: string; limit?: number; min_count?: number }) => {
    const q = new URLSearchParams();
    if (p.focus) q.set("focus", p.focus);
    if (p.limit) q.set("limit", String(p.limit));
    if (p.min_count) q.set("min_count", String(p.min_count));
    return get<GraphData>(`/api/repos/${id}/graph?${q}`);
  },
  search: (id: string, q: string) =>
    get<{ files: string[] }>(`/api/repos/${id}/search?q=${encodeURIComponent(q)}`),
  impact: (id: string, file: string, k = 15) =>
    get<ImpactData>(`/api/repos/${id}/impact?file=${encodeURIComponent(file)}&k=${k}`),
  localize: (id: string, body: {
    issue?: string; instance_id?: string; depth?: number;
    llm?: { enabled: boolean; model?: string };
  }) => post<LocalizeResult>(`/api/repos/${id}/localize`, body),
  instances: (repo?: string) =>
    get<{ instances: Instance[] }>(
      `/api/instances${repo ? `?repo=${encodeURIComponent(repo)}` : ""}`),
  instance: (iid: string) =>
    get<{ id: string; repo: string; base_commit: string; issue: string;
          gold: string[]; recorded: null | {
            candidates: string[]; final: string[];
            gold_rank_candidates: number[]; gold_rank_final: number[];
            model: string } }>(`/api/instances/${iid}`),
  benchmarks: () => get<Record<string, any>>("/api/benchmarks"),
};

/** Server-sent indexing progress. Returns an unsubscribe function. */
export function streamIndex(
  jobId: string,
  onEvent: (e: IndexEvent) => void,
  onEnd: (r: { state: string; index_id: string | null; error: string | null }) => void,
) {
  const es = new EventSource(`/api/index/${jobId}/events`);
  const stages = ["clone", "resolve", "history", "tree", "blobs", "bm25",
                  "imports", "temporal", "cache", "queue", "ready",
                  "finished", "traceback"];
  for (const s of stages) {
    es.addEventListener(s, (ev) => onEvent(JSON.parse((ev as MessageEvent).data)));
  }
  es.addEventListener("end", (ev) => {
    onEnd(JSON.parse((ev as MessageEvent).data));
    es.close();
  });
  es.onerror = () => { /* keep the connection retrying; end closes it */ };
  return () => es.close();
}
