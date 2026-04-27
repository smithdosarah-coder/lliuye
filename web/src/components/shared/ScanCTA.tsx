"use client";

/**
 * ScanCTA · 共享进度 CTA (visual-v3 demo · 2026-04-23)
 *
 * 5 agent workspace 通用：点按钮 fake 5 步 loading · 给 demo "过程感"。
 * 复用 CreditWorkspace startGenerate 模式 · 抽成可复用组件。
 *
 * 用法：
 *   <ScanCTA
 *     label="扫描信号源"
 *     tone="channel"
 *     steps={[{label:"连接数据源", pct:20}, ...]}
 *   />
 */

import { useEffect, useRef, useState } from "react";

export interface ScanStep {
  /** 该步显示文字 */
  label: string;
  /** 该步累进百分比 0-100 */
  pct: number;
}

export type ScanTone = "channel" | "alert" | "compli" | "report" | "credit" | "riskctrl";

export interface ScanCTAProps {
  /** idle 态按钮文字 */
  label: string;
  /** running 态按钮文字（默认 "扫描中…"） */
  runningLabel?: string;
  /** 假进度步骤 */
  steps: ScanStep[];
  /** 每步间隔 ms（默认 450） */
  tickMs?: number;
  /** agent 色 */
  tone?: ScanTone;
  /** 完成回调 */
  onDone?: () => void;
}

export function ScanCTA({
  label,
  runningLabel = "扫描中…",
  steps,
  tickMs = 450,
  tone,
  onDone,
}: ScanCTAProps) {
  const [progress, setProgress] = useState<{
    running: boolean;
    step: number;
    pct: number;
    label: string;
  }>({ running: false, step: -1, pct: 100, label: "准备就绪 · 点按钮触发" });
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) window.clearInterval(timerRef.current);
    };
  }, []);

  function start() {
    if (progress.running || steps.length === 0) return;
    if (timerRef.current !== null) window.clearInterval(timerRef.current);
    setProgress({ running: true, step: 0, pct: 0, label: steps[0].label });

    /* 2026-04-23 · B+ · 真 fetch Python 后端 · /api/run/{agent_id}
       · 后端 asyncio.sleep 2.2s 模拟 AI · 前端同时播 progress（UI 流畅不等）
       · fetch 失败 console.warn 后回退 mock · demo 不崩（Python 没启也能跑） */
    // prod: 相对 path 走 nginx · dev: NEXT_PUBLIC_API_BASE=http://localhost:8000
    const apiBase =
      (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) ||
      "";
    const agentKey = tone === "compli" ? "compliance" : tone ?? "channel";
    fetch(`${apiBase}/api/run/${agentKey}`, { method: "POST" })
      .then((r) => r.json())
      .then((data) => {
        console.log(`[ScanCTA] ${agentKey} backend ack:`, data);
      })
      .catch((err) => {
        console.warn(
          `[ScanCTA] ${agentKey} backend unreachable · fallback to mock:`,
          err,
        );
      });

    let i = 0;
    timerRef.current = window.setInterval(() => {
      const s = steps[i];
      setProgress({
        running: i < steps.length - 1,
        step: i,
        pct: s.pct,
        label: s.label,
      });
      if (i === steps.length - 1) {
        if (timerRef.current !== null) window.clearInterval(timerRef.current);
        timerRef.current = null;
        onDone?.();
      }
      i += 1;
    }, tickMs);
  }

  return (
    <div
      className="scan-cta"
      data-tone={tone}
      data-running={progress.running ? "yes" : "no"}
    >
      <button
        type="button"
        className="scan-cta-btn"
        data-testid="scan-trigger"
        onClick={start}
        disabled={progress.running}
      >
        <span className="scan-cta-btn-lbl">
          {progress.running ? runningLabel : label}
        </span>
        <span className="scan-cta-btn-ic" aria-hidden>
          {progress.running ? "◌" : "▸"}
        </span>
      </button>
      <div className="scan-cta-bar" data-testid="scan-progress">
        <div
          className="scan-cta-fill"
          style={{ width: `${progress.pct}%` }}
        />
      </div>
      <div className="scan-cta-label">
        <span className="scan-cta-step">
          {progress.step >= 0
            ? `${String(progress.step + 1).padStart(2, "0")} / ${String(steps.length).padStart(2, "0")}`
            : "READY"}
        </span>
        <span className="scan-cta-txt">{progress.label}</span>
        <span className="scan-cta-pct">{Math.round(progress.pct)}%</span>
      </div>
    </div>
  );
}
