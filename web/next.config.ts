import type { NextConfig } from "next";

const REPORT_BACKEND =
  process.env.REPORT_BACKEND_URL ?? "http://127.0.0.1:8002";

// W-D1F-A2 · 2026-04-28 · auth backend (auth_service · D.1 backend `bd143b5` MERGED)
// 默认端口 8000 (api_server.py 主入口) · 可通过 AUTH_BACKEND_URL 覆盖
const AUTH_BACKEND =
  process.env.AUTH_BACKEND_URL ?? "http://127.0.0.1:8000";

const LEGACY_AGENT_ROUTES = [
  "credit",
  "channel",
  "alert",
  "compliance",
  "report",
  "riskctrl",
] as const;

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost", "172.18.17.105"],
  async rewrites() {
    return [
      {
        source: "/api/report/:path*",
        destination: `${REPORT_BACKEND}/api/report/:path*`,
      },
      // Proxy auth endpoints to backend (same-origin · cookie httpOnly 浏览器接管)
      {
        source: "/api/auth/:path*",
        destination: `${AUTH_BACKEND}/api/auth/:path*`,
      },
    ];
  },
  async redirects() {
    return LEGACY_AGENT_ROUTES.map((agent) => ({
      source: `/${agent}`,
      destination: `/archive/${agent}`,
      permanent: false,
    }));
  },
};

export default nextConfig;
