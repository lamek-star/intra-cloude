import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output keeps the production Docker image small (just the
  // traced server + deps, not the full node_modules tree) — see Dockerfile.
  output: "standalone",
};

export default nextConfig;
