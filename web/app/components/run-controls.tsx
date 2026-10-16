"use client";

import { useCallback, useRef, useState } from "react";
import { ApiError, type ResultsTab } from "../../lib/api";
import { Bar } from "./ui";

// Re-export so panels can rely on the shared meter without extra imports.
export { Bar };

// Cheap saved-result simulator for the Compare/Evals/Retrieval/Recruitment
// tabs. A "fake run" costs nothing: it plays a progress animation with a live
// action trace, then loads one of the persisted result files (rotating slot
// 1 → 2 → 3 on every press) instead of calling an LLM. The secondary "real
// run" button still hits the live backend, so the console can measure real
// behavior without exhausting the provider between demos — see
// `RequestRunControls`.
export interface FakeRunStep {
  label: string;
  status: "pending" | "active" | "done";
}

export interface FakeRunState {
  active: boolean;
  progress: number; // 0..1
  label: string;
  slot: number | null;
  source: string; // "saved" | "live"
  steps: FakeRunStep[];
}

// Per-tab pipeline the fake run pretends to execute. Each entry becomes a row
// in the trace log; rows flip pending → active → done as the bar advances.
const TRACES: Record<ResultsTab, string[]> = {
  compare: [
    "Loading labeled chat cases…",
    "Calling tier model — cheap",
    "Calling tier model — balanced",
    "Calling tier model — powerful",
    "Scoring answers against the rubric…",
    "Aggregating pass rate, latency & cost",
  ],
  evals: [
    "Loading labeled suites…",
    "Evaluating suite — chat",
    "Evaluating suite — extraction",
    "Evaluating suite — classification",
    "Evaluating suite — adversarial",
    "Checking structured-output validity",
    "Aggregating suite scores",
  ],
  retrieval: [
    "Loading labeled retrieval questions…",
    "Hybrid recall: BM25 + embeddings",
    "Cross-encoder rerank…",
    "Scoring precision@k / recall@k / MRR",
  ],
  recruitment: [
    "Parsing job description…",
    "Extracting candidate profile…",
    "Scoring against the rubric…",
    "Preparing screening report",
  ],
};

const TRACE_TICKS = 40; // ×50ms ≈ 2s — long enough to read the action trace.
const TRACE_TICK_MS = 50;

function traceStatus(idx: number, progress: number, n: number): FakeRunStep["status"] {
  const start = idx / n;
  const end = (idx + 1) / n;
  if (progress >= end) return "done";
  if (progress >= start) return "active";
  return "pending";
}

function useFakeRun(tab: ResultsTab) {
  const [state, setState] = useState<FakeRunState>({
    active: false,
    progress: 0,
    label: "",
    slot: null,
    source: "saved",
    steps: [],
  });
  const slotRef = useRef(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = useCallback(() => {
    if (timer.current) {
      clearInterval(timer.current);
      timer.current = null;
    }
  }, []);

  const play = useCallback(
    (onSlot: (slot: number) => void, onComplete?: () => void) => {
      stop();
      slotRef.current = slotRef.current >= 3 ? 1 : slotRef.current + 1;
      const trace = TRACES[tab] ?? ["Simulating run…"];
      const pending = trace.map((label) => ({ label, status: "pending" as const }));
      setState({
        active: true,
        progress: 0,
        label: trace[0] ?? "Simulating run…",
        slot: null,
        source: "saved",
        steps: [{ ...pending[0], status: "active" }, ...pending.slice(1)],
      });
      let i = 0;
      timer.current = setInterval(() => {
        i += 1;
        const progress = i / TRACE_TICKS;
        setState((prev) => {
          const steps: FakeRunStep[] = trace.map((label, idx) => ({
            label,
            status: traceStatus(idx, progress, trace.length),
          }));
          const active = steps.find((s) => s.status === "active");
          return {
            ...prev,
            progress,
            steps,
            label: active?.label ?? "Finalizing…",
          };
        });
        if (i >= TRACE_TICKS) {
          stop();
          onSlot(slotRef.current);
          setState((prev) => ({
            ...prev,
            active: false,
            progress: 1,
            slot: slotRef.current,
            label: `Loaded saved result (example ${slotRef.current})`,
            steps: trace.map((label, idx) => ({
              label,
              status: traceStatus(idx, 1, trace.length),
            })),
          }));
          onComplete?.();
        }
      }, TRACE_TICK_MS);
    },
    [stop, tab],
  );

  return { state, play, stop };
}

export interface RequestRunControlsProps {
  tab: ResultsTab;
  onFakeRun: (slot: number) => void;
  onRealRun: () => Promise<void>;
  realBusy: boolean;
  realDisabled?: boolean;
  realLabel?: string;
  fakeLabel?: string;
  blurb?: string;
}

// Two-button run bar: a primary "Fake run" (progress bar + saved-result
// rotation, zero provider cost) and a secondary "Real run" (live backend,
// guarded against provider exhaustion).
export function RequestRunControls({
  tab,
  onFakeRun,
  onRealRun,
  realBusy,
  realDisabled,
  realLabel = "Real run",
  fakeLabel = "Fake run",
}: RequestRunControlsProps) {
  const fake = useFakeRun(tab);
  const [realError, setRealError] = useState("");

  const handleReal = async () => {
    setRealError("");
    try {
      await onRealRun();
    } catch (e) {
      setRealError(friendlyApiError(e));
    }
  };

  return (
    <div className="stack" style={{ gap: 10 }}>
      <div className="toolbar" style={{ flexWrap: "wrap" }}>
        <button
          className="primary"
          onClick={() => fake.play(onFakeRun)}
          disabled={fake.state.active}
        >
          {fake.state.active ? "Simulating…" : fakeLabel}
        </button>
        <button
          onClick={handleReal}
          disabled={realBusy || realDisabled}
          title={
            realDisabled
              ? "Backend unavailable"
              : "Runs against the live provider — may consume tokens."
          }
        >
          {realBusy ? "Running…" : realLabel}
        </button>
      </div>
      {fake.state.active && (
        <div className="run-progress">
          <Bar value={fake.state.progress} tone="blue" />
          <span className="muted">{fake.state.label}</span>
          {fake.state.steps.length > 0 && (
            <ol className="trace">
              {fake.state.steps.map((step, i) => (
                <li key={i} className={`trace-${step.status}`}>
                  <span className="trace-dot">
                    {step.status === "done" ? "✓" : step.status === "active" ? "›" : "·"}
                  </span>
                  <span>{step.label}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
      {realError && <p className="notice">{realError}</p>}
    </div>
  );
}

// Maps transport/HTTP errors onto a human explanation that names the status,
// so a user knows when the real run failed because the server/provider was
// exhausted rather than because of their inputs.
export function friendlyApiError(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 429)
      return "Rate limited — the server or provider is busy. Wait a moment, or re-run the fake run to view the saved results.";
    if (e.status === 502)
      return "LLM provider error — the model backend is unavailable. Showing saved results instead; try the real run later.";
    if (e.status === 503)
      return "Backend is overloaded or missing its API token. The saved results below are still viewable.";
    if (e.status === 504)
      return "LLM provider timed out — the run was too heavy or the provider is slow. Use the fake run to avoid exhausting it.";
    return e.message;
  }
  return e instanceof Error ? e.message : String(e);
}