import type { ToolArgs } from "./types.ts";
import type { ValidationIssue } from "./validate.ts";

/** The model asked for a tool that is not registered. */
export class ToolNotFoundError extends Error {
  readonly toolName: string;

  constructor(toolName: string) {
    super(`Unknown tool "${toolName}"`);
    this.name = "ToolNotFoundError";
    this.toolName = toolName;
  }
}

/** Arguments failed schema validation; the tool was never executed. */
export class ToolValidationError extends Error {
  readonly toolName: string;
  readonly issues: ValidationIssue[];

  constructor(toolName: string, issues: ValidationIssue[]) {
    super(
      `Invalid arguments for "${toolName}": ${issues
        .map((issue) => `${issue.path} ${issue.message}`)
        .join("; ")}`,
    );
    this.name = "ToolValidationError";
    this.toolName = toolName;
    this.issues = issues;
  }
}

/** The tool ran but failed while producing its result. */
export class ToolExecutionError extends Error {
  readonly toolName: string;

  constructor(toolName: string, cause: unknown) {
    const detail = cause instanceof Error ? cause.message : String(cause);
    super(`Tool "${toolName}" failed: ${detail}`);
    this.name = "ToolExecutionError";
    this.toolName = toolName;
  }
}

export type { ToolArgs, ValidationIssue };
