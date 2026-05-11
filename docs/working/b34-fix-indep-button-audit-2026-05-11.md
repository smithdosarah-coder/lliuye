# B.3.4 fix-indep · 主活C · 6 workspace 主按钮简化审计

**Worker**: fix-indep · feat/b34-fix-indep
**Date**: 2026-05-11
**审计标准**: PM 真意 verbatim — "主按钮简化 (1 主 + 1 次 · 删多余 toggle · Phase A.6/B.1 ModePill 残留已经被 B.1.x revert · 现剩的 toggle 也要砍到 minimum)"

## 审计方法

grep 6 workspace `_components/*Workspace.tsx`:
- `data-testid="*-cta"` / `*-btn` / `*-button` (CTA 类)
- `data-testid="*-toggle"` / `*-mode` / `*-switch"` (toggle 类)

按 idle CTA row 范围分类 (排除 post-state action: export / drill / refine / approve).

## 6 workspace idle CTA + toggle 现状 (2026-05-11)

| Agent | 主 CTA | 次 CTA | 必要 toggle (PM B.2 reframe 拍板) | 多余? |
|---|---|---|---|---|
| **alert** | `alert-scan-cta` (primary) | `alert-scan-cta-secondary` (选规则集) | `alert-input-mode-toggle` (live/demo · 形态切换 · 输入来源切换 不是真假切换) | ❌ 无多余 · 1 主 + 1 次 + 1 必 toggle |
| **channel** | `start-scan-cta` (隐 · 搜索框 ENTER) | (none · 一键示例 在 tab 里) | `channel-conversation-toggle` (会话折叠/展开 · 非 CTA · UI affordance) | ❌ 无多余 · 1 主 + 0 次 + 1 UI affordance |
| **credit** | `credit-decision-cta` (primary) | `credit-demo-cta` (演示模式) | `credit-input-mode-toggle` (real/demo · B.2 reframe) | ❌ 无多余 · 1 主 + 1 次 + 1 必 toggle |
| **report** | `report-upload-cta` | `report-upload-template-cta` | (none · 无 input-mode · upload 即真路径) | ❌ 无多余 · 1 主 + 1 次 + 0 toggle |
| **compliance** | `compli-policy-scan-cta` (primary) | `compli-template-check-cta` (secondary) | `compli-input-source-toggle` (B.2 reframe) | ❌ 无多余 · 1 主 + 1 次 + 1 必 toggle |
| **riskctrl** | `riskctrl-dsl-gen-cta` (primary) | `riskctrl-demo-run-cta` (secondary) | `riskctrl-mode-toggle` (real/demo · B.2 reframe) | ❌ 无多余 · 1 主 + 1 次 + 1 必 toggle |

## Verdict

**6/6 workspace 已合规** — 1 主 + 1 次 + 必要 toggle. **无可删 button/toggle**.

历史包袱 (Phase A.6/B.1 ModePill 残留) 已被 B.1.x hotfix 全部 revert (见 git log
hotfix B.1.4 等). 现剩的 toggle (input-mode / input-source / mode-toggle) 是 PM
ALL IN Phase B.2 真意 reframe 拍板保留的"输入来源切换" — **不是 mock vs live 切换** ·
backend 都真跑 · 仅输入来源不同. 删它即破 PM 拍板. 不删.

## post-state action button (非 CTA row · 不在简化范围)

排除以下 (post-state · 各自必要):
- `*-export-docx-btn` × 4 (alert/credit/compliance/riskctrl) — 完成后导出 · 必有
- `*-drill-cta` × 1 (alert) — drill drawer 入口 · 必有
- `*-refine-btn` × 1 (report) — 章节精修 · 必有
- `*-apply-launch-btn` / `*-generate-btn` (report) — pipeline 阶段控制 · 必有
- `*-violation-card-btn` (compliance) — 卡片级 drill · 必有

## 修补决策

**0 改动** — 6/6 已合规 · R3 fix-forward budget 不烧.

留 audit trail · future PR 加新 CTA 必复审本表 · 防 Phase A.6 ModePill 类残留再生长.

## 工程红线 (future code 必读)

- 任何新 idle CTA row 必须 ≤ 1 主 + 1 次
- 任何新 toggle 必须**显式区分** "输入来源" vs "mock/live data switch":
  - "输入来源 toggle" (e.g. live 客户经理上传 vs demo 内部 batch · backend 都真跑) — 允许
  - "mock/live data switch" (e.g. 切 ModePill 显假数据) — **禁止** · PM B.1.x revert 红线
- toggle 必带 `data-testid` 且 `aria-pressed` 反映状态

## Cross-reference

- B-2 audit: `docs/working/b34-fix-indep-idle-audit-2026-05-11.md`
- B-1 IdleScaffold: `web/src/app/archive/_shared/IdleScaffold.tsx`
- ALL IN Phase B.2 reframe (B.1.x revert chain):
  - hotfix B.1.4 commit `b682f88`
  - alert B.2 step 4 commit `64f8951` (字段级 evidence drawer)
  - credit B.2 step 4 commit `503b159` (字段级溯源)
- onboarding: `docs/onboarding/B.3.4-mesh-onboarding.md`
