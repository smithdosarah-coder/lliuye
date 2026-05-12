/**
 * B.4 · SLO-2 主活 B · 演示模式 seeded replay 一致性 helper
 *
 * PM 真意 (verbatim 2026-05-11 12:55):
 *   "6 助手演示模式 seeded mock 全 replay (同 sample 2 次结果一致 · PM 演示给客户用)"
 *
 * 关键: 演示给客户看不能"同样数据跑出不同结果" · LLM 必须用 fixed seed / canned response
 * 或 demo mode 走纯确定性 pipeline (§3.1 确定性 vs 概率性边界 · §3.5.1 #6 数据时效).
 *
 * 实现:
 *   - 同一 page session 内跑 2 次 demo · 抓关键字段 hash
 *   - 不同 page session 之间跑 ≠ 必然要求 (服务端 cache 不算 replay 真值)
 *   - 若 hash 不等 = demo mode LLM 未 deterministic = PM 真要 fix
 */
import type { Page } from "@playwright/test";

/**
 * 简单字符串 hash (FNV-1a 32-bit · 跨 JS impl 稳定)
 */
export function fnv1a(s: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = (h * 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, "0");
}

/**
 * 抓 page 上所有匹配 selector 的 innerText · join + hash
 * 用于比 2 次跑的 "demo mode 关键输出区"
 */
export async function hashTexts(page: Page, selectors: string[]): Promise<string> {
  const parts: string[] = [];
  for (const sel of selectors) {
    const elems = page.locator(sel);
    const count = await elems.count();
    for (let i = 0; i < count; i++) {
      parts.push((await elems.nth(i).innerText()).trim());
    }
  }
  return fnv1a(parts.join("\n##\n"));
}

/**
 * 抓 page 结构指标 (= LLM 文本无关的稳定输出):
 *   - 每个 selector 的 element count
 *   - 整页提取的数字 list (前 50 个 · sorted ascending)
 *
 * 用于比 2 次跑的"宏观一致" · 容 LLM micro-diff (措辞 / 排序微变).
 *
 * PM 真意 (verbatim): "演示给客户用" — 担心的是"昨 8 候选 今 5 候选" macro shift
 *   不是 "每行字面一致" (LLM byte-level deterministic 几乎不可能).
 */
export async function structuralFingerprint(
  page: Page,
  countSelectors: string[],
): Promise<{ counts: Record<string, number>; numbers: number[] }> {
  const counts: Record<string, number> = {};
  for (const sel of countSelectors) {
    counts[sel] = await page.locator(sel).count();
  }
  const body = await page.locator("body").innerText();
  // 提取所有 1-3 位整数或小数 · sort + dedup + 前 50 个
  const matched = body.match(/\b\d{1,3}(?:\.\d+)?\b/g) ?? [];
  const nums = [...new Set(matched.map((s) => parseFloat(s)))]
    .filter((n) => !Number.isNaN(n))
    .sort((a, b) => a - b)
    .slice(0, 50);
  return { counts, numbers: nums };
}

/**
 * Reload page · 等指定 selector 可见 (= demo 跑前 ready)
 */
export async function reloadAndWait(
  page: Page,
  path: string,
  readySelector: string,
  timeout = 30_000,
): Promise<void> {
  await page.goto(path, { waitUntil: "networkidle" });
  await page.locator(readySelector).waitFor({ state: "visible", timeout });
}
