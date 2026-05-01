"use client";

/**
 * CosmicStageGate · 黑洞场景 dynamic import 包装
 *
 * R3F + Three.js 依赖浏览器 WebGL，必须走 { ssr: false }。
 * ssr:false 只能在 Client Component 里用（Next 16 约束），所以这个壳标 "use client"。
 *
 * F4 v2 iter 3 (2026-05-01) · PM brief #5 性能 + 移动端 fallback:
 * - prefers-reduced-motion (用户系统设置) → CSS 静态背景 · 不 mount Canvas
 * - 窄屏 (innerWidth < 768) → 同 fallback (移动端 GPU 不一定支持 raymarching)
 * - 仅 desktop + 非 reduced-motion 才 render R3F Canvas
 * - 检测在 useEffect 内 (避免 SSR mismatch · 默认先 fallback · mount 后 upgrade)
 */

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

const CosmicStageR3F = dynamic(
  () =>
    import("./CosmicStageR3F").then((mod) => ({ default: mod.CosmicStageR3F })),
  {
    ssr: false,
    loading: () => <div className="cosmic" aria-hidden />,
  },
);

/** F4 v2 iter 3 · 静态 CSS fallback (移动端 / reduced-motion) · 不依赖 R3F/three.js */
function CosmicStaticFallback() {
  return (
    <div className="cosmic cosmic--fallback" aria-hidden>
      <div className="cosmic__fallback-disk" />
      <div className="cosmic__fallback-vignette" />
    </div>
  );
}

export function CosmicStageGate() {
  // 默认走 fallback (SSR + 第一帧) · client mount 后 detect upgrade 到 R3F
  const [canRender3D, setCanRender3D] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const mqlReduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    const isMobile = window.innerWidth < 768;

    const decide = () => {
      // 仅 desktop + 非 reduced-motion 才 render R3F Canvas
      setCanRender3D(!mqlReduce.matches && !isMobile);
    };
    decide();

    // reduced-motion 实时 toggle (用户改系统设置不需刷新)
    mqlReduce.addEventListener("change", decide);
    return () => mqlReduce.removeEventListener("change", decide);
  }, []);

  return canRender3D ? <CosmicStageR3F /> : <CosmicStaticFallback />;
}
