"use client";

import { MeshGradient, Waves } from "@paper-design/shaders-react";

/**
 * AtmosphericBg —— 用 WebGL shader 做无色带的海雾氛围底。
 * 三层：MeshGradient（整页深海蓝有机流动）+ Waves（水面波纹）+ 上光柔化层。
 */
export default function AtmosphericBg() {
  return (
    <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
      {/* 基底 —— 深炭灰 monochrome，无蓝色饱和 */}
      <MeshGradient
        style={{ position: "absolute", inset: 0 }}
        colors={[
          "#0a0b0d",
          "#16181c",
          "#1e2126",
          "#0d0e11",
          "#13161a",
        ]}
        speed={0.1}
        distortion={0.55}
        swirl={0.2}
        offsetX={0}
        offsetY={0}
        scale={1.3}
      />

      {/* 顶部月光 —— 冷白银，极淡 */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 110% 40% at 50% -12%, rgba(210, 220, 232, 0.12), transparent 60%)",
        }}
      />

      {/* 极淡水纹 —— 钢灰不是蓝 */}
      <div className="absolute inset-0 opacity-[0.12] mix-blend-overlay">
        <Waves
          style={{ position: "absolute", inset: 0 }}
          colorFront="#6a6e74"
          colorBack="#14161a"
          spacing={0.2}
          shape={1.5}
          frequency={0.08}
          amplitude={0.18}
          rotation={0}
          proportion={0.5}
          softness={1}
        />
      </div>
    </div>
  );
}
