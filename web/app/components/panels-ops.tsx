"use client";

import { useEffect } from "react";
import { api, type Observability, type SecurityPolicy } from "../../lib/api";
import { Badge, Bar, Card, Hero, Notice, ms, num, usd, useAsync, withRateLimitRetry } from "./ui";

export function Auth() {
  const policy = useAsync<SecurityPolicy>();
  useEffect(() => {
    policy.run(withRateLimitRetry(() => api.securityPolicy()));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const p = policy.data;

  return (
    <div className="stack">
      <Hero
        eyebrow="SECURITY"
        title="Authentication"
        blurb="Bearer authentication is enforced by backend middleware. The browser never receives the token."
        right={
          <Badge tone={p?.auth.enabled ? "green" : "amber"}>
            {p?.auth.enabled ? "enforced" : "disabled"}
          </Badge>
        }
      />
      <div className="grid two">
        <Card>
          <div className="card-head">
            <h2>Token boundary</h2>
            <Badge>server-side</Badge>
          </div>
          <div className="rows">
            <div className="row">
              <span>Scheme</span>
              <code>{p?.auth.scheme ?? "bearer"}</code>
            </div>
            <div className="row">
              <span>Header</span>
              <code>{p?.auth.header ?? "Authorization: Bearer …"}</code>
            </div>
            <div className="row">
              <span>Injection point</span>
              <code>Next.js route handler</code>
            </div>
            <div className="row">
              <span>Browser</span>
              <span className="muted">Never receives the API token</span>
            </div>
          </div>
        </Card>
        <Card>
          <div className="card-head">
            <h2>Protected routes</h2>
            <Badge>{p?.protected_routes.length ?? 0}</Badge>
          </div>
          <div className="chips">
            {(p?.protected_routes ?? []).map((route) => (
              <span className="chip" key={route}>
                {route}
              </span>
            ))}
          </div>
          <p className="muted" style={{ marginTop: 12 }}>
            Public: {(p?.public_routes ?? ["GET /health"]).join(", ")}
          </p>
        </Card>
      </div>
      <Notice error={policy.error} />
    </div>
  );
}

export function Rate() {
  const policy = useAsync<SecurityPolicy>();
  useEffect(() => {
    policy.run(withRateLimitRetry(() => api.securityPolicy()));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const rl = policy.data?.rate_limit;

  return (
    <div className="stack">
      <Hero
        eyebrow="PROTECTION"
        title="Rate limits"
        blurb="Process-local fixed window keyed on the direct peer address. Forwarding headers are ignored, so the limit cannot be bypassed with a spoofed X-Forwarded-For."
        right={<Badge>{rl ? `${rl.limit} / ${rl.window_seconds}s` : "loading"}</Badge>}
      />
      <Card>
        <div className="rate">
          <div>
            <span className="label">Configured window</span>
            <strong>{rl ? `${rl.limit} requests` : "—"}</strong>
          </div>
          <Bar value={1} tone="green" />
          <div className="row">
            <span>Window</span>
            <span>{rl ? `${rl.window_seconds} seconds` : "—"}</span>
          </div>
          <div className="row">
            <span>Key</span>
            <span className="muted">{rl?.key ?? "—"}</span>
          </div>
          <div className="row">
            <span>Response headers</span>
            <span className="chips">
              {(rl?.headers ?? []).map((h) => (
                <span className="chip" key={h}>
                  {h}
                </span>
              ))}
            </span>
          </div>
        </div>
      </Card>
      <Notice error={policy.error} />
    </div>
  );
}

export function Logs() {
  const obs = useAsync<Observability>();
  const load = () => obs.run(withRateLimitRetry(() => api.observability(30)));
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const requests = obs.data?.requests ?? [];
  const calls = obs.data?.llm_calls ?? [];

  return (
    <div className="stack">
      <Hero
        eyebrow="OBSERVABILITY"
        title="Recent activity"
        blurb="Live request and LLM-call records with correlation IDs, latency, and token usage. Metadata only — no prompt content is stored."
        right={
          <button onClick={load} disabled={obs.loading}>
            {obs.loading ? "Refreshing…" : "Refresh"}
          </button>
        }
      />
      <Card>
        <div className="card-head">
          <h2>Requests</h2>
          <Badge>{requests.length}</Badge>
        </div>
        {requests.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Method</th>
                  <th>Path</th>
                  <th>Status</th>
                  <th>Latency</th>
                  <th>Request ID</th>
                  <th>Trace ID</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((r) => (
                  <tr key={r.request_id}>
                    <td>{r.method}</td>
                    <td>
                      <code>{r.path}</code>
                    </td>
                    <td>
                      <Badge tone={r.success ? "green" : "amber"}>{r.status}</Badge>
                    </td>
                    <td>{ms(r.latency_ms)}</td>
                    <td>
                      <code>{r.request_id.slice(0, 12)}…</code>
                    </td>
                    <td>
                      <code>{r.trace_id.slice(0, 12)}…</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">
            {obs.loading ? "Loading records…" : "No requests recorded yet."}
          </p>
        )}
      </Card>
      <Card>
        <div className="card-head">
          <h2>LLM calls</h2>
          <Badge>{calls.length}</Badge>
        </div>
        {calls.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Tier</th>
                  <th>Status</th>
                  <th>Latency</th>
                  <th>Tokens</th>
                  <th>Cost</th>
                </tr>
              </thead>
              <tbody>
                {calls.map((c, i) => (
                  <tr key={`${c.request_id}-${i}`}>
                    <td>
                      <code>{c.model}</code>
                    </td>
                    <td>{c.tier}</td>
                    <td>
                      <Badge tone={c.status === "success" ? "green" : "amber"}>
                        {c.status}
                      </Badge>
                    </td>
                    <td>{ms(c.latency_ms)}</td>
                    <td>{num(c.total_tokens)}</td>
                    <td>{usd(c.cost_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">
            No LLM calls recorded yet. Run a chat or evaluation to populate this.
          </p>
        )}
      </Card>
      <Notice error={obs.error} />
    </div>
  );
}

export function Settings() {
  const rows: [string, string][] = [
    ["Backend proxy", "/api/backend/*"],
    ["Backend origin", "BACKEND_URL"],
    ["Model configuration", "MODEL_CHEAP / BALANCED / POWERFUL"],
    ["Rate limit", "RATE_LIMIT_REQUESTS / RATE_LIMIT_WINDOW_SECONDS"],
    ["Auth", "API_AUTH_TOKEN (server-side only)"],
    ["Chat", "POST /chat · POST /chat/stream"],
    ["Knowledge", "POST /ask · POST /rag/retrieve"],
    ["Evaluation", "GET /compare · POST /evals/run"],
    ["Recruitment", "POST /recruitment/screen"],
    ["Telemetry", "GET /metrics · GET /observability/requests"],
    ["Security", "GET /security/policy · GET /models"],
  ];
  return (
    <div className="stack">
      <Hero
        eyebrow="CONFIGURATION"
        title="Settings"
        blurb="Environment boundaries and the backend surface this console talks to."
      />
      <Card>
        <div className="rows">
          {rows.map(([k, v]) => (
            <div className="row" key={k}>
              <span>{k}</span>
              <code>{v}</code>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
