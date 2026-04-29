"use client";

/**
 * pin-thumb · 钉拖拽缩略图生成 / 共享 MIME
 *
 * 治本方案（不再为 thumbDataUrl 缺失走 fallback 兜底）：
 *
 * 1. **drag source 始终带 thumb**：PanelPinHandle / MessagePinHandle 在 dragstart
 *    时同步生成一个内联 SVG `data:image/svg+xml;utf8,...` URI 写入 dataTransfer
 *    （MIME = `pin/thumb`），保证 composer drop 永远能拿到一个 thumbDataUrl，
 *    哪怕原 DOM 里没有真图片素材。
 *
 * 2. **SVG 设计要素**：accentVar 色条 + 主标题 + 副标题，200×120，**纯样式**
 *    （不嵌入实际页面截图，避免引入 html2canvas 重依赖）。
 *
 * 3. **对外契约**：消费方（ComposerBar handleDrop / archive composer onDrop）
 *    只读 `PIN_THUMB_MIME`，得到 data URL 写进 ImMessage.refs.thumbDataUrl，
 *    MessageBubble.PinRefThumbnail 直接 `<img src=...>` 渲染。
 *
 * 不做的事：
 *   - 不引入 html2canvas / dom-to-image（package.json 没装，新增依赖成本不值）
 *   - 不做异步 canvas 截图（dragstart 必须同步 setData，等不起 await）
 *   - 不做关键词/正则黑名单（黑名单永远列不全）
 */

/** 拖拽 dataTransfer 上承载缩略图的 MIME 类型。 */
export const PIN_THUMB_MIME = "application/x-pin-thumb";

/** SVG 渲染入参 —— 渲染语义和 PinRefThumbnail / 缩略卡视觉对齐。 */
export interface PinThumbSpec {
  /** 主标题（如 "营销优先级雷达"）。≥1 行截断。 */
  title: string;
  /** 副标题（"获客 · 厦门瑞鼎" / 发言人时间戳）。可空。 */
  subtitle?: string;
  /** 6 Agent CSS var 名（如 "--t-channel" / "--t-report"），决定色条色。 */
  accentVar?: string;
  /** 类型标签 · panel / message / card · SVG 右上角小角标。 */
  badge?: string;
}

/** 6 Agent var → 实色 fallback（SVG 不能直接吃 CSS var，必须有具体色值）。
 *  与 platform-shell-v2 §7 6 Agent 功能色映射一致；后端不存这些值，
 *  只在 SVG 缩略图静态渲染时用。 */
const ACCENT_FALLBACK: Record<string, string> = {
  "--t-report": "#a16949",
  "--t-alert": "#b25244",
  "--t-compli": "#3f6b54",
  "--t-credit": "#4279a3",
  "--t-riskctrl": "#7a4783",
  "--t-channel": "#3f8a82",
};

const DEFAULT_ACCENT = "#7a6a52"; // 中性墨褐

function resolveAccent(accentVar?: string): string {
  if (!accentVar) return DEFAULT_ACCENT;
  return ACCENT_FALLBACK[accentVar] ?? DEFAULT_ACCENT;
}

/** XML 安全转义（SVG 文本节点用）。 */
function xmlEscape(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/** 中文/英文混合截断 · 简单按字符数。 */
function clip(s: string, max: number): string {
  const flat = s.replace(/\s+/g, " ").trim();
  return flat.length > max ? flat.slice(0, max - 1) + "…" : flat;
}

/** 生成一张 200×120 的 SVG data URL · 同步、零依赖、< 1KB。 */
export function buildPinThumbDataUrl(spec: PinThumbSpec): string {
  const accent = resolveAccent(spec.accentVar);
  const title = xmlEscape(clip(spec.title, 22));
  const subtitle = spec.subtitle ? xmlEscape(clip(spec.subtitle, 28)) : "";
  const badge = spec.badge ? xmlEscape(clip(spec.badge, 6)) : "";

  // 结构：左侧 6px 色条 + 标题（中粗 13px） + 副标题（11px 灰） + 右上小角标
  // 中文用通用 sans-serif 栈（SVG inline 不能 @import 字体，浏览器自动 fallback）
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="120" viewBox="0 0 200 120">
  <rect x="0" y="0" width="200" height="120" rx="10" ry="10" fill="#f7f3ec" stroke="#d8cfbe" stroke-width="1"/>
  <rect x="0" y="0" width="6" height="120" fill="${accent}"/>
  <text x="18" y="40" font-family="'Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif" font-size="13" font-weight="600" fill="#2a2519">${title}</text>
  ${subtitle ? `<text x="18" y="64" font-family="'Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif" font-size="11" fill="#6a6253">${subtitle}</text>` : ""}
  <text x="18" y="100" font-family="'JetBrains Mono',monospace" font-size="9" fill="${accent}" letter-spacing="1">PIN</text>
  ${badge ? `<rect x="156" y="10" width="34" height="16" rx="3" ry="3" fill="${accent}" opacity="0.18"/><text x="173" y="22" font-family="'JetBrains Mono',monospace" font-size="9" fill="${accent}" text-anchor="middle">${badge}</text>` : ""}
</svg>`;

  // encodeURIComponent 保证中文/特殊字符在 data URL 中合法
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}
