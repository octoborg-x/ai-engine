"use client";

import { useCallback, useRef, useState } from "react";
import { ApiError, type ResultsTab } from "../../lib/api";
import { Bar } from "./ui";

// Re-export so panels can rely on the shared meter without extra imports.
export { Bar };

// Cheap saved-result simulator for the Compare/Evals tabs. A "fake run" costs
// nothing: it plays a progress animation, then loads one of the persisted
// result files (rotating slot 1 → 2 → 3 on every press) instead of calling an
// LLM. The secondary "real run" button still hits the live backend, so the
// console can measure real behavior without exhausting the provider between
// demos — see `RequestRunControls`.
export interface FakeRunState {
  active: boolean;
  progress: number; // 0..1
  label: string;
  slot: number | null;
  source: string; // "saved" | "live"
}

function useFakeRun(tab: ResultsTab) {
  const [state, setState] = useState<FakeRunState>({
    active: false,
    progress: 0,
    label: "",
    slot: null,
    source: "saved",
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
      setState({
        active: true,
        progress: 0,
        label: "Simulating run…",
        slot: null,
        source: "saved",
      });
      const steps = 40;
      let i = 0;
      timer.current = setInterval(() => {
        i += 1;
        const progress = i / steps;
        setState((prev) => ({
          ...prev,
          progress,
          label:
            progress < 0.25
              ? "Loading labeled cases…"
              : progress < 0.5
                ? "Running retrieval pipeline…"
                : progress < 0.75
                  ? "Reranking candidates…"
                  : "Scoring against ground truth…",
        }));
        if (i >= steps) {
          stop();
          onSlot(slotRef.current);
          setState((prev) => ({
            ...prev,
            active: false,
            progress: 1,
            slot: slotRef.current,
            label: `Loaded saved result (example ${slotRef.current})`,
          }));
          onComplete?.();
        }
      }, 25);
    },
    [stop],
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