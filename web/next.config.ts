import type { NextConfig } from "next";

// The backend proxy lives in app/api/backend/[...path]/route.ts, which injects
// the server-side API token at request time. No rewrites are used here so the
// token never reaches the browser.
const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
