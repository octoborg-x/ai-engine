"use client";

import { useEffect, useState } from "react";

type Section = "overview" | "playground" | "models" | "compare" | "tests" | "evals" | "auth" | "rate" | "logs" | "settings";

const nav: { id: Section; label: string; icon: string }[] = [
  { id: "overview", label: "Overview", icon: "⌂" },
  { id: "playground", label: "Playground", icon: "✦" },
  { id: "models", label: "Models", icon: "◈" },
  { id: "compare", label: "Compare", icon: "⇄" },
  { id: "tests", label: "Tests", icon: "✓" },
  { id: "evals", label: "Evals", icon: "▣" },
  { id: "auth", label: "Auth", icon: "⌁" },
  { id: "rate", label: "Rate limits", icon: "◴" },
  { id: "logs", label: "Observability", icon: "≡" },
  { id: "settings", label: "Settings", icon: "⚙" },
];

const models = [
  { name: "Cheap", env: "MODEL_CHEAP", model: "configured free model", tone: "green" },
  { name: "Balanced", env: "MODEL_BALANCED", model: "configured free model", tone: "blue" },
  { name: "Powerful", env: "MODEL_POWERFUL", model: "configured free model", tone: "violet" },
];

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`card ${className}`}>{children}</section>;
}

function Badge({ children, tone = "green" }: { children: React.ReactNode; tone?: string }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

const TOKEN_KEY = "apiToken";

function storedToken(): string {
  if (typeof window === "undefined") return "";
  return (localStorage.getItem(TOKEN_KEY) ?? "").trim();
}

function authHeaders(): Record<string, string> {
  const token = storedToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function Overview({ setSection }: { setSection: (s: Section) => void }) {
  return (
    <>
      <div className="hero">
        <div>
          <p className="eyebrow">WEEK 1 · AI ENGINEERING</p>
          <h1>Backend control plane</h1>
          <p className="muted">One monolith. One repository. One environment. The UI exposes the backend capabilities without moving domain logic into React.</p>
        </div>
        <Badge>● API ready</Badge>
      </div>
      <div className="grid four">
        <Card><p className="label">LLM tiers</p><strong>3</strong><span className="muted">cheap · balanced · powerful</span></Card>
        <Card><p className="label">Streaming</p><strong>✓</strong><span className="muted">SSE-style endpoint</span></Card>
        <Card><p className="label">Security</p><strong>✓</strong><span className="muted">bearer + rate limit</span></Card>
        <Card><p className="label">Telemetry</p><strong>✓</strong><span className="muted">request / trace IDs</span></Card>
      </div>
      <div className="grid two">
        <Card>
          <div className="card-head"><h2>Backend surface</h2><Badge>Connected</Badge></div>
          <div className="rows">
            {["GET /health", "POST /chat", "POST /chat/stream", "POST /extract-ticket"].map(x => <div className="row" key={x}><code>{x}</code><Badge>ready</Badge></div>)}
          </div>
        </Card>
        <Card>
          <div className="card-head"><h2>Quick actions</h2></div>
          <div className="actions">
            <button onClick={() => setSection("playground")}>Try streaming →</button>
            <button onClick={() => setSection("models")}>Inspect models →</button>
            <button onClick={() => setSection("tests")}>View test indices →</button>
            <button onClick={() => setSection("logs")}>Open observability →</button>
          </div>
        </Card>
      </div>
    </>
  );
}

function Playground() {
  const [prompt, setPrompt] = useState("Explain dependency inversion in one paragraph.");
  const [output, setOutput] = useState("");
  const [running, setRunning] = useState(false);
  const [model, setModel] = useState("balanced");
  const [meta, setMeta] = useState("Ready");

  async function run() {
    setRunning(true); setOutput(""); setMeta("Streaming…");
    const started = performance.now();
    try {
      const res = await fetch("/api/backend/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ prompt }),
      });
      if (res.status === 401) {
        throw new Error("401 Unauthorized — open the Auth tab and save an API token, then retry.");
      }
      if (!res.ok || !res.body) throw new Error(`Request failed: ${res.status}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let text = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        text += decoder.decode(value, { stream: true });
        setOutput(text);
      }
      setMeta(`Completed · ${Math.round(performance.now() - started)} ms · route selected by backend`);
    } catch (e) {
      setMeta(e instanceof Error ? e.message : "Request failed");
    } finally { setRunning(false); }
  }

  return <div className="stack">
    <div className="hero"><div><p className="eyebrow">PLAYGROUND</p><h1>Streaming chat</h1><p className="muted">Thin UI over <code>/chat/stream</code>. Routing remains a backend concern.</p></div><Badge tone={running ? "blue" : "green"}>{running ? "● streaming" : "● idle"}</Badge></div>
    <Card>
      <div className="toolbar"><label>Model tier<select value={model} onChange={e => setModel(e.target.value)}><option value="cheap">Cheap</option><option value="balanced">Balanced</option><option value="powerful">Powerful</option></select></label><span className="muted">Selected tier is currently informational; backend routing remains authoritative.</span></div>
      <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={5} />
      <div className="toolbar"><button className="primary" onClick={run} disabled={running || !prompt.trim()}>{running ? "Streaming…" : "Send"}</button><span className="muted">{meta}</span></div>
      <div className="response"><div className="label">Response</div><p>{output || "Your streamed response will appear here."}</p></div>
    </Card>
  </div>;
}

function Models() {
  return <div className="stack"><div className="hero"><div><p className="eyebrow">MODEL ROUTING</p><h1>Providers & tiers</h1><p className="muted">Three environment-configured free-model tiers, plus a safe placeholder for an OpenAI-compatible custom provider.</p></div></div>
    <div className="grid three">{models.map(m => <Card key={m.name}><Badge tone={m.tone}>{m.name}</Badge><h2>{m.model}</h2><p className="muted"><code>{m.env}</code></p><div className="row"><span>Streaming</span><Badge>yes</Badge></div><div className="row"><span>Cost</span><span>$0 configured</span></div></Card>)}</div>
    <Card><div className="card-head"><h2>Custom OpenAI-compatible provider</h2><Badge tone="amber">credentials stay server-side</Badge></div><div className="grid three"><label>Base URL<input placeholder="https://api.openai.com/v1" /></label><label>Model<input placeholder="gpt-4.1-mini" /></label><label>API key<input type="password" placeholder="••••••••••••" /></label></div><p className="muted">This Week 1 console reserves the UX. Do not persist provider keys in browser storage; wire this form to a server-side secrets boundary before enabling it.</p><button>Test connection</button></Card>
  </div>;
}

function Compare() {
  return <div className="stack"><div className="hero"><div><p className="eyebrow">BENCHMARKS</p><h1>Model comparison</h1><p className="muted">A backend-fed view for latency, tokens, cost and pass-rate comparisons.</p></div><button className="primary">Run comparison</button></div>
    <Card><div className="table-wrap"><table><thead><tr><th>Metric</th><th>Cheap</th><th>Balanced</th><th>Powerful</th></tr></thead><tbody>{[["Pass rate","—","—","—"],["Avg latency","—","—","—"],["P95 latency","—","—","—"],["Avg tokens","—","—","—"],["Cost / run","$0*","$0*","$0*"]].map(r=><tr key={r[0]}>{r.map((x,i)=><td key={i}>{x}</td>)}</tr>)}</tbody></table></div><p className="footnote">* Values are intentionally backend-fed placeholders until a comparison endpoint is exposed. The frontend does not invent benchmark results.</p></Card>
  </div>;
}

function Tests() {
  const suites = [["Chat API","40 cases","—"],["Structured output","30 cases","—"],["Streaming","10 cases","—"],["Error handling","20 cases","—"]];
  return <div className="stack"><div className="hero"><div><p className="eyebrow">ENGINEERING TESTS</p><h1>Test indices</h1><p className="muted">Storybook-like navigation for backend test suites without reproducing the test implementation in the UI.</p></div></div><div className="grid two">{suites.map(s=><Card key={s[0]}><div className="card-head"><h2>{s[0]}</h2><Badge>ready</Badge></div><strong>{s[1]}</strong><div className="metric-line"><span>Pass rate</span><span>{s[2]}</span></div><div className="metric-line"><span>Technical failures</span><span>—</span></div><button>Open indices →</button></Card>)}</div></div>;
}

function Evals() {
  return <div className="stack"><div className="hero"><div><p className="eyebrow">QUALITY</p><h1>Evaluation cases</h1><p className="muted">Index and run evaluation datasets; detailed scoring stays in the backend/eval layer.</p></div><button className="primary">Run evaluation</button></div><Card><div className="rows">{["chat_cases.json","classification_cases.json","extraction_cases.json","adversarial_cases.json"].map((x,i)=><div className="row" key={x}><code>{x}</code><span className="muted">{i === 0 ? "chat quality" : "dataset"}</span><Badge>indexed</Badge></div>)}</div></Card></div>;
}

function Auth() {
  const [token,setToken]=useState("");
  const [saved,setSaved]=useState(false);
  useEffect(()=>{ const t=storedToken(); if(t){ setToken(t); setSaved(true); } },[]);
  function save(){
    const t=token.trim();
    if(t){ localStorage.setItem(TOKEN_KEY,t); } else { localStorage.removeItem(TOKEN_KEY); }
    setToken(t); setSaved(Boolean(t));
  }
  return <div className="stack"><div className="hero"><div><p className="eyebrow">SECURITY</p><h1>Authentication</h1><p className="muted">Bearer-token authentication is enforced by the FastAPI middleware for chat.</p></div><Badge tone={saved ? "green" : "amber"}>{saved ? "token saved" : "no token"}</Badge></div><Card><div className="grid two"><label>API token<input type="password" value={token} onChange={e=>{setToken(e.target.value); setSaved(false);}} placeholder="Paste the API_AUTH_TOKEN value" /></label><div><p className="label">Session state</p><strong>{saved ? "Saved for this browser" : token ? "Not saved yet" : "No token configured"}</strong><p className="muted">The Playground sends this as a Bearer token on every request. It is stored in this browser&apos;s local storage.</p></div></div><button onClick={save}>Save token for API calls</button></Card></div>;
}

function Rate() {
  return <div className="stack"><div className="hero"><div><p className="eyebrow">PROTECTION</p><h1>Rate limits</h1><p className="muted">The current backend uses a process-local fixed window. Default configuration is 10 requests / 60 seconds.</p></div><Badge>10 / 60s</Badge></div><Card><div className="rate"><div><span className="label">Current window</span><strong>10 requests</strong></div><div className="meter"><span style={{width:"20%"}} /></div><div className="row"><span>Remaining</span><span>Backend response header</span></div><div className="row"><span>429 behavior</span><Badge tone="amber">Retry-After</Badge></div></div></Card></div>;
}

function Logs() {
  return <div className="stack"><div className="hero"><div><p className="eyebrow">OBSERVABILITY</p><h1>Request logs</h1><p className="muted">UI for the structured JSON events already emitted by the backend. No prompt contents are displayed.</p></div><Badge>trace-ready</Badge></div><Card><div className="log"><div><b>INFO</b> request.start <span>request_id=req_…</span></div><div><b>INFO</b> llm.call <span>model=… latency_ms=… tokens=…</span></div><div><b>INFO</b> request.end <span>status=success trace_id=trace_…</span></div><div><b>WARN</b> llm.retry <span>attempt=2 error_type=…</span></div></div><p className="footnote">The backend currently writes structured logs to stdout. A queryable log endpoint can be added when persistence/aggregation is introduced.</p></Card></div>;
}

function Settings() {
  return <div className="stack"><div className="hero"><div><p className="eyebrow">CONFIGURATION</p><h1>Settings</h1><p className="muted">Monolith environment boundaries.</p></div></div><Card><div className="rows">{[["Backend proxy","/api/backend/*"],["Backend origin","BACKEND_URL"],["Model configuration","MODEL_CHEAP / BALANCED / POWERFUL"],["Rate limit","RATE_LIMIT_REQUESTS / RATE_LIMIT_WINDOW_SECONDS"],["Auth","API_AUTH_TOKEN"]].map(x=><div className="row" key={x[0]}><span>{x[0]}</span><code>{x[1]}</code></div>)}</div></Card></div>;
}

export default function Home() {
  const [section,setSection]=useState<Section>("overview");
  const current=nav.find(x=>x.id===section)!;
  const content = section==="overview" ? <Overview setSection={setSection}/> :
    section==="playground" ? <Playground/> :
    section==="models" ? <Models/> :
    section==="compare" ? <Compare/> :
    section==="tests" ? <Tests/> :
    section==="evals" ? <Evals/> :
    section==="auth" ? <Auth/> :
    section==="rate" ? <Rate/> :
    section==="logs" ? <Logs/> : <Settings/>;

  return <main className="shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark">AI</div><div><b>Engineering</b><span>Console</span></div></div><nav>{nav.map(item=><button key={item.id} className={section===item.id ? "active" : ""} onClick={()=>setSection(item.id)}><span>{item.icon}</span>{item.label}</button>)}</nav><div className="side-foot"><span className="dot"/> monolith / week 1</div></aside>
    <section className="main"><header><span>{current.icon} {current.label}</span><span className="muted">ai-api-project · main target</span></header><div className="content">{content}</div></section>
  </main>;
}
