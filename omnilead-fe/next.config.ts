import type { NextConfig } from "next";

const frontendOrigin = process.env.OMNILEAD_FRONTEND_URL;

const nextConfig: NextConfig = {
  /* config options here */
  allowedDevOrigins: frontendOrigin ? [new URL(frontendOrigin).hostname] : [],
  experimental: {
    agentFeedback: true,
    // Account-gated pages fetch their session before rendering their children.
    instantInsights: { validationLevel: "manual-warning" },
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
