"use client";

import { useState } from "react";
import {
  api,
  type CitationReport,
  type RagAnswer,
  type ScreeningReport,
} from "../../lib/api";
import { Badge, Bar, Card, Hero, Notice, ms, pct, useAsync } from "./ui";

function Citations({ citations }: { citations?: CitationReport }) {
  if (!citations) return null;
  const { valid_citations, hallucinated_citations, coverage, source_map } = citations;
  return (
    <div className="grid two">
      <Card>
        <div className="card-head">
          <h2>Citations</h2>
          <Badge tone={hallucinated_citations.length ? "amber" : "green"}>
            coverage {pct(coverage)}
          </Badge>
        </div>
        <div className="rows">
          <div className="row">
            <span>Grounded citations</span>
            <span className="chips">
              {valid_citations.length ? (
                valid_citations.map((c) => (
                  <span className="chip" key={c}>
                    {c}
                  </span>
                ))
              ) : (
                <span className="muted">none</span>
              )}
            </span>
          </div>
          <div className="row">
            <span>Hallucinated citations</span>
            <span className="chips">
              {hallucinated_citations.length ? (
                hallucinated_citations.map((c) => (
                  <span className="chip chip-warn" key={c}>
                    {c}
                  </span>
                ))
              ) : (
                <span className="muted">none</span>
              )}
            </span>
          </div>
        </div>
      </Card>
      <Card>
        <div className="card-head">
          <h2>Source map</h2>
          <Badge>validated</Badge>
        </div>
        <div className="rows">
          {valid_citations.length ? (
            valid_citations.map((c) => (
              <div className="row" key={c}>
                <span className="chip">{c}</span>
                <span className="muted">{source_map[c]}</span>
              </div>
            ))
          ) : (
            <p className="muted">
              The answer cited no sources, so nothing could be validated.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}

export function Knowledge() {
  const [query, setQuery] = useState("What is the refund policy?");
  const ask = useAsync<RagAnswer>();
  const retrieve = useAsync<RagAnswer>();

  const runAsk = () => ask.run(() => api.ask(query));
  const runRetrieve = () => retrieve.run(() => api.ragRetrieve(query));
  const data = ask.data;
  const cand = retrieve.data?.candidates ?? [];

  return (
    <div className="stack">
      <Hero
        eyebrow="RAG"
        title="Knowledge assistant"
        blurb="Hybrid recall → cross-encoder rerank → grounded answer with validated citations. Inspect the retrieval stage without generating an answer."
      />
      <Card>
        <label>
          Question
          <input value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        <div className="toolbar" style={{ marginTop: 12 }}>
          <button className="primary" onClick={runAsk} disabled={ask.loading}>
            {ask.loading ? "Answering…" : "Ask"}
          </button>
          <button onClick={runRetrieve} disabled={retrieve.loading}>
            {retrieve.loading ? "Retrieving…" : "Retrieve only"}
          </button>
          {data?.route && (
            <span className="muted">
              {data.model} · route {data.route} · {ms(data.latency_ms)}
            </span>
          )}
        </div>
      </Card>

      {data && (
        <Card>
          <div className="card-head">
            <h2>Grounded answer</h2>
            <Badge>grounded</Badge>
          </div>
          <p className="answer">{data.answer}</p>
        </Card>
      )}

      {data && <Citations citations={data.citations} />}

      {cand.length > 0 && (
        <Card>
          <div className="card-head">
            <h2>Retrieval candidates</h2>
            <Badge>
              {cand.filter((c) => c.kept).length} kept of {cand.length}
            </Badge>
          </div>
          <div className="rows">
            {cand.map((c) => (
              <div className="row candidate" key={c.chunk_id}>
                <div className="cand-head">
                  <span className="chip">{c.chunk_id}</span>
                  <span className="muted">
                    {c.source}
                    {c.section ? ` · ${c.section}` : ""}
                  </span>
                  {c.kept ? <Badge>kept</Badge> : <Badge tone="amber">dropped</Badge>}
                </div>
                <p className="muted cand-text">{c.text}</p>
                <div className="metric-line">
                  <span>recall ({c.recall_type})</span>
                  <span>{c.recall_score.toFixed(3)}</span>
                </div>
                <div className="metric-line">
                  <span>rerank score</span>
                  <span>{c.rerank_score == null ? "—" : c.rerank_score.toFixed(3)}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Notice error={ask.error || retrieve.error} />
    </div>
  );
}

const EXAMPLE_JD = `Senior Backend Engineer

We are hiring a backend engineer to own our LLM platform services.

Required skills:
- Python
- FastAPI
- PostgreSQL
- Docker and Kubernetes

Minimum 5 years of professional backend experience.

Nice to have:
- Experience with vector databases (pgvector or similar)
- Observability tooling (OpenTelemetry)

Responsibilities:
- Design and ship production APIs
- Own reliability and performance
- Mentor engineers`;

const EXAMPLE_RESUME = `Ada Lovelace — Backend Engineer

8 years building production services.

Skills: Python, FastAPI, PostgreSQL, Docker, Redis, Terraform, OpenTelemetry

Experience:
- Led migration of a monolith to FastAPI microservices serving 4M requests/day
- Built an internal retrieval service backed by pgvector
- Mentored three engineers through promotion

Education: MSc Computer Science`;

export function Recruitment() {
  const [jd, setJd] = useState(EXAMPLE_JD);
  const [resume, setResume] = useState(EXAMPLE_RESUME);
  const screen = useAsync<ScreeningReport>();

  const run = () => screen.run(() => api.screen(jd, resume));
  const r = screen.data;
  const tone =
    r?.recommendation === "advance"
      ? "green"
      : r?.recommendation === "hold"
        ? "amber"
        : "violet";

  return (
    <div className="stack">
      <Hero
        eyebrow="USE CASE"
        title="Recruitment screening"
        blurb="Paste a job description and a resume. The model extracts structure; a deterministic rubric scores the match and shows the evidence."
        right={
          <button className="primary" onClick={run} disabled={screen.loading}>
            {screen.loading ? "Screening…" : "Screen candidate"}
          </button>
        }
      />
      <div className="grid two">
        <Card>
          <label>
            Job description
            <textarea value={jd} onChange={(e) => setJd(e.target.value)} rows={14} />
          </label>
        </Card>
        <Card>
          <label>
            Candidate resume
            <textarea value={resume} onChange={(e) => setResume(e.target.value)} rows={14} />
          </label>
        </Card>
      </div>

      {r && (
        <>
          <div className="grid three">
            <Card>
              <p className="label">Match score</p>
              <strong>{r.match_score}</strong>
              <Bar value={r.match_score / 100} tone={tone} />
              <span className="muted">deterministic rubric</span>
            </Card>
            <Card>
              <p className="label">Recommendation</p>
              <Badge tone={tone}>{r.recommendation}</Badge>
              <span className="muted">thresholds: advance ≥ 75 · hold ≥ 50</span>
            </Card>
            <Card>
              <p className="label">Parsed by</p>
              <strong style={{ fontSize: 18 }}>{r.model}</strong>
              <span className="muted">
                route {r.route} · {ms(r.latency_ms)}
              </span>
            </Card>
          </div>
          <div className="grid two">
            <Card>
              <div className="card-head">
                <h2>{r.candidate.name}</h2>
                <Badge>{r.candidate.years_experience} yrs</Badge>
              </div>
              <div className="chips">
                {r.candidate.skills.map((s) => (
                  <span className="chip" key={s}>
                    {s}
                  </span>
                ))}
              </div>
              <div className="metric-line">
                <span>Education</span>
                <span>{r.candidate.education || "—"}</span>
              </div>
            </Card>
            <Card>
              <div className="card-head">
                <h2>{r.requirements.role}</h2>
                <Badge>requires {r.requirements.min_years} yrs</Badge>
              </div>
              <div className="metric-line">
                <span>Matched skills</span>
                <span className="chips">
                  {r.matched_skills.map((s) => (
                    <span className="chip" key={s}>
                      {s}
                    </span>
                  ))}
                </span>
              </div>
              <div className="metric-line">
                <span>Missing skills</span>
                <span className="chips">
                  {r.missing_skills.length ? (
                    r.missing_skills.map((s) => (
                      <span className="chip chip-warn" key={s}>
                        {s}
                      </span>
                    ))
                  ) : (
                    <span className="muted">none</span>
                  )}
                </span>
              </div>
            </Card>
          </div>
          <Card>
            <div className="card-head">
              <h2>Evidence</h2>
              <Badge>auditable</Badge>
            </div>
            <div className="rows">
              {r.evidence.map((e, i) => (
                <div className="row" key={i}>
                  <span>{e.criterion}</span>
                  <span className="muted">{e.detail}</span>
                  <Badge tone={e.matched ? "green" : "amber"}>
                    {e.matched ? "met" : "not met"}
                  </Badge>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
      <Notice error={screen.error} />
    </div>
  );
}
