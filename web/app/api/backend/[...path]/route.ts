import { NextRequest } from "next/server";

// Server-side proxy for the backend API. The browser calls /api/backend/*, and
// this handler attaches the shared API token before forwarding upstream. The
// token is read from the server environment at request time, so it is never
// included in the client bundle or exposed to any user.
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const backendUrl = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/+$/, "");

// Request headers that must not be copied upstream: the token is injected
// server-side, and the rest describe the hop to this proxy rather than the
// backend origin.
const STRIPPED_REQUEST_HEADERS = new Set([
  "authorization",
  "host",
  "connection",
  "content-length",
  "accept-encoding",
]);

// Response headers that describe the proxied hop and must not be forwarded.
const STRIPPED_RESPONSE_HEADERS = new Set([
  "content-encoding",
  "content-length",
  "transfer-encoding",
  "connection",
  "keep-alive",
]);

async function proxy(request: NextRequest, path: string[]): Promise<Response> {
  const token = process.env.API_AUTH_TOKEN;
  if (!token) {
    return Response.json(
      { detail: "Server is missing API_AUTH_TOKEN; chat is unavailable." },
      { status: 503 },
    );
  }

  const target = new URL(`${backendUrl}/${path.join("/")}`);
  target.search = request.nextUrl.search;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!STRIPPED_REQUEST_HEADERS.has(key.toLowerCase())) headers.set(key, value);
  });
  headers.set("Authorization", `Bearer ${token}`);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const upstream = await fetch(target, {
    method: request.method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    redirect: "manual",
    cache: "no-store",
  });

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!STRIPPED_RESPONSE_HEADERS.has(key.toLowerCase())) responseHeaders.append(key, value);
  });

  // Pass the upstream body through untouched so SSE streams incrementally.
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, ctx: RouteContext) {
  return proxy(request, (await ctx.params).path);
}

export async function POST(request: NextRequest, ctx: RouteContext) {
  return proxy(request, (await ctx.params).path);
}

export async function PUT(request: NextRequest, ctx: RouteContext) {
  return proxy(request, (await ctx.params).path);
}

export async function PATCH(request: NextRequest, ctx: RouteContext) {
  return proxy(request, (await ctx.params).path);
}

export async function DELETE(request: NextRequest, ctx: RouteContext) {
  return proxy(request, (await ctx.params).path);
}
