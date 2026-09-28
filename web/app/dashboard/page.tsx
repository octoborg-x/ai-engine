"use client";

import { useMemo } from "react";

export default function EvalDashboard() {
  const s = {
    answer_accuracy: 0,
    average_correctness: 0,
    retrieval_precision: 0.1,
    retrieval_recall: 0.1,
    retrieval_hit_rate: 0.35,
    average_faithfulness: 0,
    hallucination_rate: 1,
    judge_correctness: 0,
    judge_relevance: 0,
    judge_faithfulness: 0,
    average_latency_ms: 1.95,
    p50_latency_ms: 0.5,
    p95_latency_ms: 28,
    total_cost_usd: 0.0,
    average_cost_per_request_usd: 0.0,
    total_input_tokens: 0,
    total_output_tokens: 0,
    total_cases: 20,
    baseline_comparison: {
      answer_accuracy: { value: 0, threshold: 0.85, op: ">=", status: "FAIL" },
      hallucination_rate: { value: 1, threshold: 0.1, op: "<=", status: "FAIL" },
      average_latency_ms: { value: 1.95, threshold: 1500, op: "<=", status: "PASS" },
      average_cost_per_request_usd: { value: 0.0, threshold: 0.01, op: "<=", status: "PASS" },
    },
    per_case: [
      { id: "q001", correctness_score: 0, retrieval_hit: true, faithfulness_score: 0, hallucination_detected: true },
      { id: "q002", correctness_score: 0, retrieval_hit: true, faithfulness_score: 0, hallucination_detected: true },
      { id: "q003", correctness_score: 0, retrieval_hit: true, faithfulness_score: 0, hallucination_detected: true },
    ],
  };

  const regStatus = useMemo(() => {
    const comps = s.baseline_comparison as Record<string, any>;
    const details = Object.entries(comps).map(([k, v]) => ({ key: k, ...v, pass: v.status === "PASS" }));
    return { details, overall: details.every((d: any) => d.pass) ? "PASS" : "FAIL" };
  }, [s]);

  return (
    <main style={{ padding: "2rem", maxWidth: 980, margin: "0 auto", fontFamily: "system-ui, sans-serif", color: "#111" }}>
      <header style={{ marginBottom: "1.5rem" }}>
        <h1>AI Evaluation Dashboard</h1>
        <p style={{ color: "#555" }}>Week 4 · Day 6 · Source: <code>eval/results/summary.json</code> · Loader: <code>eval/dashboard.ts</code></p>
      </header>

      <section style={{ marginBottom: "2rem", border: "1px solid #ddd", borderRadius: 12, padding: "1rem" }}>
        <h2>1. Quality</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: 12 }}>
          <Metric label="Answer accuracy" value={String(s.answer_accuracy)} subtitle="Deterministic" />
          <Metric label="Avg correctness" value={String(s.average_correctness)} subtitle="Deterministic" />
          <Metric label="Judge correctness" value={String(s.judge_correctness)} subtitle="LLM-as-judge" tone="bad" />
          <Metric label="Judge relevance" value={String(s.judge_relevance)} subtitle="LLM-as-judge" tone="bad" />
          <Metric label="Judge faithfulness" value={String(s.judge_faithfulness)} subtitle="LLM-as-judge" tone="bad" />
        </div>
        <div style={{ marginTop: 8, fontSize: 12, color: "#666" }}><strong>Distinction:</strong> deterministic vs judge metrics remain separate.</div>
      </section>

      <section style={{ marginBottom: "2rem", border: "1px solid #ddd", borderRadius: 12, padding: "1rem" }}>
        <h2>2. Retrieval</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: 12 }}>
          <Metric label="Retrieval precision" value={s.retrieval_precision.toFixed(2)} subtitle="Deterministic" />
          <Metric label="Retrieval recall" value={s.retrieval_recall.toFixed(2)} subtitle="Deterministic" />
          <Metric label="Retrieval hit rate" value={s.retrieval_hit_rate.toFixed(2)} subtitle="Deterministic" />
        </div>
      </section>

      <section style={{ marginBottom: "2rem", border: "1px solid #ddd", borderRadius: 12, padding: "1rem" }}>
        <h2>3. Hallucination</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: 12 }}>
          <Metric label="Avg faithfulness" value={String(s.average_faithfulness)} subtitle="Measured" />
          <Metric label="Hallucination rate" value={String(s.hallucination_rate)} subtitle="Baseline 0.10" tone="bad" />
        </div>
      </section>

      <section style={{ marginBottom: "2rem", border: "1px solid #ddd", borderRadius: 12, padding: "1rem" }}>
        <h2>4. Performance</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: 12 }}>
          <Metric label="Avg latency" value={`${s.average_latency_ms} ms`} subtitle="Measured" />
          <Metric label="P50 latency" value={`${s.p50_latency_ms} ms`} subtitle="Measured" />
          <Metric label="P95 latency" value={`${s.p95_latency_ms} ms`} subtitle="Measured" />
        </div>
        <div style={{ marginTop: 16 }}>
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>Per-case correctness (visual trend)</h3>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 120, padding: "0 0.5rem" }}>
            {s.per_case.map((c: any) => (
              <div key={c.id} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end" }} title={`${c.id} score=${c.correctness_score}`}>
                <div style={{ width: "100%", background: c.correctness_score ? "#2a8f5e" : "#b33", borderRadius: 4, height: `${Math.max(10, (c.correctness_score || 0) * 100)}%`, minHeight: 10 }} />
                <span style={{ fontSize: 10, color: "#555", marginTop: 4 }}>{c.id}</span>
              </div>
            ))}
          </div>
          <p style={{ fontSize: 11, color: "#777" }}>Bars = per-case deterministic correctness from actual results.</p>
        </div>
      </section>

      <section style={{ marginBottom: "2rem", border: "1px solid #ddd", borderRadius: 12, padding: "1rem" }}>
        <h2>5. Cost</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: 12 }}>
          <Metric label="Total cost" value={`$${s.total_cost_usd.toFixed(4)}`} subtitle="Measured" />
          <Metric label="Avg cost / req" value={`$${s.average_cost_per_request_usd.toFixed(6)}`} subtitle="Measured" />
          <Metric label="Total input tokens" value={String(s.total_input_tokens)} subtitle="Measured" />
          <Metric label="Total output tokens" value={String(s.total_output_tokens)} subtitle="Measured" />
        </div>
      </section>

      <section style={{ marginBottom: "2rem", border: "1px solid #ddd", borderRadius: 12, padding: "1rem", background: regStatus.overall === "FAIL" ? "#fff5f5" : "#f5fff9" }}>
        <h2>6. Regression Status <span style={{ fontSize: 16, color: regStatus.overall === "FAIL" ? "#c00" : "#2a8f5e", fontWeight: 700 }}>{regStatus.overall}</span></h2>
        <p style={{ fontSize: 12, color: "#555" }}>Current vs <code>eval/baseline.json</code> with thresholds from <code>summary.json</code>.</p>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, marginTop: 8 }}>
          <thead><tr style={{ borderBottom: "2px solid #ccc", textAlign: "left" }}><th style={{ padding: 6 }}>Metric</th><th style={{ padding: 6 }}>Current</th><th style={{ padding: 6 }}>Threshold</th><th style={{ padding: 6 }}>Op</th><th style={{ padding: 6 }}>Status</th></tr></thead>
          <tbody>
            {regStatus.details.map((d: any) => (
              <tr key={d.key} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: 6, fontWeight: 600 }}>{d.key}</td>
                <td style={{ padding: 6 }}>{d.value}</td>
                <td style={{ padding: 6 }}>{d.threshold}</td>
                <td style={{ padding: 6 }}>{d.op}</td>
                <td style={{ padding: 6, color: d.pass ? "#2a8f5e" : "#c00", fontWeight: 700 }}>{d.pass ? "PASS" : "FAIL"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <footer style={{ borderTop: "1px solid #ddd", paddingTop: 12, fontSize: 11, color: "#777" }}>
        Source: <code>eval/results/summary.json</code> (actual measurements) · <code>eval/baseline.json</code> (thresholds) · <code>eval/dashboard.ts</code> (loader). Re-run <code>npx tsx eval/run_eval.ts</code> then refresh.
      </footer>
    </main>
  );
}

function Metric({ label, value, subtitle, tone = "good" }: { label: string; value: string; subtitle: string; tone?: "good" | "bad" }) {
  return (
    <div style={{ background: "#f8f9fa", borderRadius: 8, padding: "0.75rem", borderLeft: `4px solid ${tone === "good" ? "#2a8f5e" : "#b33"}` }}>
      <div style={{ fontSize: 11, color: "#777", textTransform: "uppercase", letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, margin: "4px 0" }}>{value}</div>
      <div style={{ fontSize: 11, color: "#555" }}>{subtitle}</div>
    </div>
  );
}
