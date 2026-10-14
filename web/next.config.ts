import type { NextConfig } from "next";

// In production Docker builds this is set at image build time via the
// BACKEND_URL build arg (defaults to the backend container on the Docker
// network). Locally it falls back to localhost:8000.
const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/api/backend/:path*", destination: `${backendUrl}/:path*` },
    ];
  },
};

export default nextConfig;
