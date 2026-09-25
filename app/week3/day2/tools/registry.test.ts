import { test } from "node:test";
import assert from "node:assert/strict";

import { ToolNotFoundError, ToolValidationError } from "./errors.ts";
import { createDefaultRegistry, ToolRegistry } from "./registry.ts";
import type { Tool } from "./types.ts";

const echoTool: Tool = {
  definition: {
    name: "echo",
    description: "Echo the input back.",
    inputSchema: {
      type: "object",
      properties: { value: { type: "string" } },
      required: ["value"],
      additionalProperties: false,
    },
  },
  execute: async (args) => ({ echoed: (args as { value: string }).value }),
};

test("registry exposes metadata separately from implementation", () => {
  const registry = createDefaultRegistry();
  const definitions = registry.definitions();

  assert.deepEqual(
    definitions.map((definition) => definition.name).sort(),
    ["getCustomer", "searchDocuments"],
  );
  for (const definition of definitions) {
    assert.equal(typeof definition.description, "string");
    assert.equal(typeof definition.inputSchema, "object");
    assert.equal("execute" in definition, false);
  }
});

test("openAiTools wraps each definition in the provider function envelope", () => {
  const [first] = createDefaultRegistry().openAiTools();
  assert.ok(first);
  assert.equal(first.type, "function");
  assert.ok(first.function.parameters);
  assert.equal("execute" in first.function, false);
});

test("registering a duplicate name fails fast", () => {
  const registry = new ToolRegistry().register(echoTool);
  assert.throws(() => registry.register(echoTool), /already registered/);
});

test("executeTool validates before running the implementation", async () => {
  let ran = false;
  const spy: Tool = {
    definition: echoTool.definition,
    execute: async () => {
      ran = true;
      return "should not happen";
    },
  };

  const registry = new ToolRegistry().register(spy);
  await assert.rejects(
    () => registry.executeTool("echo", {}),
    (error: unknown) => error instanceof ToolValidationError,
  );
  assert.equal(ran, false, "tool ran despite invalid arguments");
});

test("executeTool rejects malformed JSON arguments as a validation error", async () => {
  const registry = new ToolRegistry().register(echoTool);
  await assert.rejects(
    () => registry.executeTool("echo", "{not json"),
    (error: unknown) => error instanceof ToolValidationError,
  );
});

test("executeTool accepts JSON-string arguments like a provider sends", async () => {
  const registry = new ToolRegistry().register(echoTool);
  const result = await registry.executeTool("echo", '{"value":"hi"}');
  assert.deepEqual(result, { echoed: "hi" });
});

test("executeTool raises ToolNotFoundError for an unregistered name", async () => {
  const registry = new ToolRegistry();
  await assert.rejects(
    () => registry.executeTool("nope", {}),
    (error: unknown) => error instanceof ToolNotFoundError,
  );
});
