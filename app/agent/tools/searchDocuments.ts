import type { Tool, ToolArgs } from "./types.ts";

/**
 * searchDocuments - a deterministic keyword search tool.
 *
 * Stands in for the Week 2 retrieval pipeline: it scores a small in-memory
 * knowledge base with a naive term-overlap metric. Deterministic by design so
 * the tool loop is reproducible in tests without embeddings or a vector store.
 */

export type DocumentHit = {
  id: string;
  source: string;
  section: string;
  score: number;
  snippet: string;
};

const DOCUMENTS = [
  {
    id: "refund-001",
    source: "refund-policy.pdf",
    section: "Returns",
    text: "Refunds are allowed within 30 days of purchase.",
  },
  {
    id: "returns-001",
    source: "returns.pdf",
    section: "Damaged Goods",
    text: "Damaged products can be returned if reported within 48 hours.",
  },
  {
    id: "payment-001",
    source: "errors.pdf",
    section: "Payment Errors",
    text: "Error code ERR_PAYMENT_403 indicates a forbidden transaction.",
  },
  {
    id: "shipping-001",
    source: "shipping_policy.md",
    section: "Processing Orders",
    text: "Standard delivery typically takes 3-5 business days after processing.",
  },
  {
    id: "account-001",
    source: "account.md",
    section: "Suspension",
    text: "Accounts are suspended after repeated failed payment attempts.",
  },
];

export const searchDocumentsDefinition = {
  name: "searchDocuments",
  description:
    "Search the support knowledge base for documents matching a query. " +
    "Returns the best matching passages with source and relevance score.",
  inputSchema: {
    type: "object",
    properties: {
      query: {
        type: "string",
        minLength: 1,
        description: "Natural language search query.",
      },
      limit: {
        type: "integer",
        minimum: 1,
        maximum: 5,
        description: "Maximum number of documents to return. Defaults to 3.",
      },
    },
    required: ["query"],
    additionalProperties: false,
  },
} as const;

export async function searchDocuments(rawArgs: unknown): Promise<{ results: DocumentHit[] }> {
  // The registry has already validated against inputSchema; the public
  // signature stays `unknown` to match Tool.execute.
  const args = rawArgs as ToolArgs;
  const query = String(args.query);
  const limit = args.limit === undefined ? 3 : Number(args.limit);
  const terms = tokenize(query);

  const results = DOCUMENTS.map((doc) => {
    const haystack = tokenize(`${doc.section} ${doc.text}`);
    // Prefix match so "refund" matches "refunds" without a stemmer.
    const score = terms.filter((term) =>
      haystack.some((token) => token.startsWith(term)),
    ).length;
    return { ...doc, score };
  })
    .filter((doc) => doc.score > 0)
    .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id))
    .slice(0, limit)
    .map(({ id, source, section, score, text }) => ({
      id,
      source,
      section,
      score,
      snippet: text,
    }));

  return { results };
}

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[^a-z0-9_]+/)
    .filter((token) => token.length > 2);
}

export const searchDocumentsTool: Tool = {
  definition: searchDocumentsDefinition,
  execute: searchDocuments,
};
