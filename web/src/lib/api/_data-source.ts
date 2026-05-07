/**
 * data_source SSOT (per Q-054 件 #2 + Q-055 KT cherry-pick + live-fallback-banner-spec v1.0).
 *
 * 后端 canon (shared/sse_envelope.py:81-86): 5 enum 是产品 trust model 唯一锚点。前端
 * 6 agent client 必走本文件 normalizeDataSource() · 不允许各自再 string union。
 *
 *   live           → 真实 LLM / 真实搜索路径 (Tavily / 政府 API / akshare 等)
 *   mock           → 历史 session / 演示模式 (用户主动选历史)
 *   mock_forced    → 前端显式切 DEMO (force_mock=true · /api/<agent>/demo/run)
 *   mock_fallback  → 主路径 fail · 后端自动降级 mock (Q-055 §"4 backend 默认假数据混跑")
 *   cached         → 命中 LLM cache (无新 LLM 调用 · 响应 << 1s)
 *
 * 与 §3.5.1 #6 数据时效 (CLAUDE.md) 互补:
 *   - data_source = 单次 call 的真假属性 (per-call · trust model 一级)
 *   - source_tier = 单条 evidence 的层级 (per-evidence · 推荐核心理由 SLA · 一级权威~四级公开)
 *   本文件 dataSourceLabel(opts) 接受 sourceTier 可选 · 透出但不强制每 workspace 显示。
 *
 * 红线 (per AGENT_IDENTITY 件 #2):
 *   - 不引入新 LLM 调用 (BASELINE=30 · DIFF guard 必 0 新增) · 本文件纯 string-handling
 *   - 不破 Q-041 4 字段 candidate metadata · 本文件不动 candidate schema
 */
"use client";

export const DATA_SOURCE_KINDS = [
  "live",
  "mock",
  "mock_forced",
  "mock_fallback",
  "cached",
] as const;

export type DataSourceKind = (typeof DATA_SOURCE_KINDS)[number];


/** 后端 emit 不规范 / 缺字段 / 历史 mock-session 没 data_source 时统一 fallback "mock". */
export function normalizeDataSource(raw: unknown): DataSourceKind {
  if (typeof raw !== "string") return "mock";
  const v = raw.trim().toLowerCase();
  return (DATA_SOURCE_KINDS as readonly string[]).includes(v)
    ? (v as DataSourceKind)
    : "mock";
}


/** UI banner / badge tone · 决定颜色 + icon. */
export type DataSourceTone = "ok" | "info" | "warn";


/**
 * tone 映射 (per banner-spec v1.0 §2):
 *   live / cached  → ok   (绿/中性 · 表示真实 / 缓存命中均无信任降级)
 *   mock           → info (蓝/灰 · 历史演示 · 显式选过)
 *   mock_forced    → info (蓝 · 用户主动 DEMO 模式)
 *   mock_fallback  → warn (黄 · 后端 fail 自动降级 · 用户必感知)
 *
 * cached 归 ok 因为底层数据是 live 来源 · 命中 cache 仅是优化;
 * mock_fallback 归 warn 因为 trust model 一级降级 (Q-055 §4 backend 假数据混跑根因).
 */
export function dataSourceTone(kind: DataSourceKind): DataSourceTone {
  switch (kind) {
    case "live":
    case "cached":
      return "ok";
    case "mock":
    case "mock_forced":
      return "info";
    case "mock_fallback":
      return "warn";
  }
}


/** 默认中文短标签 (badge 单行用 · ≤ 6 个汉字). */
const DEFAULT_LABEL: Record<DataSourceKind, string> = {
  live: "真实数据",
  mock: "演示模式",
  mock_forced: "DEMO 模式",
  mock_fallback: "降级演示",
  cached: "缓存命中",
};


export type DataSourceLabelOptions = {
  /** 具体 provider 名 · e.g. "Tavily" / "akshare" / "gov.cn" / "pbc.gov" / "企查查" · 显示在 badge tooltip 或第二行. */
  provider?: string;
  /** §3.5.1 #6 数据源 4 Tier (1=内部权威 · 2=政府监管 · 3=行业 · 4=公开 web). 可选透出. */
  sourceTier?: 1 | 2 | 3 | 4;
  /** §3.5.1 #6 freshness_days · 仅显示数字 · 调用方决定是否拼"近 N 天". 可选透出. */
  freshnessDays?: number;
};


/**
 * Badge / banner 主标签文案 · 仅 5 enum 短词 · 不含 provider/tier 描述.
 * Provider/tier/freshness 拼接用 dataSourceProviderHint() · 给 tooltip / 副标 / longLabel.
 */
export function dataSourceLabel(kind: DataSourceKind): string {
  return DEFAULT_LABEL[kind];
}


/**
 * Long 标签 (用于 banner 二级文案 / tooltip · 含 provider+tier+freshness).
 * 例: "真实数据 · via Tavily · Tier 4 公开 web · 近 12 天"
 */
export function dataSourceLongLabel(
  kind: DataSourceKind,
  opts?: DataSourceLabelOptions,
): string {
  const main = dataSourceLabel(kind);
  const parts: string[] = [main];
  if (opts?.provider) parts.push(`via ${opts.provider}`);
  if (opts?.sourceTier !== undefined) parts.push(`Tier ${opts.sourceTier} ${tierName(opts.sourceTier)}`);
  if (opts?.freshnessDays !== undefined && opts.freshnessDays >= 0) {
    parts.push(`近 ${opts.freshnessDays} 天`);
  }
  return parts.join(" · ");
}


/** §3.5.1 #6 4 Tier 中文短名 · 显式 ladder. */
export function tierName(tier: 1 | 2 | 3 | 4): string {
  switch (tier) {
    case 1: return "内部权威";
    case 2: return "政府监管";
    case 3: return "行业";
    case 4: return "公开 web";
  }
}


/** 是否触发 banner-spec rule 1+2 黄/红 banner 显式提示 (mock_fallback / 历史 mock 用). */
export function isFallback(kind: DataSourceKind): boolean {
  return kind === "mock_fallback" || kind === "mock" || kind === "mock_forced";
}


/** banner-spec §2 规则 1 触发: live 路径 fail 自动降级到 mock_fallback · 必显式 banner. */
export function isLiveDegraded(kind: DataSourceKind): boolean {
  return kind === "mock_fallback";
}


/**
 * Provider hint string · 给 tooltip / aria-label / debug log.
 * 不 i18n · 仅中文调试用.
 */
export function dataSourceProviderHint(
  kind: DataSourceKind,
  opts?: DataSourceLabelOptions,
): string {
  if (!opts?.provider && opts?.sourceTier === undefined && opts?.freshnessDays === undefined) {
    return dataSourceLabel(kind);
  }
  return dataSourceLongLabel(kind, opts);
}
