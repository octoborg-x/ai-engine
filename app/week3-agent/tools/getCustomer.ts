import type { Tool, ToolArgs } from "./types.ts";

/**
 * getCustomer - a deterministic lookup tool.
 *
 * No LLM and no network: given a customer ID it returns the stored record.
 * This is the "authorized side effect" half of the loop, kept trivially
 * testable so the agent mechanics are what gets exercised.
 */

export type Customer = {
  id: string;
  name: string;
  email: string;
  plan: "free" | "pro" | "enterprise";
  status: "active" | "suspended" | "cancelled";
  since: string;
};

const CUSTOMERS: Record<string, Customer> = {
  "C-1001": {
    id: "C-1001",
    name: "Ada Lovelace",
    email: "ada@example.com",
    plan: "enterprise",
    status: "active",
    since: "2023-04-12",
  },
  "C-1002": {
    id: "C-1002",
    name: "Grace Hopper",
    email: "grace@example.com",
    plan: "pro",
    status: "active",
    since: "2024-01-09",
  },
  "C-1003": {
    id: "C-1003",
    name: "Alan Turing",
    email: "alan@example.com",
    plan: "free",
    status: "suspended",
    since: "2024-07-30",
  },
};

export const getCustomerDefinition = {
  name: "getCustomer",
  description:
    "Look up a customer record by ID. Returns name, email, plan, status, " +
    "and the date the account was opened.",
  inputSchema: {
    type: "object",
    properties: {
      customerId: {
        type: "string",
        minLength: 1,
        description: "Customer identifier, for example C-1001.",
      },
    },
    required: ["customerId"],
    additionalProperties: false,
  },
} as const;

export type CustomerLookup =
  | { found: true; customer: Customer }
  | { found: false; id: string; reason: string };

export async function getCustomer(rawArgs: unknown): Promise<CustomerLookup> {
  // The registry has already validated against inputSchema; the public
  // signature stays `unknown` to match Tool.execute.
  const customerId = String((rawArgs as ToolArgs).customerId);
  const customer = CUSTOMERS[customerId];

  if (!customer) {
    // A thrown error here would abort the loop. Return a structured miss so
    // the model can observe the failure and choose a different action.
    return { found: false, id: customerId, reason: "no customer with that id" };
  }

  return { found: true, customer };
}

export const getCustomerTool: Tool = {
  definition: getCustomerDefinition,
  execute: getCustomer,
};
