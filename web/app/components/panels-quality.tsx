"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  type CompareResult,
  type EvalReport,
  type SavedResult,
  type SuiteIndex,
} from "../../lib/api";
import { Badge, Card, Hero, Notice, num, ms, pct, usd, useAsync, type Section } from "./ui";
import { friendlyApiError, RequestRunControls } from "./run-controls";

export function Compare() {
  const [limit, setLimit] = useState(5);
  const [results, setResults] = useState<CompareResult | null>(null);
  const [source, setSource] = useState<"saved" | "live">("saved");
  const [slotLabel, setSlotLabel] = useState("saved example");
  const [realBusy, setRealBusy] = useState(false);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    // Default view comes from a saved file — opening the tab never exhausts
    // the provider by triggering a fresh comparison.
    api
      .resultsSaved<CompareResult>("compare")
      .then((r) => {
        setResults(r);
        setSource("saved");
        setSlotLabel(`saved example ${r._meta?.slot ?? "—"}`);
      })
      .catch(() => setLoadError("No saved comparison yet. Use a real run once to capture one."));
  }, []);

  const fakeRun = useCallback(
    (slot: number) => {
      setLoadError("");
      api
        .resultsSaved<CompareResult>("compare", slot)
        .then((r) => {
          setResults(r);
          setSource("saved");
          setSlotLabel(`saved example ${r._meta?.slot ?? slot}`);
        })
        .catch((e) => setLoadError(friendlyApiError(e)));
    },
    [],
  );

  const realRun = async () => {
    setRealBusy(true);
    setLoadError("");
    try {
      const r = await api.compare(limit);
      setResults(r);
      setSource("live");
      setSlotLabel("live run");
      // Persist so subsequent fake runs rotate through this measured result.
      await api.resultsSave("compare", r).catch(() => undefined);
    } finally {
      setRealBusy(false);
    }
  };

  const rows = results?.results ?? [];
  const row = (label: string, pick: (r: CompareResult["results"][number]) => string) => (
    <tr key={label}>
      <td>{label}</td>
      {rows.map((r) => (
        <td key={r.tier}>{pick(r)}</td>
      ))}
    </tr>
  );

  return (
    <div className="stack">
      <Hero
        eyebrow="BENCHMARKS"
        title="Model comparison"
        blurb="Same labeled prompt set through every tier (main, cheap, balanced, powerful): pass rate, latency, tokens, cost. Fake runs replay saved files; real runs measure the live provider."
        right={
          <label>
            Cases per tier
            <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              {[3, 5, 8, 10].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
        }
      />
      <RequestRunControls
        tab="compare"
        onFakeRun={fakeRun}
        onRealRun={realRun}
        realBusy={realBusy}
        realLabel="Real run"
        fakeLabel="Fake run"
      />
      <Card>
        <div className="card-head">
          <h2>Measured results</h2>
          {results && (
            <Badge tone={source === "live" ? "green" : "blue"}>
              {source === "live" ? "● live" : slotLabel}
            </Badge>
          )}
        </div>
        {rows.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  {rows.map((r) => (
                    <th key={r.tier}>
                      {r.tier}
                      <span className="muted"> · {r.model}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {row("Cases", (r) => num(r.cases))}
                {row("Pass rate", (r) => pct(r.pass_rate))}
                {row("Avg latency", (r) => ms(r.latency_ms.average))}
                {row("P95 latency", (r) => ms(r.latency_ms.p95))}
                {row("Avg tokens", (r) => num(r.tokens.average))}
                {row("Cost / run", (r) => usd(r.cost.average_per_request_usd))}
                {row("Provider errors", (r) => num(r.errors))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">
            No results yet. Press <em>Fake run</em> to view a saved comparison, or{" "}
            <em>Real run</em> to measure the live model.
          </p>
        )}
        {results && (
          <p className="footnote">
            Measured {results.timestamp} over {results.cases_per_tier} labeled chat cases
            per tier. Pass rate counts cases whose answer contained all required concepts
            and none of the forbidden ones. {source === "saved" ? "Source: saved result file." : "Source: live provider run."}
          </p>
        )}
      </Card>
      <Notice error={loadError} />
    </div>
  );
}

export function Quality({ setSection }: { setSection: (s: Section) => void }) {
  const suites = useAsync<SuiteIndex>();
  useEffect(() => {
    suites.run(() => api.evalSuites());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="stack">
      <Hero
        eyebrow="QUALITY"
        title="Evaluation suites"
        blurb="The labeled datasets the backend can run. Counts come from the packaged case files."
        right={
          <div className="toolbar">
            <a className="link" href="/dashboard">
              Retrieval dashboard →
            </a>
            <button className="primary" onClick={() => setSection("evals")}>
              Run evaluations →
            </button>
          </div>
        }
      />
      <div className="grid two">
        {(suites.data?.suites ?? []).map((s) => (
          <Card key={s.name}>
            <div className="card-head">
              <h2>{s.name}</h2>
              <Badge>indexed</Badge>
            </div>
            <strong>{s.cases} cases</strong>
            <div className="metric-line">
              <span>Dataset</span>
              <code>{s.file}</code>
            </div>
          </Card>
        ))}
        {!suites.data && (
          <Card>
            <p className="muted">Loading suites…</p>
          </Card>
        )}
      </div>
      <Notice error={suites.error} />
    </div>
  );
}

export function Evals() {
  const suites = useAsync<SuiteIndex>();
  const [limit, setLimit] = useState(5);
  const [report, setReport] = useState<SavedResult<EvalReport> | null>(null);
  const [source, setSource] = useState<"saved" | "live">("saved");
  const [slotLabel, setSlotLabel] = useState("saved example");
  const [realBusy, setRealBusy] = useState(false);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    suites.run(() => api.evalSuites());
    api
      .resultsSaved<EvalReport>("evals")
      .then((r) => {
        setReport(r);
        setSource("saved");
        setSlotLabel(`saved example ${r._meta?.slot ?? "—"}`);
      })
      .catch(() => setLoadError("No saved evaluation yet. Use a real run once to capture one."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const all = suites.data?.suites.map((s) => s.name) ?? [];

  const fakeRun = useCallback((slot: number) => {
    setLoadError("");
    api
      .resultsSaved<EvalReport>("evals", slot)
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
      const r = await api.runEvals(all, limit);
      setReport({ ...r, _meta: undefined });
      setSource("live");
      setSlotLabel("live run");
      await api.resultsSave("evals", r).catch(() => undefined);
    } finally {
      setRealBusy(false);
    }
  };

  return (
    <div className="stack">
      <Hero
        eyebrow="EVALUATION"
        title="Evaluation runs"
        blurb="Scores the live model against labeled cases: accuracy, structured validity, latency, tokens, cost. Fake runs replay saved files; real runs measure the live provider."
        right={
          <label>
            Cases per suite
            <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              {[3, 5, 8, 10].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
        }
      />
      <RequestRunControls
        tab="evals"
        onFakeRun={fakeRun}
        onRealRun={realRun}
        realBusy={realBusy}
        realDisabled={!suites.data}
        realLabel="Real run"
        fakeLabel="Fake run"
      />
      {report && (
        <div className="grid four">
          <Card>
            <p className="label">Overall accuracy</p>
            <strong>{pct(report.totals.accuracy)}</strong>
            <span className="muted">
              {report.totals.passed}/{report.totals.evaluated_cases} evaluated
            </span>
          </Card>
          <Card>
            <p className="label">Cases run</p>
            <strong>{num(report.totals.total_cases)}</strong>
            <span className="muted">across {report.suites.length} suites</span>
          </Card>
          <Card>
            <p className="label">Provider errors</p>
            <strong>{num(report.totals.api_errors)}</strong>
            <span className="muted">excluded from accuracy</span>
          </Card>
          <Card>
            <p className="label">Cost</p>
            <strong>{usd(report.totals.cost.total_usd)}</strong>
            <span className="muted">{num(report.totals.tokens.total)} tokens</span>
          </Card>
        </div>
      )}
      <Card>
        <div className="card-head">
          <h2>Suite scores</h2>
          {report && (
            <Badge tone={source === "live" ? "green" : "blue"}>
              {source === "live" ? "● live" : slotLabel}
            </Badge>
          )}
        </div>
        {report ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Suite</th>
                  <th>Cases</th>
                  <th>Accuracy</th>
                  <th>Secondary</th>
                  <th>API errors</th>
                  <th>P95 latency</th>
                  <th>Tokens</th>
                  <th>Cost</th>
                </tr>
              </thead>
              <tbody>
                {report.suites.map((s) => (
                  <tr key={s.suite}>
                    <td>{s.suite}</td>
                    <td>{s.total_cases}</td>
                    <td>{pct(s.accuracy)}</td>
                    <td>
                      {s.retrieval
                        ? `recall@${s.retrieval.k} ${pct(s.retrieval.recall_at_k)}`
                        : pct(s.structured_output_validity)}
                    </td>
                    <td>{pct(s.api_error_rate)}</td>
                    <td>{ms(s.latency_ms.p95)}</td>
                    <td>{num(s.tokens.total)}</td>
                    <td>{usd(s.cost.total_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">
            Run a fake run to view the saved scores, or a real run to measure them live.
            Nothing here is estimated.
          </p>
        )}
        {report && (
          <p className="footnote">
            Measured {report.timestamp}. Accuracy excludes provider errors; structured
            validity counts schema- and enum-conformant extractions.{" "}
            {source === "saved" ? "Source: saved result file." : "Source: live provider run."}
          </p>
        )}
      </Card>
      <Notice error={loadError || suites.error} />
    </div>
  );
}
