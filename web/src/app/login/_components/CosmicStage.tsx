"use client";

/**
 * 登录页左侧主视觉 · 宇宙静态大图 + 三路独立动画
 *
 * 策略：
 * - 图片本身静止，不做整体旋转（整体转会被读作"全景在旋"，违反物理直觉）
 * - 星环：SVG `<animateMotion>` 让一批发光粒子沿椭圆路径流动（看起来是环在绕）
 * - 行星：盘面内 clip 一条漂移的亮带，伪装成自转把地表带出视野
 * - 光晕：缓慢呼吸，给星体加点生命力
 *
 * 星空层已经挪到 `.login-sky`（跨左右两栏铺满），这里只负责星系主体。
 */
const SPECK_COUNT = 32;

export function CosmicStage() {
  return (
    <div className="cosmic" aria-hidden>
      <div className="cosmic__system">
        <div className="cosmic__halo" />
        <div className="cosmic__img">
          <svg
            className="cosmic__ring"
            viewBox="0 0 100 100"
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              <path
                id="cosmic-ringpath"
                d="M 94 40.6 A 45 13 -12 1 1 6 59.4 A 45 13 -12 1 1 94 40.6 Z"
              />
              <filter
                id="cosmic-speck-glow"
                x="-50%"
                y="-50%"
                width="200%"
                height="200%"
              >
                <feGaussianBlur stdDeviation="0.35" />
              </filter>
            </defs>
            <g filter="url(#cosmic-speck-glow)">
              {Array.from({ length: SPECK_COUNT }).map((_, i) => {
                const r = 0.3 + (i % 5) * 0.12;
                const fill =
                  i % 3 === 0
                    ? "#ffe6c0"
                    : i % 3 === 1
                    ? "#ffb070"
                    : "#ff8a4c";
                const opacity = 0.55 + (i % 4) * 0.12;
                const begin = `-${((i * 22) / SPECK_COUNT).toFixed(2)}s`;
                return (
                  <circle key={i} r={r} fill={fill} opacity={opacity}>
                    <animateMotion
                      dur="22s"
                      repeatCount="indefinite"
                      begin={begin}
                    >
                      <mpath href="#cosmic-ringpath" />
                    </animateMotion>
                  </circle>
                );
              })}
            </g>
          </svg>
          <div className="cosmic__planet-spin" />
        </div>
      </div>
      <div className="cosmic__vignette" />
    </div>
  );
}
