import { test } from "node:test";
import assert from "node:assert/strict";

import { getCustomer, getCustomerDefinition, getCustomerTool } from "./getCustomer.ts";
import { searchDocuments, searchDocumentsDefinition } from "./searchDocuments.ts";
import { validateArgs } from "./validate.ts";

// DoD: two tools exist and work independently.

test("getCustomer returns a known customer with no LLM involved", async () => {
  const result = await getCustomer({ customerId: "C-1001" });
  assert.equal(result.found, true);
  assert.equal(result.found && result.customer.name, "Ada Lovelace");
});

test("getCustomer reports a miss instead of throwing", async () => {
  const result = await getCustomer({ customerId: "C-9999" });
  assert.equal(result.found, false);
  assert.equal(result.found === false && result.id, "C-9999");
});

test("searchDocuments ranks the matching policy first", async () => {
  const { results } = await searchDocuments({ query: "refund policy" });
  assert.equal(results[0]?.id, "refund-001");
  assert.ok(results[0]!.score > 0);
});

test("searchDocuments honours the limit argument", async () => {
  const { results } = await searchDocuments({ query: "payment returns refund", limit: 1 });
  assert.equal(results.length, 1);
});

test("searchDocuments returns an empty list rather than throwing on no match", async () => {
  const { results } = await searchDocuments({ query: "quantum chromodynamics" });
  assert.deepEqual(results, []);
});

// DoD: arguments are validated before execution.

test("validator accepts well-formed arguments", () => {
  const result = validateArgs(getCustomerDefinition.inputSchema, { customerId: "C-1001" });
  assert.equal(result.ok, true);
});

test("validator rejects a missing required argument", () => {
  const result = validateArgs(getCustomerDefinition.inputSchema, {});
  assert.equal(result.ok, false);
  assert.deepEqual(result.ok === false && result.issues, [
    { path: "customerId", message: "is required" },
  ]);
});

test("validator rejects the wrong type", () => {
  const result = validateArgs(getCustomerDefinition.inputSchema, { customerId: 42 });
  assert.equal(result.ok, false);
  assert.ok(result.ok === false && result.issues[0]!.message === "must be a string");
});

test("validator rejects unknown arguments when additionalProperties is false", () => {
  const result = validateArgs(getCustomerDefinition.inputSchema, {
    customerId: "C-1001",
    admin: true,
  });
  assert.equal(result.ok, false);
});

test("validator enforces integer bounds on the search limit", () => {
  assert.equal(validateArgs(searchDocumentsDefinition.inputSchema, { query: "x", limit: 0 }).ok, false);
  assert.equal(validateArgs(searchDocumentsDefinition.inputSchema, { query: "x", limit: 9 }).ok, false);
  assert.equal(validateArgs(searchDocumentsDefinition.inputSchema, { query: "x", limit: 2 }).ok, true);
});

test("validator rejects non-object arguments", () => {
  const result = validateArgs(getCustomerDefinition.inputSchema, "C-1001");
  assert.equal(result.ok, false);
});

// DoD: metadata is exposed separately from implementation.

test("tool definition carries name, description, and a JSON schema only", () => {
  const keys = Object.keys(getCustomerTool.definition).sort();
  assert.deepEqual(keys, ["description", "inputSchema", "name"]);
  assert.equal("execute" in getCustomerTool.definition, false);
});
