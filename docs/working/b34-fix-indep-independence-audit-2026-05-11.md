# B.3.4 fix-indep · 主活D · 6 助手独立可用 audit

**Worker**: fix-indep · feat/b34-fix-indep
**Date**: 2026-05-11
**审计标准**: PM 真意 verbatim — "6 助手独立可用 (default 演示模式 · 不显'等别人')"

## 审计方法

grep 6 workspace `_components/*Workspace.tsx` 找:
- 真"等别人 agent": `等 (Agent[1-6]|报告|授信|获客|预警|合规)` / `推过来` / `推送来` / `从.*起决策`
- 区分:
  - "等待用户操作" (user-driven · 保留)
  - "等待 X agent 回写" (cross-agent dependency · 软化或翻 default)

## 6 workspace 现状 (2026-05-11)

| Agent | "等待"类文字 | 真"等别人"? | 处理 |
|---|---|---|---|
| **alert** | "等待启动" / "等待主操作" / "等待对话开始" | ❌ 全是"等用户操作" | 0 改 |
| **channel** | "等待业务诉求 · 输入诉求开始..." | ❌ 等用户输入 | 0 改 |
| **credit** | "等待 Agent6 报告 handoff" (generateSteps) + "从 Agent6 报告起决策" (real CTA) + default `inputMode="real"` | ⚠️ **真"等别人"** + default 入口卡死路径 | **本批修** |
| **report** | "等待触发" (idle) | ❌ 等用户上传 | 0 改 |
| **compliance** | "等待触发巡检" / "尚未触发巡检 · 等待用户输入" | ❌ 等用户输入 | 0 改 |
| **riskctrl** | "等待真路径触发" / "等待触发策略" | ❌ 等用户输入 | 0 改 |

## 修补 (本批 · credit 唯一真问题)

### 1. generateSteps 首步软化 (UX 文字 · 不变行为)

**Before**:
```tsx
{ label: "等待 Agent6 报告 handoff", pct: 22 },
```

**After**:
```tsx
{ label: "装载 ReportJSON · Agent6 / 内置 sample 二选一", pct: 22 },
```

理由: 反映 inputMode toggle 现实 (real → Agent6 / demo → 内置 sample · backend 都真跑) ·
不显"等别人 agent 推过来"的卡死暗示 · credit 可独立跑 demo 模式.

### 2. default inputMode 翻 real → demo (default 演示模式)

**Before**:
```tsx
const [inputMode, setInputMode] = useState<CreditInputMode>("real");
```

**After**:
```tsx
const [inputMode, setInputMode] = useState<CreditInputMode>("demo");
```

理由: PM 真意 "6 助手独立可用 (default 演示模式)". credit 单 agent 演示无需
Agent6 handoff 前置 · 真后端跑内置 sample. 用户切 "real" tab 后仍可走 Agent6
handoff 路径 · 不破坏功能 · 仅默认入口换.

**风险评估**:
- credit-empty-state.spec / credit-pilot-4gate.spec 不直接断言 default `inputMode` (grep 验证)
- 代码路径 `inputMode === "real"` 仍可走 (用户手动切)
- E2E 跑 demo CTA 时无前置依赖

## 不修 (其他 5 workspace · 已独立可用)

alert · channel · report · compliance · riskctrl 已无"等别人 agent"硬编 hint ·
全部"等待"措辞都是"等用户操作" · 0 改动.

## 真 contract dependency 保留 (反 over-fix)

虽 default 切 demo · 但 real 路径仍保留 · 因为它是真业务依赖:
- credit 真跑 = 消费 Agent6 ReportJSON (per Agent3 spec · BE2 evidence graph)
- 这是后端 contract · UI 不能假装无依赖

修法仅是: **default 入口换 + UX 文字软化** · 不删 contract dependency · 不改后端.

## 验收硬线

- [x] 6 workspace 全审 (本 doc)
- [x] credit "等待 Agent6" 软化 (generateSteps)
- [x] credit default `inputMode` 翻 "demo"
- [x] 其他 5 workspace 0 改 (已合规)
- [x] 后端 contract dependency 保留 (real 路径仍可用)

## Cross-reference

- B-2 audit: `docs/working/b34-fix-indep-idle-audit-2026-05-11.md`
- C audit: `docs/working/b34-fix-indep-button-audit-2026-05-11.md`
- onboarding: `docs/onboarding/B.3.4-mesh-onboarding.md`
- Agent3 真 contract: `docs/contracts/agent-credit-decision-graph.md` v1.0
