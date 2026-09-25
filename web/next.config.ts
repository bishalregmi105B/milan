import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Exposed to client bundles so admin pages share the exact base URL the
  // server-side code uses. Defaults to the production API — never a
  // localhost fallback (master plan §7.6).
  env: {
    MILAN_API_BASE_URL:
      process.env.MILAN_API_BASE_URL ?? "https://milanapi.pukarphulara.com.np/api/v1",
  },
};

export default nextConfig;
