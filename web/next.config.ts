import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Docker runtime runs the emitted standalone server (see Dockerfile.web).
  output: "standalone",
  // No optimised images are used anywhere; avoids sharp machinery in the image.
  images: { unoptimized: true },
};

export default nextConfig;
