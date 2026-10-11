import path from "node:path";
import type { NextConfig } from "next";

try {
  // Resolve the repository-level env file from this config instead of relying
  // on the cwd used by pnpm or Playwright.
  process.loadEnvFile(path.resolve(__dirname, "../../.env"));
} catch {
  // The root .env is optional during static checks and CI builds.
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // The parent home directory also contains a pnpm lockfile. Keep Next's
  // tracing/workspace calculations anchored to this repository.
  outputFileTracingRoot: path.resolve(__dirname, "../.."),
  // Keep `next dev` artifacts separate from `next build` artifacts.
  distDir: process.env.GOAG_NEXT_DIST_DIR ?? (process.env.NODE_ENV === "development" ? ".next-dev" : ".next"),
};

export default nextConfig;
