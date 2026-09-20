import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output keeps the production Docker image small (just the
  // traced server + deps, not the full node_modules tree) — see Dockerfile.
  output: "standalone",
  // The image-optimization endpoint (/_next/image) is not used -- brand assets are plain <img> and customer
  // images come from IntraForge's own authorized download endpoint -- and it has carried critical advisories
  // (GHSA-2xp9-vwfh-vxw4). Turning it off removes the endpoint and the native image library behind it.
  images: { unoptimized: true },
};

export default nextConfig;
