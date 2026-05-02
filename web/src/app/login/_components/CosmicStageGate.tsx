"use client";

/**
 * CosmicStageGate · 黑洞场景 dynamic import 包装
 *
 * R3F + Three.js 依赖浏览器 WebGL，必须走 { ssr: false }。
 * ssr:false 只能在 Client Component 里用（Next 16 约束），所以这个壳标 "use client"。
 */

import dynamic from "next/dynamic";

const CosmicStageR3F = dynamic(
  () =>
    import("./CosmicStageR3F").then((mod) => ({ default: mod.CosmicStageR3F })),
  {
    ssr: false,
    loading: () => <div className="cosmic" aria-hidden />,
  },
);

export function CosmicStageGate() {
  return <CosmicStageR3F />;
}
