"use client";

import dynamic from "next/dynamic";

const EarthScene = dynamic(() => import("./EarthScene"), {
  ssr: false,
  loading: () => <div className="login-stage__fallback" aria-hidden />,
});

export function EarthSceneClient() {
  return <EarthScene />;
}
