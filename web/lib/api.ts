// Typed client for the console. Every call goes through the server-side proxy
// at /api/backend/*, which attaches the API token before forwarding upstream,
// so the browser never handles credentials.

export type Tier = "main" | "cheap" | "balanced" | "powerful";

export interface Health {
  status: string;
}

export interface ModelTier {
  tier: Tier;
  env_var: string;
  model: string;
  configured: boolean;
  fallback: boolean;
}

export interface MetricsSnapshot {
  http_requests_total: Record<string, number>;
  http_latency_ms_avg: Record<string, number>;
  llm_calls_total: Record<string, number>;
  llm_latency_ms_avg: Record<string, number>;
  llm_input_tokens_total: number;
  llm_output_tokens_total: number;
  llm_total_tokens_total: number;
  llm_estimated_cost_usd_total: number;
}

export interface RequestRecord {
  request_id: string;
  trace_id: string;
  method: string;
  path: string;
  status: number;
  latency_ms: number;
  success: boolean;
  timestamp: number;
}

export interface LlmCallRecord {
  request_id: string;
  trace_id: string;
  model: string;
  tier: string;
  status: string;
  latency_ms: number;
  attempt: number;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  cost_usd: number | null;
  timestamp: number;
}

export interface Observability {
  requests: RequestRecord[];
  llm_calls: LlmCallRecord[];
}

export interface LatencyStats {
  average: number | null;
  p50?: number | null;
  p95?: number | null;
  p99?: number | null;
}

export interface TierComparison {
  tier: Tier;
  model: string;
  cases: number;
  passed: number;
  pass_rate: number | null;
  errors: number;
  latency_ms: LatencyStats;
  tokens: { average: number | null; input: number; output: number };
  cost: { average_per_request_usd: number | null; total_usd: number };
}

export interface CompareResult {
  timestamp: string;
  cases_per_tier: number;
  results: TierComparison[];
}

export interface SuiteIndex {
  suites: { name: string; cases: number; file: string }[];
}

export interface SuiteReport {
  suite: string;
  total_cases: number;
  evaluated_cases: number;
  passed: number;
  model_failures: number;
  api_errors: number;
  accuracy: number | null;
  api_error_rate: number;
  structured_output_validity: number | null;
  retrieval?: {
    precision_at_k: number;
    recall_at_k: number;
    hit_rate_at_k: number;
    mrr: number;
    k: number;
  };
  latency_ms: LatencyStats;
  tokens: { input: number; output: number; total: number };
  cost: { total_usd: number; average_per_request_usd: number };
}

export interface EvalReport {
  timestamp: string;
  suites: SuiteReport[];
  totals: {
    total_cases: number;
    evaluated_cases: number;
    passed: number;
    accuracy: number | null;
    api_errors: number;
    tokens: { input: number; output: number; total: number };
    cost: { total_usd: number };
  };
}

export interface Source {
  source_id: string;
  chunk_id: string;
  source: string;
  page: number | null;
  section: string | null;
  score: number;
}

export interface Candidate {
  chunk_id: string;
  source: string;
  page: number | null;
  section: string | null;
  text: string;
  recall_score: number;
  recall_type: string;
  rerank_score: number | null;
  kept: boolean;
}

export interface CitationReport {
  valid_citations: string[];
  hallucinated_citations: string[];
  coverage: number;
  source_map: Record<string, string>;
}

export interface RagAnswer {
  query: string;
  answer: string;
  context: string;
  sources: Source[];
  retrieved_ids: string[];
  candidates: Candidate[];
  citations?: CitationReport;
  model?: string;
  route?: string;
  latency_ms?: number;
  estimated_cost_usd?: number;
}

export interface ScreeningReport {
  candidate: {
    name: string;
    years_experience: number;
    skills: string[];
    education: string;
    highlights: string[];
  };
  requirements: {
    role: string;
    required_skills: string[];
    min_years: number;
    nice_to_have: string[];
    responsibilities: string[];
  };
  match_score: number;
  recommendation: "advance" | "hold" | "reject";
  matched_skills: string[];
  missing_skills: string[];
  evidence: { criterion: string; matched: boolean; detail: string }[];
  model: string;
  route: string;
  latency_ms: number;
}

export interface SecurityPolicy {
  auth: { scheme: string; enabled: boolean; header: string };
  rate_limit: {
    limit: number;
    window_seconds: number;
    key: string;
    headers: string[];
  };
  protected_routes: string[];
  public_routes: string[];
}

const BASE = "/api/backend";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (res.status === 503) {
    throw new Error("Backend is unavailable — the server is missing its API token.");
  }
  if (!res.ok) {
    let detail = `Request failed: ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = `${detail} — ${body.detail}`;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

const get = <T,>(path: string) => request<T>(path);
const post = <T,>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) });

export const api = {
  health: () => get<Health>("/health"),
  metrics: () => get<MetricsSnapshot>("/metrics"),
  models: () => get<{ tiers: ModelTier[] }>("/models"),
  observability: (limit = 30) =>
    get<Observability>(`/observability/requests?limit=${limit}`),
  compare: (limit = 5) => get<CompareResult>(`/compare?limit=${limit}`),
  evalSuites: () => get<SuiteIndex>("/evals/suites"),
  runEvals: (suites: string[], limit = 5) =>
    post<EvalReport>("/evals/run", { suites, limit }),
  ragRetrieve: (query: string, recall_k = 6, final_k = 3) =>
    post<RagAnswer>("/rag/retrieve", { query, recall_k, final_k }),
  ask: (query: string, recall_k = 6, final_k = 3) =>
    post<RagAnswer>("/ask", { query, recall_k, final_k }),
  securityPolicy: () => get<SecurityPolicy>("/security/policy"),
  screen: (job_description: string, resume: string) =>
    post<ScreeningReport>("/recruitment/screen", { job_description, resume }),
};

// Streaming chat. Reads the upstream body incrementally so tokens render as
// they arrive; the proxy passes the stream through untouched.
export async function streamChat(
  prompt: string,
  tier: Tier,
  onChunk: (text: string) => void,
): Promise<void> {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, tier }),
    cache: "no-store",
  });
  if (res.status === 503) {
    throw new Error("Chat is unavailable — the server is missing its API token.");
  }
  if (!res.ok || !res.body) throw new Error(`Request failed: ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let text = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    text += decoder.decode(value, { stream: true });
    onChunk(text);
  }
}
