"use client";

import { useEffect, useState } from "react";
import { api, type CompareResult, type EvalReport, type SuiteIndex } from "../../lib/api";
import { Badge, Card, Hero, Notice, num, ms, pct, usd, useAsync, withRateLimitRetry, type Section } from "./ui";

export function Compare() {
  const [limit, setLimit] = useState(5);
  const compare = useAsync<CompareResult>();

  const run = () => compare.run(() => api.compare(limit));
  const results = compare.data?.results ?? [];

  const row = (label: string, pick: (r: CompareResult["results"][number]) => string) => (
    <tr key={label}>
      <td>{label}</td>
      {results.map((r) => (
        <td key={r.tier}>{pick(r)}</td>
      ))}
    </tr>
  );

  return (
    <div className="stack">
      <Hero
        eyebrow="BENCHMARKS"
        title="Model comparison"
        blurb="Runs the same labeled prompt set through every tier and reports measured pass rate, latency, tokens, and cost."
        right={
          <div className="toolbar">
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
            <button className="primary" onClick={run} disabled={compare.loading}>
              {compare.loading ? "Running…" : "Run comparison"}
            </button>
          </div>
        }
      />
      <Card>
        {results.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  {results.map((r) => (
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
            {compare.loading
              ? "Running the comparison across all three tiers…"
              : "No results yet. Run the comparison to measure each tier on labeled cases."}
          </p>
        )}
        {compare.data && (
          <p className="footnote">
            Measured {compare.data.timestamp} over {compare.data.cases_per_tier} labeled
            chat cases per tier. Pass rate counts cases whose answer contained all required
            concepts and none of the forbidden ones.
          </p>
        )}
      </Card>
      <Notice error={compare.error} />
    </div>
  );
}

export function Quality({ setSection }: { setSection: (s: Section) => void }) {
  const suites = useAsync<SuiteIndex>();
  useEffect(() => {
    suites.run(withRateLimitRetry(() => api.evalSuites()));
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
  const report = useAsync<EvalReport>();
  const [limit, setLimit] = useState(5);

  useEffect(() => {
    suites.run(withRateLimitRetry(() => api.evalSuites()));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const all = suites.data?.suites.map((s) => s.name) ?? [];
  const run = () => report.run(() => api.runEvals(all, limit));

  return (
    <div className="stack">
      <Hero
        eyebrow="EVALUATION"
        title="Evaluation runs"
        blurb="Scores the live model against labeled cases: answer accuracy, structured-output validity, latency, tokens, and cost."
        right={
          <div className="toolbar">
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
            <button
              className="primary"
              onClick={run}
              disabled={report.loading || all.length === 0}
            >
              {report.loading ? "Running…" : "Run evaluation"}
            </button>
          </div>
        }
      />
      {report.data && (
        <div className="grid four">
          <Card>
            <p className="label">Overall accuracy</p>
            <strong>{pct(report.data.totals.accuracy)}</strong>
            <span className="muted">
              {report.data.totals.passed}/{report.data.totals.evaluated_cases} evaluated
            </span>
          </Card>
          <Card>
            <p className="label">Cases run</p>
            <strong>{num(report.data.totals.total_cases)}</strong>
            <span className="muted">across {report.data.suites.length} suites</span>
          </Card>
          <Card>
            <p className="label">Provider errors</p>
            <strong>{num(report.data.totals.api_errors)}</strong>
            <span className="muted">excluded from accuracy</span>
          </Card>
          <Card>
            <p className="label">Cost</p>
            <strong>{usd(report.data.totals.cost.total_usd)}</strong>
            <span className="muted">{num(report.data.totals.tokens.total)} tokens</span>
          </Card>
        </div>
      )}
      <Card>
        {report.data ? (
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
                {report.data.suites.map((s) => (
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
            {report.loading
              ? "Scoring the live model against the labeled cases…"
              : "Run an evaluation to see measured scores. Nothing here is estimated."}
          </p>
        )}
        {report.data && (
          <p className="footnote">
            Measured {report.data.timestamp}. Accuracy excludes provider errors; structured
            validity counts schema- and enum-conformant extractions.
          </p>
        )}
      </Card>
      <Notice error={report.error || suites.error} />
    </div>
  );
}
