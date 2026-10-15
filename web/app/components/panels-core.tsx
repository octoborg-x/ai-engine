"use client";

import { useEffect, useState } from "react";
import { api, streamChat, type MetricsSnapshot, type ModelTier, type Tier } from "../../lib/api";
import { Badge, Card, Hero, Notice, num, ms, usd, useAsync, type Section } from "./ui";

export function Overview({ setSection }: { setSection: (s: Section) => void }) {
  const health = useAsync<{ status: string }>();
  const metrics = useAsync<MetricsSnapshot>();
  const models = useAsync<{ tiers: ModelTier[] }>();

  useEffect(() => {
    health.run(() => api.health());
    metrics.run(() => api.metrics());
    models.run(() => api.models());
  }, [health, metrics, models]);

  const m = metrics.data;
  const totalHttp = m
    ? Object.values(m.http_requests_total).reduce((a, b) => a + b, 0)
    : null;
  const llmCalls = m ? Object.values(m.llm_calls_total).reduce((a, b) => a + b, 0) : null;
  const llmLatencies = m ? Object.values(m.llm_latency_ms_avg) : [];

  return (
    <>
      <Hero
        eyebrow="AI ENGINEERING CONSOLE"
        title="Backend control plane"
        blurb="One monolith, one repository. Every panel reads live backend state — no placeholder numbers."
        right={
          <Badge tone={health.data?.status === "ok" ? "green" : "amber"}>
            {health.data?.status === "ok" ? "● API ready" : "● checking"}
          </Badge>
        }
      />
      <div className="grid four">
        <Card>
          <p className="label">LLM calls</p>
          <strong>{num(llmCalls)}</strong>
          <span className="muted">measured since process start</span>
        </Card>
        <Card>
          <p className="label">HTTP requests</p>
          <strong>{num(totalHttp)}</strong>
          <span className="muted">across all routes</span>
        </Card>
        <Card>
          <p className="label">Total tokens</p>
          <strong>{num(m?.llm_total_tokens_total)}</strong>
          <span className="muted">
            in {num(m?.llm_input_tokens_total)} · out {num(m?.llm_output_tokens_total)}
          </span>
        </Card>
        <Card>
          <p className="label">Estimated cost</p>
          <strong>{usd(m?.llm_estimated_cost_usd_total)}</strong>
          <span className="muted">
            {llmLatencies.length ? `avg latency ${ms(llmLatencies[0])}` : "no LLM calls yet"}
          </span>
        </Card>
      </div>
      <div className="grid two">
        <Card>
          <div className="card-head">
            <h2>Routing tiers</h2>
            <Badge>live</Badge>
          </div>
          <div className="rows">
            {(models.data?.tiers ?? []).map((t) => (
              <div className="row" key={t.tier}>
                <span className="chip">{t.tier}</span>
                <code>{t.model}</code>
                <Badge tone={t.fallback ? "amber" : "green"}>
                  {t.configured ? "configured" : t.fallback ? "fallback" : "unset"}
                </Badge>
              </div>
            ))}
            {!models.data && <p className="muted">Loading tiers…</p>}
          </div>
        </Card>
        <Card>
          <div className="card-head">
            <h2>Quick actions</h2>
          </div>
          <div className="actions">
            <button onClick={() => setSection("playground")}>Stream a chat →</button>
            <button onClick={() => setSection("compare")}>Run tier comparison →</button>
            <button onClick={() => setSection("evals")}>Run evaluations →</button>
            <button onClick={() => setSection("knowledge")}>Ask the knowledge base →</button>
            <button onClick={() => setSection("recruitment")}>Screen a candidate →</button>
          </div>
        </Card>
      </div>
      <Notice error={health.error || metrics.error || models.error} />
    </>
  );
}

export function Playground() {
  const [prompt, setPrompt] = useState("Explain dependency inversion in one paragraph.");
  const [output, setOutput] = useState("");
  const [running, setRunning] = useState(false);
  const [tier, setTier] = useState<Tier | "">("");
  const [meta, setMeta] = useState("Ready");

  async function run() {
    setRunning(true);
    setOutput("");
    setMeta("Streaming…");
    const started = performance.now();
    try {
      await streamChat(prompt, tier, setOutput);
      setMeta(
        `Completed · ${Math.round(performance.now() - started)} ms · ${
          tier ? `tier pinned to ${tier}` : "tier chosen by backend router"
        }`,
      );
    } catch (e) {
      setMeta(e instanceof Error ? e.message : "Request failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="stack">
      <Hero
        eyebrow="PLAYGROUND"
        title="Streaming chat"
        blurb="Streams /chat/stream through the server-side proxy. Pin a tier to force routing, or leave it automatic."
        right={
          <Badge tone={running ? "blue" : "green"}>
            {running ? "● streaming" : "● idle"}
          </Badge>
        }
      />
      <Card>
        <div className="toolbar">
          <label>
            Model tier
            <select value={tier} onChange={(e) => setTier(e.target.value as Tier | "")}>
              <option value="">Auto (backend router)</option>
              <option value="cheap">Cheap</option>
              <option value="balanced">Balanced</option>
              <option value="powerful">Powerful</option>
            </select>
          </label>
          <span className="muted">The selected tier is enforced by the backend.</span>
        </div>
        <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={5} />
        <div className="toolbar">
          <button className="primary" onClick={run} disabled={running || !prompt.trim()}>
            {running ? "Streaming…" : "Send"}
          </button>
          <span className="muted">{meta}</span>
        </div>
        <div className="response">
          <div className="label">Response</div>
          <p>{output || "Your streamed response will appear here."}</p>
        </div>
      </Card>
    </div>
  );
}

export function Models() {
  const models = useAsync<{ tiers: ModelTier[] }>();
  useEffect(() => {
    models.run(() => api.models());
  }, [models]);

  const tone = (tier: string) =>
    tier === "cheap" ? "green" : tier === "balanced" ? "blue" : "violet";

  return (
    <div className="stack">
      <Hero
        eyebrow="MODEL ROUTING"
        title="Providers & tiers"
        blurb="The model each tier resolves to, read from backend configuration. Routing is deterministic and adds no token cost."
      />
      <div className="grid three">
        {(models.data?.tiers ?? []).map((t) => (
          <Card key={t.tier}>
            <Badge tone={tone(t.tier)}>{t.tier}</Badge>
            <h2>{t.model}</h2>
            <p className="muted">
              <code>{t.env_var}</code>
            </p>
            <div className="row">
              <span>Configured</span>
              <Badge tone={t.configured ? "green" : "amber"}>
                {t.configured ? "yes" : t.fallback ? "fallback" : "no"}
              </Badge>
            </div>
          </Card>
        ))}
        {!models.data && (
          <Card>
            <p className="muted">Loading…</p>
          </Card>
        )}
      </div>
      <Notice error={models.error} />
    </div>
  );
}
