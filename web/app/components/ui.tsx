"use client";

import { useCallback, useState } from "react";

export type Section =
  | "overview"
  | "playground"
  | "models"
  | "compare"
  | "quality"
  | "evals"
  | "knowledge"
  | "recruitment"
  | "auth"
  | "rate"
  | "logs"
  | "settings";

export const nav: { id: Section; label: string; icon: string }[] = [
  { id: "overview", label: "Overview", icon: "⌂" },
  { id: "playground", label: "Playground", icon: "✦" },
  { id: "models", label: "Models", icon: "◈" },
  { id: "compare", label: "Compare", icon: "⇄" },
  { id: "quality", label: "Quality suites", icon: "✓" },
  { id: "evals", label: "Evals", icon: "▣" },
  { id: "knowledge", label: "Knowledge", icon: "◎" },
  { id: "recruitment", label: "Recruitment", icon: "▤" },
  { id: "auth", label: "Auth", icon: "⌁" },
  { id: "rate", label: "Rate limits", icon: "◴" },
  { id: "logs", label: "Observability", icon: "≡" },
  { id: "settings", label: "Settings", icon: "⚙" },
];

export const pct = (x: number | null | undefined) =>
  x == null ? "—" : `${(x * 100).toFixed(0)}%`;
export const ms = (x: number | null | undefined) =>
  x == null ? "—" : `${Math.round(x)} ms`;
export const usd = (x: number | null | undefined) =>
  x == null ? "—" : x === 0 ? "$0" : `$${x.toFixed(6)}`;
export const num = (x: number | null | undefined) =>
  x == null ? "—" : x.toLocaleString();

export function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <section className={`card ${className}`}>{children}</section>;
}

export function Badge({
  children,
  tone = "green",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function Hero({
  eyebrow,
  title,
  blurb,
  right,
}: {
  eyebrow: string;
  title: string;
  blurb: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="hero">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="muted">{blurb}</p>
      </div>
      {right}
    </div>
  );
}

export function Notice({ error }: { error: string }) {
  if (!error) return null;
  return <p className="notice">{error}</p>;
}

export function Bar({ value, tone = "green" }: { value: number; tone?: string }) {
  const width = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="meter">
      <span className={`bar-${tone}`} style={{ width: `${width}%` }} />
    </div>
  );
}

// Small async-state hook shared by every panel: loading flag, error string,
// and the resolved data. Callers pass a thunk so retries are trivial.
// A failed run keeps any previously loaded data, so a transient 429 from the
// shared rate limiter never blanks an already-rendered panel.
export function useAsync<T>() {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const run = useCallback(async (fn: () => Promise<T>) => {
    setLoading(true);
    setError("");
    try {
      setData(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);
  return { data, error, loading, run };
}

// Rate-limit-aware thunk: retries a shared protected endpoint over the span of
// the fixed-rate-limit window (60s) when the backend returns 429, so a panel
// auto-load recovers after the window resets instead of showing a permanent
// "Loading…". Cumulative delays reach 60s, the default rate-limit window, so
// the final attempt runs just as the budget resets.
const RETRY_DELAYS_MS = [3000, 6000, 9000, 12000, 15000, 15000]; // cumulative 60s

export function withRateLimitRetry<T>(fn: () => Promise<T>, attempts = RETRY_DELAYS_MS.length): () => Promise<T> {
  const attempt = (remaining: number): Promise<T> =>
    fn().catch((e) => {
      const limited =
        e instanceof Error &&
        (e.message.includes("429") || e.message.includes("Rate limit exceeded"));
      if (!limited || remaining <= 1) throw e;
      const delay = RETRY_DELAYS_MS[RETRY_DELAYS_MS.length - remaining] ?? RETRY_DELAYS_MS.at(-1)!;
      return new Promise((resolve, reject) =>
        setTimeout(() => attempt(remaining - 1).then(resolve, reject), delay),
      );
    });
  return () => attempt(attempts);
}
