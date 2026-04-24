/**
 * claimParser — 把后端正文里的 [ref:xxx]...[/ref] 锚点切出来包高亮。
 *
 * 格式约定(来自 shared/evidence/protocol.py Phase 2 grounded 生成):
 *   "营收 5820 万[ref:ev_001]毛利率 32%[/ref]进入行业 70 分位"
 *   → ["营收 5820 万", <HighlightCard refId="ev_001">毛利率 32%</HighlightCard>, "进入行业 70 分位"]
 *
 * 降级(Task B 硬指标):
 *   - 无 [ref:] 锚点 → 原样渲染,不报错
 *   - ref_id 在 evidence_trail 里找不到 → HighlightCard 内部退回 <span> (见 HighlightCard.tsx)
 *   - 嵌套 / 未闭合 [ref:xxx] 无 [/ref] → 当作普通文本
 *
 * 纯字符串分析,不做 NLP 启发式识别 claim — 完全依赖后端插锚点。
 */

const REF_PATTERN = /\[ref:([A-Za-z0-9_\-]+)\]([\s\S]+?)\[\/ref\]/g;

export type ClaimToken =
  | { kind: "text"; content: string }
  | { kind: "ref"; refId: string; content: string };

export function parseClaims(text: string): ClaimToken[] {
  if (!text || typeof text !== "string") return [];
  const tokens: ClaimToken[] = [];
  let cursor = 0;
  // Reset regex state between calls (global flag retains lastIndex across calls).
  const re = new RegExp(REF_PATTERN.source, "g");
  let match: RegExpExecArray | null;
  while ((match = re.exec(text)) !== null) {
    if (match.index > cursor) {
      tokens.push({ kind: "text", content: text.slice(cursor, match.index) });
    }
    tokens.push({ kind: "ref", refId: match[1], content: match[2] });
    cursor = match.index + match[0].length;
  }
  if (cursor < text.length) {
    tokens.push({ kind: "text", content: text.slice(cursor) });
  }
  return tokens;
}

export function hasAnchors(text: string): boolean {
  if (!text) return false;
  const re = new RegExp(REF_PATTERN.source);
  return re.test(text);
}
