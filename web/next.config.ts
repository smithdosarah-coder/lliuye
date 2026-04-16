import type { NextConfig } from "next";

const REPORT_BACKEND =
  process.env.REPORT_BACKEND_URL ?? "http://127.0.0.1:8002";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost", "172.18.17.105"],
  async rewrites() {
    return [
      {
        source: "/api/report/:path*",
        destination: `${REPORT_BACKEND}/api/report/:path*`,
      },
    ];
  },
};

export default nextConfig;
