"use client";

import { MeshGradient, Waves } from "@paper-design/shaders-react";

/**
 * AtmosphericBg —— 用 WebGL shader 做无色带的海雾氛围底。
 * 三层：MeshGradient（整页深海蓝有机流动）+ Waves（水面波纹）+ 上光柔化层。
 */
export default function AtmosphericBg() {
  return (
    <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
      {/* 基底：无色带 mesh gradient —— 有机流动的深海蓝 */}
      <MeshGradient
        style={{ position: "absolute", inset: 0 }}
        colors={[
          "#0a1220",
          "#1a2e4a",
          "#27415f",
          "#0e1a2a",
          "#142a44",
        ]}
        speed={0.15}
        distortion={0.75}
        swirl={0.35}
        offsetX={0}
        offsetY={0}
        scale={1.1}
      />

      {/* 水面波纹层 —— 下方 40% 画水感 */}
      <div className="absolute inset-x-0 bottom-0 h-[55%] opacity-55">
        <Waves
          style={{ position: "absolute", inset: 0 }}
          colorFront="#1a2e48"
          colorBack="#0a1828"
          spacing={0.085}
          shape={1}
          frequency={0.18}
          amplitude={0.32}
          rotation={0}
          proportion={0.42}
          softness={0.95}
        />
      </div>

      {/* 顶部月光 —— 柔化过渡 */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 120% 70% at 50% -15%, rgba(170, 200, 235, 0.22), transparent 70%)",
        }}
      />

      {/* 底部深压 —— 让下方内容区过渡到深色 */}
      <div
        className="absolute inset-x-0 bottom-0 h-1/3"
        style={{
          background:
            "linear-gradient(180deg, transparent 0%, rgba(5, 10, 18, 0.7) 70%, rgba(3, 6, 12, 0.95) 100%)",
        }}
      />
    </div>
  );
}
