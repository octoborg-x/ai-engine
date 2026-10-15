import type { ToolArgs } from "./types.ts";

export type ValidationIssue = { path: string; message: string };

/**
 * Minimal JSON Schema validator for the subset the tools actually declare:
 * object schemas with typed properties, required keys, enums, integer and
 * numeric bounds.
 *
 * It returns a list of issues rather than throwing so the caller can decide
 * whether a failure is fatal or should be fed back to the model.
 */
export function validateArgs(
  schema: object,
  args: unknown,
): { ok: true; value: ToolArgs } | { ok: false; issues: ValidationIssue[] } {
  const issues: ValidationIssue[] = [];

  if (!isPlainObject(args)) {
    return {
      ok: false,
      issues: [{ path: "$", message: "must be a JSON object" }],
    };
  }

  const spec = schema as Record<string, unknown>;
  const properties = (spec.properties ?? {}) as Record<string, JsonShape>;
  const required = new Set(
    Array.isArray(spec.required) ? (spec.required as string[]) : [],
  );

  for (const key of required) {
    if (!(key in args)) {
      issues.push({ path: key, message: "is required" });
    }
  }

  if (spec.additionalProperties === false) {
    for (const key of Object.keys(args)) {
      if (!(key in properties)) {
        issues.push({ path: key, message: "is not an allowed argument" });
      }
    }
  }

  for (const [key, shape] of Object.entries(properties)) {
    if (!(key in args)) continue;
    issues.push(...validateValue(key, args[key], shape));
  }

  if (issues.length > 0) return { ok: false, issues };
  return { ok: true, value: args as ToolArgs };
}

type JsonShape = {
  type?: string;
  enum?: unknown[];
  minimum?: number;
  maximum?: number;
  minLength?: number;
  description?: string;
};

function validateValue(path: string, value: unknown, shape: JsonShape): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  if (shape.type === "string") {
    if (typeof value !== "string") {
      return [{ path, message: "must be a string" }];
    }
    if (shape.minLength !== undefined && value.length < shape.minLength) {
      issues.push({ path, message: `must be at least ${shape.minLength} characters` });
    }
  } else if (shape.type === "integer" || shape.type === "number") {
    if (typeof value !== "number" || Number.isNaN(value)) {
      return [{ path, message: "must be a number" }];
    }
    if (shape.type === "integer" && !Number.isInteger(value)) {
      issues.push({ path, message: "must be an integer" });
    }
  }

  if (shape.enum && !shape.enum.includes(value)) {
    issues.push({
      path,
      message: `must be one of ${shape.enum.map((v) => JSON.stringify(v)).join(", ")}`,
    });
  }

  if (typeof value === "number") {
    if (shape.minimum !== undefined && value < shape.minimum) {
      issues.push({ path, message: `must be >= ${shape.minimum}` });
    }
    if (shape.maximum !== undefined && value > shape.maximum) {
      issues.push({ path, message: `must be <= ${shape.maximum}` });
    }
  }

  return issues;
}

function isPlainObject(value: unknown): value is ToolArgs {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
