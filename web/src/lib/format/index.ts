/**
 * F1 (V4 plan · Phase B-1) · 金融数字 + 货币格式化 utilities
 *
 * 4 角色 view (today/dispatch/archive/warroom) 全数字达金融规范:
 * - 千分位 (¥50,000,000.00)
 * - Tabular Figures (CSS class .num · font-variant-numeric: tabular-nums)
 * - 严格右对齐 (CSS class .num-right)
 * - 纯中文术语 (utils 不带英文 · 调用方负责 label)
 *
 * 来源: V4 plan F1 (主 CLI A1 + Gemini 升级 + Codex 同意)
 * 配套: web/src/app/globals.css `.num` / `.num-right` / `.num-tabular` utility class
 */

const NBSP = " ";

/** 货币格式化 · 默认 ¥ 符号 + 千分位 + 2 位小数。
 *  示例: formatCurrency(50000000) → "¥50,000,000.00"
 *        formatCurrency(8000000, { fractionDigits: 0 }) → "¥8,000,000"
 *        formatCurrency(null) → "—" (无源时显 fallback 标识) */
export function formatCurrency(
  value: number | null | undefined,
  opts: {
    fractionDigits?: number;
    symbol?: string;
    /** 单位扩展 (per V4 plan "纯中文术语"): "万" / "亿" 等 · 调用方决定 */
    unit?: string;
  } = {},
): string {
  const { fractionDigits = 2, symbol = "¥", unit } = opts;
  if (value == null || Number.isNaN(value)) return "—";
  const formatted = value.toLocaleString("zh-CN", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
  return unit ? `${symbol}${formatted}${NBSP}${unit}` : `${symbol}${formatted}`;
}

/** 万元格式化 · 把 value (元) 转 "X,XXX.XX 万元" · 银行常用单位。
 *  示例: formatCurrencyWan(8000000) → "¥800.00 万元"
 *        formatCurrencyWan(12000000, { fractionDigits: 0 }) → "¥1,200 万元" */
export function formatCurrencyWan(
  value: number | null | undefined,
  opts: { fractionDigits?: number; symbol?: string } = {},
): string {
  const { fractionDigits = 2, symbol = "¥" } = opts;
  if (value == null || Number.isNaN(value)) return "—";
  const wan = value / 10_000;
  const formatted = wan.toLocaleString("zh-CN", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
  return `${symbol}${formatted}${NBSP}万元`;
}

/** 普通数字千分位 · 不带货币符号。用于户数/笔数/天数等 metric。
 *  示例: formatNumber(1234) → "1,234"
 *        formatNumber(15.7, { fractionDigits: 1 }) → "15.7" */
export function formatNumber(
  value: number | null | undefined,
  opts: { fractionDigits?: number; unit?: string } = {},
): string {
  const { fractionDigits = 0, unit } = opts;
  if (value == null || Number.isNaN(value)) return "—";
  const formatted = value.toLocaleString("zh-CN", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
  return unit ? `${formatted}${NBSP}${unit}` : formatted;
}

/** 百分比格式化 · 输入 0-1 区间或 0-100 区间 (mode 决定)。
 *  示例: formatPercent(0.025, { mode: "ratio" }) → "2.5%"
 *        formatPercent(2.5, { mode: "percent" }) → "2.5%" */
export function formatPercent(
  value: number | null | undefined,
  opts: { fractionDigits?: number; mode?: "ratio" | "percent" } = {},
): string {
  const { fractionDigits = 1, mode = "ratio" } = opts;
  if (value == null || Number.isNaN(value)) return "—";
  const pct = mode === "ratio" ? value * 100 : value;
  return `${pct.toLocaleString("zh-CN", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })}%`;
}

/** 智能金额格式 · ≥1 万自动转万元 · <1 万显元。
 *  常用于客户列表/卡片摘要等不固定量级场景。
 *  示例: formatCurrencySmart(8000000) → "¥800.00 万元"
 *        formatCurrencySmart(5000) → "¥5,000.00" */
export function formatCurrencySmart(
  value: number | null | undefined,
  opts: { fractionDigits?: number } = {},
): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (Math.abs(value) >= 10_000) return formatCurrencyWan(value, opts);
  return formatCurrency(value, opts);
}
