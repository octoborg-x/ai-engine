"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  type EvalReport,
  type SavedResult,
} from "../../lib/api";
import { Badge, Card, Hero, Notice, num, ms, pct, usd } from "../components/ui";
import { friendlyApiError, RequestRunControls } from "../components/run-controls";

// Retrieval-quality dashboard. Everything shown here is measured by the
// backend's deterministic retrieval suite (hybrid recall + rerank against
// labeled relevant chunks). A fake run replays the saved result files; the
// real run hits the (offline, provider-free) pipeline.
export default function EvalDashboard() {
  const [limit, setLimit] = useState(10);
  const [report, setReport] = useState<SavedResult<EvalReport> | null>(null);
  const [source, setSource] = useState<"saved" | "live">("saved");
  const [slotLabel, setSlotLabel] = useState("saved example");
  const [realBusy, setRealBusy] = useState(false);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    // Default view comes from a saved file — opening the dashboard never
    // triggers a new run.
    api
      .resultsSaved<EvalReport>("retrieval")
      .then((r) => {
        setReport(r);
        setSource("saved");
        setSlotLabel(`saved example ${r._meta?.slot ?? "—"}`);
      })
      .catch(() =>
        setLoadError("No saved retrieval result yet. Use a real run once to capture one."),
      );
  }, []);

  const fakeRun = useCallback((slot: number) => {
    setLoadError("");
    api
      .resultsSaved<EvalReport>("retrieval", slot)
      .then((r) => {
        setReport(r);
        setSource("saved");
        setSlotLabel(`saved example ${r._meta?.slot ?? slot}`);
      })
      .catch((e) => setLoadError(friendlyApiError(e)));
  }, []);

  const realRun = async () => {
    setRealBusy(true);
    setLoadError("");
    try {
      // Deterministic offline pipeline: no provider calls, so this is cheap.
      const r = await api.runEvals(["retrieval"], limit);
      setReport({ ...r, _meta: undefined });
      setSource("live");
      setSlotLabel("live run");
      await api.resultsSave("retrieval", r).catch(() => undefined);
    } finally {
      setRealBusy(false);
    }
  };

  const suite = report?.suites.find((s) => s.suite === "retrieval");
  const r = suite?.retrieval;

  return (
    <main className="shell" style={{ display: "block" }}>
      <section className="main" style={{ maxWidth: 1100, margin: "0 auto", padding: 34 }}>
        <Hero
          eyebrow="RETRIEVAL QUALITY"
          title="RAG evaluation dashboard"
          blurb="Measured retrieval quality over labeled questions: precision@k, recall@k, hit rate, and MRR from the backend's hybrid recall + rerank pipeline."
          right={
            <label>
              Cases
              <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
                {[5, 10].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          }
        />
        <RequestRunControls
          tab="retrieval"
          onFakeRun={fakeRun}
          onRealRun={realRun}
          realBusy={realBusy}
          realLabel="Real run"
          fakeLabel="Fake run"
        />

        {report && suite && r ? (
          <>
            <div className="grid four">
              <Card>
                <p className="label">Hit rate@{r.k}</p>
                <strong>{pct(r.hit_rate_at_k)}</strong>
                <span className="muted">relevant chunk in top {r.k}</span>
              </Card>
              <Card>
                <p className="label">Recall@{r.k}</p>
                <strong>{pct(r.recall_at_k)}</strong>
                <span className="muted">of labeled relevant chunks</span>
              </Card>
              <Card>
                <p className="label">Precision@{r.k}</p>
                <strong>{pct(r.precision_at_k)}</strong>
                <span className="muted">of retrieved chunks relevant</span>
              </Card>
              <Card>
                <p className="label">MRR</p>
                <strong>{r.mrr.toFixed(2)}</strong>
                <span className="muted">mean reciprocal rank</span>
              </Card>
            </div>

            <div className="grid three">
              <Card>
                <p className="label">Cases</p>
                <strong>{num(suite.total_cases)}</strong>
                <span className="muted">labeled questions</span>
              </Card>
              <Card>
                <p className="label">P95 latency</p>
                <strong>{ms(suite.latency_ms.p95)}</strong>
                <span className="muted">retrieval only, no LLM</span>
              </Card>
              <Card>
                <p className="label">Cost</p>
                <strong>{usd(suite.cost.total_usd)}</strong>
                <span className="muted">deterministic pipeline</span>
              </Card>
            </div>

            <Card>
              <div className="card-head">
                <h2>Regression targets</h2>
                <Badge tone={source === "live" ? "green" : "blue"}>
                  {source === "live" ? "● live" : slotLabel}
                </Badge>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th>Measured</th>
                      <th>Engineering target</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    <Target
                      label="Hit rate@3"
                      value={r.hit_rate_at_k}
                      threshold={0.9}
                      op=">="
                    />
                    <Target
                      label="Recall@3"
                      value={r.recall_at_k}
                      threshold={0.8}
                      op=">="
                    />
                    <Target label="MRR" value={r.mrr} threshold={0.7} op=">=" />
                  </tbody>
                </table>
              </div>
              <p className="footnote">
                Measured {report.timestamp}. Targets are engineering
                thresholds, not measured results; the dashboard shows the real
                measurement beside them so regressions are visible.{" "}
                {source === "saved" ? "Source: saved result file." : "Source: live offline run."}
              </p>
            </Card>
          </>
        ) : (
          <Card>
            <p className="muted">
              No measurement yet. Press <em>Fake run</em> to view a saved
              retrieval result, or <em>Real run</em> to measure the offline
              pipeline.
            </p>
          </Card>
        )}

        <Notice error={loadError} />
        <p className="footnote" style={{ marginTop: 18 }}>
          Retrieval is deterministic and offline, so this suite costs nothing and
          runs without a provider. Model-quality suites (chat, extraction,
          classification, adversarial) are on the Evals page.
        </p>
      </section>
    </main>
  );
}

function Target({
  label,
  value,
  threshold,
  op,
}: {
  label: string;
  value: number;
  threshold: number;
  op: string;
}) {
  const pass = op === ">=" ? value >= threshold : value <= threshold;
  return (
    <tr>
      <td>{label}</td>
      <td>{pct(value)}</td>
      <td>
        {op} {pct(threshold)}
      </td>
      <td>
        <Badge tone={pass ? "green" : "amber"}>{pass ? "PASS" : "BELOW"}</Badge>
      </td>
    </tr>
  );
}
