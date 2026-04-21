"use client";

/**
 * 登录页左侧主视觉 · 分层合成 + 物理遮挡
 *
 * 层序（下→上）：
 * 1. cosmic__backdrop — cosmic.png 全图做底（保留原图的美术质感）
 * 2. cosmic__ring--back — SVG 粒子环流，clipPath 只露星环"背面"那一半
 * 3. cosmic__planet — 从 cosmic.png 抠出的行星盘面（scripts/extract_planet_disk.py）
 * 4. cosmic__planet-spin — 盘面内漂移光带，伪装自转
 * 5. cosmic__ring--front — SVG 粒子环流，clipPath 只露"正面"那一半
 *
 * 背面粒子在第 2 层，后面会被行星盘面覆盖（=遮挡住"绕到行星后面"的那部分）；
 * 正面粒子在第 5 层，画在所有东西之上（=显示"从行星前面穿过"的那部分）。
 * 两个 SVG 的粒子用完全一致的轨迹和时序，clip 各取一半，合起来看就是一圈连续的粒子绕行。
 *
 * 轨迹基于 cosmic.png 实际像素：行星中心 (420,417)，星环近似 a=390 b=100 倾角 -12°。
 */

const SPECK_COUNT = 30;
const VIEW_BOX = "0 0 910 811";
// 星环路径 · 中心 (420,417) · 半轴 (390,100) · 倾角 -12°
const RING_D =
  "M 801 336 A 390 100 -12 1 1 39 498 A 390 100 -12 1 1 801 336 Z";
// 主轴分界线：y = 417 - (x-420)*tan(12°) ≈ 417 - 0.213(x-420)
// 线在 x=0:  y ≈ 506.5；x=910: y ≈ 312.6
const BACK_POLY = "0,0 910,0 910,312.6 0,506.5"; // 星环主轴以上（背面）
const FRONT_POLY = "0,506.5 910,312.6 910,811 0,811"; // 主轴以下（正面）

function RingSpecks({
  half,
  clip,
}: {
  half: "back" | "front";
  clip: string;
}) {
  return (
    <svg
      className={`cosmic__ring cosmic__ring--${half}`}
      viewBox={VIEW_BOX}
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <path id={`cosmic-ring-${half}`} d={RING_D} />
        <clipPath id={`cosmic-clip-${half}`}>
          <polygon points={clip} />
        </clipPath>
        <filter
          id={`cosmic-glow-${half}`}
          x="-50%"
          y="-50%"
          width="200%"
          height="200%"
        >
          <feGaussianBlur stdDeviation="2.8" />
        </filter>
      </defs>
      <g
        clipPath={`url(#cosmic-clip-${half})`}
        filter={`url(#cosmic-glow-${half})`}
      >
        {Array.from({ length: SPECK_COUNT }).map((_, i) => {
          const r = 2.2 + (i % 5) * 1.2;
          const fill =
            i % 4 === 0
              ? "#fff2d2"
              : i % 4 === 1
              ? "#ffcc88"
              : i % 4 === 2
              ? "#ff9a56"
              : "#ff7030";
          const opacity = 0.7 + (i % 3) * 0.1;
          const begin = `-${((i * 22) / SPECK_COUNT).toFixed(2)}s`;
          return (
            <circle key={i} r={r} fill={fill} opacity={opacity}>
              <animateMotion
                dur="22s"
                repeatCount="indefinite"
                begin={begin}
              >
                <mpath href={`#cosmic-ring-${half}`} />
              </animateMotion>
            </circle>
          );
        })}
      </g>
    </svg>
  );
}

export function CosmicStage() {
  return (
    <div className="cosmic" aria-hidden>
      <div className="cosmic__system">
        <div className="cosmic__halo" />
        <div className="cosmic__img">
          <div className="cosmic__backdrop" />
          <RingSpecks half="back" clip={BACK_POLY} />
          <div className="cosmic__planet" />
          <div className="cosmic__planet-spin" />
          <RingSpecks half="front" clip={FRONT_POLY} />
        </div>
      </div>
      <div className="cosmic__vignette" />
    </div>
  );
}
