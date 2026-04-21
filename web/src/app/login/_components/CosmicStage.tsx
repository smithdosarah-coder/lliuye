"use client";

/**
 * 登录页左侧主视觉 · 静态宇宙大图 + CSS 层特效
 *
 * 策略：不用 three.js 跑全场景；以参考图为底图，叠加：
 * - 星点 twinkle 层（CSS 关键帧随机闪烁）
 * - 环与行星交汇处的光斑 pulse（radial-gradient）
 * - 整体慢 zoom + 漂移，制造呼吸感
 *
 * 好处：包体小、首屏快、视觉与参考图 1:1，而不是折腾 shader 去逼近。
 */
export function CosmicStage() {
  return (
    <div className="cosmic" aria-hidden>
      <div className="cosmic__field" />
      <div className="cosmic__stars" />
      <div className="cosmic__system">
        <div className="cosmic__halo" />
        <div className="cosmic__img" />
        <div className="cosmic__flare" />
      </div>
      <div className="cosmic__vignette" />
    </div>
  );
}
