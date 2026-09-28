import { readFileSync } from "fs";
import { resolve } from "path";

export function loadDashboardData() {
  const summary = JSON.parse(readFileSync(resolve("eval/results/summary.json"), "utf-8"));
  const baseline = JSON.parse(readFileSync(resolve("eval/baseline.json"), "utf-8"));
  return { summary, baseline };
}

export function getRegressionStatus(summary: any) {
  const comparisons = summary.baseline_comparison || {};
  const status: Record<string, any> = {};
  for (const [key, comp] of Object.entries(comparisons) as [string, any][]) {
    status[key] = { value: comp.value, threshold: comp.threshold, op: comp.op, pass: comp.status === "PASS" };
  }
  const allPass = Object.values(status).every((s: any) => s.pass);
  return { status, overall: allPass ? "PASS" : "FAIL" };
}
