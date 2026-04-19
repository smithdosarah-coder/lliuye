"use client";

/**
 * Today Hero · eyebrow + h1 glyph-rise + hero-meta (3 KV + 1 live pill)
 * Source: design_mockups/rm-assistant-final-2026-04-19.html
 *         L223-356 (CSS) + L2791-2809 (markup)
 *
 * - <h1> 每字符拆 <span class="glyph cn">, 用 useEffect 清 animation → 强制
 *   reflow → 回填 → 设 animationDelay, 保证导航回来时 stagger 重放 (mockup
 *   staggerH1 L3575-3599)
 * - eyebrow 日期动态: SSR 占位 "—", client useEffect 填入
 * - live pill 时钟 20s tick
 * - data-theme 切换 bg: 依赖 shell-root 的 --g0..--g7 渐变,hero 自身透明
 */

import { useEffect, useRef, useState, type CSSProperties } from "react";

const HERO_WORD = "今日看板";
const STAGGER_BASE = 0.8; // s, mockup staggerH1 baseDelay
const STAGGER_STEP = 0.045; // s per glyph

function formatEyebrowDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const wd = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"][d.getDay()];
  return `${y} · ${m} · ${day} · ${wd}`;
}

function formatLiveTime(d: Date): string {
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

export function Hero() {
  const h1Ref = useRef<HTMLHeadingElement | null>(null);
  const [eyebrowDate, setEyebrowDate] = useState<string>("—");
  const [liveTime, setLiveTime] = useState<string>("--:--");

  // Re-trigger glyph-rise on mount (mockup staggerH1 pattern)
  useEffect(() => {
    const glyphs = h1Ref.current?.querySelectorAll<HTMLSpanElement>(".glyph");
    if (!glyphs) return;
    glyphs.forEach((g, i) => {
      g.style.animation = "none";
      // force reflow
      void g.offsetWidth;
      g.style.animation = "";
      g.style.animationDelay = `${STAGGER_BASE + i * STAGGER_STEP}s`;
    });
  }, []);

  // Eyebrow date (hydration-safe, client-only) + live tick
  useEffect(() => {
    function tick() {
      const d = new Date();
      setEyebrowDate(formatEyebrowDate(d));
      setLiveTime(formatLiveTime(d));
    }
    tick();
    const id = setInterval(tick, 20000);
    return () => clearInterval(id);
  }, []);

  return (
    <>
      <div className="eyebrow">
        <span>{eyebrowDate}</span>
        <span className="sep" />
        <em>早上好，王哲。</em>
      </div>

      <h1 ref={h1Ref} className="hero-h1" id="h1Today">
        <span className="word" data-w={HERO_WORD} data-cjk="1">
          {[...HERO_WORD].map((ch, i) => (
            <span
              key={`${ch}-${i}`}
              className="glyph cn"
              style={
                {
                  animationDelay: `${STAGGER_BASE + i * STAGGER_STEP}s`,
                  "--i": i,
                } as CSSProperties
              }
            >
              {ch}
            </span>
          ))}
        </span>
      </h1>

      <div className="hero-meta hero-meta--row">
        <span className="kv big">
          <span className="k">管道总额 · Pipeline</span>
          <span className="v">
            ¥<span className="vnum">28.5</span>
            <span className="vunit">亿</span>
          </span>
        </span>
        <span className="kv big">
          <span className="k">在队项 · Queue</span>
          <span className="v">
            <span className="vnum">14</span>
            <span className="vunit">项</span>
          </span>
        </span>
        <span className="kv big">
          <span className="k">风险等级 · Risk</span>
          <span className="v">
            <span className="vnum">黄色</span>
            <span className="vunit">III</span>
          </span>
        </span>
        <span className="pill">
          <span className="livedot" />
          LIVE · {liveTime} <span className="cn">同步</span>
        </span>
      </div>
    </>
  );
}
