# CSS 命名 SSOT · v1/v2 alias 与 universal override 规则

> 2026-05-21 沉淀 · 防 v1/v2 命名漏覆盖坑（report layout bug 已踩 3 次：4/22 / 5/11 / 5/21）

## 背景

历史原因导致 archive workspace CSS 命名分为 v1 / v2 两套：

| v1 命名（report / channel 用） | v2 命名（credit / alert / compliance 用） | 责任 |
|---|---|---|
| `.rpt-body` | `.rpt-grid` | 3 列 grid 容器 |
| `.rpt-main` | `.rpt-col--mid` | 中栏对话主轴 |
| `.rpt-side` | `.rpt-col--left` | 左栏导航 |
| `.rpt-aux` | `.rpt-col--right` | 右栏预览 |

**历史溯源**：
- v1 (canon 旧 dash 命名): 2026-04-21 redesign 时 report/channel 用
- v2 (CLI-B 2026-04-22 重设计 BEM 风): credit/alert/compliance workspace 用新命名但漏了 grid CSS 定义，三个页面 panel 全部塌成 block 流 → 补 v2 alias 到 `report-workspace.css:202-239`

两套并存，互不覆盖。

## 规则

### 规则 1 · universal override 必须 cover 两套 alias

`web/src/app/archive/_shared/idle-tight.css` 是跨 6 workspace 的 universal layout override。
**任何 selector 写 v2 命名时必须同时写 v1 alias**（反之亦然）。

✅ **正例**：

```css
.v-archive--canon .rpt-grid,
.v-archive--canon .rpt-body {
  min-height: auto !important;
}
```

❌ **反例**（2026-05-21 report layout bug 真因）：

```css
.v-archive--canon .rpt-grid {  /* 漏 .rpt-body · report workspace 不生效 */
  min-height: auto !important;
}
```

### 规则 2 · lint 自动验证

每次改 `idle-tight.css` 跑：

```bash
bash scripts/lint/css_universal_override_check.sh
```

报 `[✗ FAIL]` 必须修才能 commit。

建议集成：
- pre-commit hook
- CI on PR change to `idle-tight.css` 或 `*Workspace.tsx`

### 规则 3 · 添加新 alias 必须同步本 SSOT

如果引入新的 v1/v2 alias 对（例如新增 panel 类型），必须：
1. 更新本文档表格
2. 更新 `scripts/lint/css_universal_override_check.sh` 的 `V2_NAMES` / `V1_NAMES` 数组
3. 同步 `report-workspace.css` 的 v1/v2 alias 定义

## 长期收口路径（ROI #4 真治本，未做）

最终目标：**删 v1 alias，统一到 v2 命名**。需要：

1. ReportWorkspace.tsx / ChannelWorkspace.tsx 改 `className="rpt-body"` → `"rpt-grid"`（含 `.rpt-main` / `.rpt-side` / `.rpt-aux` 全替换）
2. 删 `report-workspace.css` 里 v1 定义（行 181-200 + 599-630）
3. 删本 SSOT 文档（命名收口后就不需要这层 alias 治理）
4. 删 `scripts/lint/css_universal_override_check.sh`（无 alias 漂移可 lint）

工作量估计：≥ 1 sprint（涉及 2 个 3000+ 行 workspace 改造 + 全面回归）

**当前为止只做了临时止血**（universal override patch）+ lint 防再坑，**未做命名收口治本**。

## 当前状态（2026-05-21）

| 项 | 状态 |
|---|---|
| v1 命名（report / channel） | 🟡 仍在用 |
| v2 命名（credit / alert / compliance） | 🟢 在用 |
| `idle-tight.css` universal override v1/v2 cover | ✅ 已同步（commit `b1ce51a`） |
| lint script | ✅ 已就位（commit TBD） |
| SSOT 文档 | ✅ 本文件（commit TBD） |
| 长期命名收口（删 v1） | ❌ 未做（≥ 1 sprint） |

## 历史踩坑

| 时间 | 事件 | 病灶 |
|---|---|---|
| 2026-04-22 | 创 v2 命名时未做 alias 镜像 → credit/alert/compliance panel 塌成 block 流 → 补 v2 alias 到 `report-workspace.css` | 没立 SSOT |
| 2026-05-11 | PM 7 截图大空白真痛 → `idle-tight.css` universal override (commit `76b04bf` 起多轮) → 但只 cover v2 | 第 2 次踩同坑 |
| 2026-05-21 | PM 真号 dogfooding 抓 report layout bug → v1 漏 cover → patch `idle-tight.css` 补 v1 alias (commit `b1ce51a`) + 立本 SSOT + lint | 第 3 次踩同坑 → 才立规则 |

这是 5/10 复盘 §4 "事后反应式机制"的活体复发。本次 SSOT + lint 才把它转成"前置防御式"。

## 配套文件

- `scripts/lint/css_universal_override_check.sh` — lint 验证脚本
- `web/src/app/archive/_shared/idle-tight.css` — universal override（按本 SSOT 维护）
- `web/src/app/archive/report/report-workspace.css` — v1 + v2 alias 兼容定义（行 181-239）
- 6 workspace TSX 文件：
  - `web/src/app/archive/report/_components/ReportWorkspace.tsx`（v1）
  - `web/src/app/archive/channel/_components/ChannelWorkspace.tsx`（v1）
  - `web/src/app/archive/credit/_components/CreditWorkspace.tsx`（v2）
  - `web/src/app/archive/alert/_components/AlertWorkspace.tsx`（v2）
  - `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx`（v2）
  - `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx`（待 verify v1 还是 v2）

## 关联 wiki

- `D:/second-brain/wiki/questions/2026-05-21-report-layout-bug.md` — bug 详细诊断
- `D:/second-brain/wiki/concepts/Agent 矩阵工程实践原则.md` — "事后反应式机制" 病灶
