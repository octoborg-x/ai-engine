"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  type CitationReport,
  type ModelTier,
  type RagAnswer,
  type SavedResult,
  type ScreeningReport,
  type SourcesResponse,
  type Tier,
} from "../../lib/api";
import { Badge, Bar, Card, Hero, Notice, ms, pct, useAsync } from "./ui";
import { friendlyApiError, RequestRunControls } from "./run-controls";

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

function kb(bytes: number) {
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${bytes} B`;
}

export function Knowledge() {
  const [query, setQuery] = useState("What is the refund policy?");
  const [file, setFile] = useState<File | null>(null);
  const [tier, setTier] = useState<Tier>("main");
  const models = useAsync<{ tiers: ModelTier[] }>();
  const ask = useAsync<RagAnswer>();
  const retrieve = useAsync<RagAnswer>();
  const sources = useAsync<SourcesResponse>();
  const upload = useAsync<{ ok: boolean; name: string }>();
  const remove = useAsync<{ ok: boolean }>();

  useEffect(() => {
    models.run(() => api.models());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refresh = () => sources.run(() => api.ragSources());
  const runAsk = () => ask.run(() => api.ask(query, { tier }));
  const runRetrieve = () => retrieve.run(() => api.ragRetrieve(query));

  const modelLabel = (t: ModelTier) =>
    t.tier === "main"
      ? `${t.model} (main)`
      : t.tier === "openai-compatible"
        ? `${t.model} (openai-compatible)`
        : `${t.model} — ${t.tier}`;

  const onUpload = () => {
    if (!file) return;
    upload.run(() => api.ragUpload(file)).then((res) => {
      if (res?.ok) {
        setFile(null);
        refresh();
      }
    });
  };
  const onRemove = (name: string) =>
    remove.run(() => api.ragDelete(name)).then((res) => {
      if (res?.ok) refresh();
    });

  const data = ask.data;
  const cand = retrieve.data?.candidates ?? [];
  const files = sources.data?.sources ?? [];

  return (
    <div className="stack">
      <Hero
        eyebrow="RAG"
        title="Knowledge assistant"
        blurb="Hybrid recall → cross-encoder rerank → grounded answer with validated citations. Inspect the retrieval stage without generating an answer."
      />
      <Card>
        <div className="card-head">
          <h2>Knowledge files</h2>
          <div className="chips">
            <Badge tone="green">
              {files.filter((f) => f.kind === "local").length} local
            </Badge>
            <Badge tone={files.some((f) => f.kind === "upload") ? "amber" : "green"}>
              {files.filter((f) => f.kind === "upload").length} uploaded
            </Badge>
          </div>
        </div>
        <div className="rows">
          {files.length ? (
            files.map((f) => (
              <div className="row" key={`${f.kind}:${f.name}`}>
                <span>
                  <span className={`chip ${f.kind === "upload" ? "chip-warn" : ""}`}>
                    {f.kind}
                  </span>{" "}
                  <b>{f.name}</b>{" "}
                  <span className="muted">
                    · {f.sections} sections · {kb(f.size_bytes)}
                  </span>
                </span>
                {f.kind === "upload" && (
                  <button
                    className="link"
                    onClick={() => onRemove(f.name)}
                    disabled={remove.loading}
                  >
                    remove
                  </button>
                )}
              </div>
            ))
          ) : sources.data ? (
            <p className="muted">No knowledge files found in the corpus directory.</p>
          ) : (
            <p className="muted">Loading files…</p>
          )}
        </div>
        <div className="toolbar" style={{ marginTop: 12 }}>
          <input
            type="file"
            accept=".md,.markdown,.txt"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <button
            className="primary"
            onClick={onUpload}
            disabled={!file || upload.loading}
          >
            {upload.loading ? "Uploading…" : "Upload document"}
          </button>
          <button onClick={refresh} disabled={sources.loading}>
            {sources.loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
        <p className="muted">
          Supported formats: {(sources.data?.formats ?? [".md", ".txt"]).join(", ")}
          {sources.data
            ? ` · max ${(sources.data.max_upload_bytes / 1024).toFixed(0)} KiB`
            : ""}
        </p>
        <Notice error={sources.error || upload.error || remove.error} />
      </Card>
      <Card>
        <label>
          Question
          <input value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        <div className="toolbar" style={{ marginTop: 12 }}>
          <label>
            Model
            <select value={tier} onChange={(e) => setTier(e.target.value as Tier)}>
              {(models.data?.tiers ?? []).map((t) => (
                <option key={t.tier} value={t.tier}>
                  {modelLabel(t)}
                </option>
              ))}
            </select>
          </label>
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
        <Notice error={models.error} />
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
  const [report, setReport] = useState<SavedResult<ScreeningReport> | null>(null);
  const [source, setSource] = useState<"saved" | "live">("saved");
  const [slotLabel, setSlotLabel] = useState("saved example");
  const [realBusy, setRealBusy] = useState(false);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    // Default view comes from a saved file — opening the tab never spends
    // provider budget on a real screening.
    api
      .resultsSaved<ScreeningReport>("recruitment")
      .then((r) => {
        setReport(r);
        setSource("saved");
        setSlotLabel(`saved example ${r._meta?.slot ?? "—"}`);
      })
      .catch(() => setLoadError("No saved screening yet. Use a real run once to capture one."));
  }, []);

  const fakeRun = useCallback((slot: number) => {
    setLoadError("");
    api
      .resultsSaved<ScreeningReport>("recruitment", slot)
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
      const r = await api.screen(jd, resume);
      setReport({ ...r, _meta: undefined });
      setSource("live");
      setSlotLabel("live run");
      // Persist so subsequent fake runs rotate through this measured result.
      await api.resultsSave("recruitment", r).catch(() => undefined);
    } finally {
      setRealBusy(false);
    }
  };

  const r = report;
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
        blurb="Paste a job description and a resume. The model extracts structure; a deterministic rubric scores the match and shows the evidence. Fake runs replay saved screens; real runs measure the live provider."
      />
      <RequestRunControls
        tab="recruitment"
        onFakeRun={fakeRun}
        onRealRun={realRun}
        realBusy={realBusy}
        realLabel="Real run"
        fakeLabel="Fake run"
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
              <Badge tone={source === "live" ? "green" : "blue"}>
                {source === "live" ? "● live" : slotLabel}
              </Badge>
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
      <Notice error={loadError} />
    </div>
  );
}
