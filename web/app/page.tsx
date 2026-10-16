"use client";

import { useState } from "react";
import { nav, type Section } from "./components/ui";
import { Models, Overview, Playground } from "./components/panels-core";
import { Compare, Evals, Quality } from "./components/panels-quality";
import { Knowledge, Recruitment } from "./components/panels-use-cases";
import { Auth, Logs, Rate, Settings } from "./components/panels-ops";

function render(section: Section, setSection: (s: Section) => void) {
  switch (section) {
    case "overview":
      return <Overview setSection={setSection} />;
    case "playground":
      return <Playground />;
    case "models":
      return <Models />;
    case "compare":
      return <Compare />;
    case "quality":
      return <Quality setSection={setSection} />;
    case "evals":
      return <Evals />;
    case "knowledge":
      return <Knowledge />;
    case "recruitment":
      return <Recruitment />;
    case "auth":
      return <Auth />;
    case "rate":
      return <Rate />;
    case "logs":
      return <Logs />;
    default:
      return <Settings />;
  }
}

export default function Home() {
  const [section, setSection] = useState<Section>("overview");
  const current = nav.find((x) => x.id === section)!;

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">AI</div>
          <div>
            <b>Engineering</b>
            <span>Console</span>
          </div>
        </div>
        <nav>
          {nav.map((item) => (
            <button
              key={item.id}
              className={section === item.id ? "active" : ""}
              onClick={() => setSection(item.id)}
            >
              <span>{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>
        <div className="side-foot">
          <span className="dot" /> backend-connected console
        </div>
      </aside>
      <section className="main">
        <header>
          <span>
            {current.icon} {current.label}
          </span>
          <span className="muted">ai-engine · live backend</span>
        </header>
        <div className="content">{render(section, setSection)}</div>
      </section>
    </main>
  );
}
