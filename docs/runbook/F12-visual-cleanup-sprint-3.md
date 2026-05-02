# F12 视觉清洗 + F1c mock 中文术语 · Sprint 3 完整重塑 checklist

> **Sprint 2 (worker-B3)** 已 ship 基础设施: tokens.css 加 `--pingfang` / `--misans` /
> `--inter` 字体栈 + `--r-sharp` 8px 圆角 token (commit 待提)。完整大重塑推
> **Sprint 3** (跟 Gemini design phase 一起)。
>
> 来源: V4 plan F12 (Gemini R1+R2 主张端正 · Codex 同意) + F1c (V4 plan F1
> Sprint 1 漏的 mock data 字符串字面值改 number)。

---

## 1. 当前 Sprint 2 已 ship 的基础设施 (worker-B3 commit 待提)

| 文件 | 改动 | 用途 |
|---|---|---|
| `web/src/app/tokens.css` | +5 行 token | `--pingfang` / `--misans` / `--inter` 字体栈 + `--r-sharp` 8px 圆角 |

**当前不动**:
- `--display` / `--sans` / `--cjk` default 字体栈 (Funnel Display / Instrument Sans / Noto Sans SC)
- `--r-md` 18px / `--r-lg` 26px (mockup 设计意图保留)
- 4 主题 8 档渐变 (`--g0..--g7`) · F14 已隔到装饰区 (Masthead)

**理由**: Sprint 2 单 worker 0.5w 不够做整个 frontend 视觉重塑 · 推 Sprint 3 跟
Gemini design phase 一起做 · 一致性更好。

---

## 2. Sprint 3 完整 checklist (Gemini design phase)

### 2.1 字体栈大重塑 (~1 周)

- [ ] tokens.css `--display` / `--sans` / `--cjk` default 改 `var(--inter), var(--pingfang), system-ui`
- [ ] tokens.css `--italic` 删手写斜体 default · 替 `var(--inter)` 普通 (Gemini 反斜体装饰)
- [ ] tailwind.config.ts (或 web/postcss.config) `theme.fontFamily.serif/sans/mono` 同步
- [ ] grep 全 web/src `<em>` `<i>` `font-style: italic` · 视情况删或保留 (mockup 装饰例外保留)
- [ ] grep 全 web/src `font-family: var(--italic)` · 替成 `var(--sans)` 或保留 (mockup 装饰例外)
- [ ] layout.tsx `next/font` import 字体减 (Funnel Display / Instrument Serif 删 · Inter / Noto SC 保留)

### 2.2 圆角收敛 ≤ 8px (~0.3 周)

- [ ] grep 全 web/src/app `border-radius: 18px|26px|999px` · 评估是否改 `var(--r-sharp)` 8px
- [ ] 例外保留: mockup 设计的 pill (`.shell-tabs` `border-radius: 999px`) · 视觉装饰 `card.warm` 等
- [ ] tokens.css `--r-md` 18px 和 `--r-lg` 26px 是否撤 (跟 Gemini 协商 · 替 `--r-sharp` 8px / `--r-md` 6px / `--r-lg` 12px)

### 2.3 F1c mock 中文术语 (~0.5-1 周)

- [ ] `web/src/lib/mock/agent-credit-session.ts` (4 type def + ~30 amount entry · `string "X 万"` → `number`)
- [ ] `web/src/lib/mock/agent-alert-sessions.ts` (1 type def + ~50 amount entry)
- [ ] `web/src/lib/mock/agent-report-session.ts` (1 type def + 1 amount entry · L647)
- [ ] `web/src/lib/mock/dispatch.ts` / `today.ts` / `warroom.ts` / `desk.ts` 检查 + 改
- [ ] `web/src/lib/mock/agent-channel-sessions.ts` / `agent-compliance-session.ts` 检查
- [ ] `web/src/lib/mock/archive.ts` 检查
- [ ] consumer 4 view + 6 workspace 内 amount 渲染统一用 `formatCurrencyWan(n, { fractionDigits: 0 })`
- [ ] type definition 4 处 (`amount: string` → `amount: number`) · TypeScript 严格 · CI 阻断 type error

### 2.4 4 view + 6 workspace 数字 cell 严格右对齐

- [ ] grep 全 view/workspace 含 `<td>` / `<div className="kv">` 或类似数字 cell
- [ ] 给 cell 加 `className="num-right"` (V4 plan F1 已有 utility 在 globals.css)
- [ ] 表格列头同对齐 (`<th>` 加 `text-align: right` 或 className)

### 2.5 grep 验收

- [ ] `grep -r "var(--italic)" web/src` 0 命中 (除 mockup 装饰例外)
- [ ] `grep -rn 'amount: "' web/src/lib/mock` 0 命中
- [ ] `grep -rn "border-radius: 18px\|border-radius: 26px" web/src/app` ≤ 5 命中 (mockup 例外)
- [ ] `npx tsc --noEmit` 0 错
- [ ] `npx next build` ✓ 18 routes 全 prerender

---

## 3. 工程量 + 排期

| 子任务 | 工程量 | 责任 |
|---|---|---|
| 2.1 字体栈大重塑 | 1 周 | Sprint 3 worker-B3 (Gemini design 协同) |
| 2.2 圆角收敛 | 0.3 周 | 同上 |
| 2.3 F1c mock 重塑 | 0.5-1 周 | 同上 |
| 2.4 数字 cell 右对齐 | 0.3 周 | 同上 |
| 2.5 grep 验收 + smoke | 0.2 周 | 同上 |

**Sprint 3 总工程量**: ~2.3-3 周 (跟 V4 plan F12 0.5 周原估超 5x · 因为含 F1c 真重塑)

PM 拍板: Sprint 3 单独跑 F12+F1c 大重塑 (Gemini design phase) OR 拆 Sprint 3+4 接力。

---

## 4. Sign-off

- Sprint 2 (worker-B3) ship: tokens.css 字体栈 + `--r-sharp` token (基础设施)
- Sprint 3 (worker-B3 ?) plan: 本 doc 5 子任务 · 完整重塑
- 拍板待 PM: Sprint 3 启动时机 + 是否拆 Sprint 3+4
