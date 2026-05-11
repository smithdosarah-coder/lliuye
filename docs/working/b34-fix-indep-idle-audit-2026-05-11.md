# B.3.4 fix-indep · 主活B-2 · 6 workspace idle 3-slot 合规审计

**Worker**: fix-indep · feat/b34-fix-indep
**Date**: 2026-05-11
**审计标准**: PM 真意 verbatim — "共享原则: **主 CTA + 占位 + 完成后显啥提示**"

## 审计方法

- 静态 grep `_components/*Workspace.tsx` 找:
  - 主 CTA: `data-testid="*-cta"` + `data-cta="primary"`
  - 占位卡: `data-testid="*-empty-skeleton"` / `*-placeholder` / `*-skel-card`
  - 完成后 hint: 文本 grep `完成后` / `启动后` / `...后此处显示` / `通过后` / `解析后`

## 6 workspace 现状 (2026-05-11)

| Agent | 主 CTA testid | 占位结构 | 完成后 hint | Verdict |
|---|---|---|---|---|
| **alert** | `alert-scan-cta` (primary) + `alert-scan-cta-secondary` | `alert-empty-skeleton-panels` (3 灯卡 + hitlist + signalmap skel) + 主活A 新 `alert-idle-mid-overview` (started=yes idle) | "扫描完显示户数 + TOP 1 客户" / "扫描完显示行业 × 信号类型分布" + 主活A "扫描已完成 · 选客户查看 drill" | ✅ COMPLIANT |
| **channel** | `start-scan-cta` + `channel-empty-quick` (3 chip) | ⚠️ 仅 form-card 描述 input · 无 **result-shape skeleton** | ⚠️ 描述是 input/process ("9 维评分 · 字段级溯源") · 缺**显式** "完成后此处显示..." | **GAP × 1** |
| **credit** | `credit-decision-cta` (primary) + `credit-demo-cta` | `credit-empty-skeleton-panels` (含 hero + 4 维评分 skel) | "决策完成后此处显示 4 维评分 · 红线明细 · 相似案例 · 决策建议书" (line 654) + "起决策完成后显示决策结论 / 额度 / 期限 / 利率" (line 2104) | ✅ COMPLIANT |
| **report** | `report-upload-cta` + `report-upload-template-cta` | ⚠️ 无 visual skel-card · 仅 4-bullet 描述 (line 2306-2323) | ✅ "材料解析后此处显示 5 类槽位计数" / "章节流式生成 · 4 chapter 渐进渲染" / "QC 9 维评分 · 通过后可导出 Word" (line 2319-2322) | ⚠️ PARTIAL (bullet 已含 hint · 仅缺 visual skel) |
| **compliance** | `compli-policy-scan-cta` (primary) + `compli-template-check-cta` (secondary) | `compli-empty-skeleton` + `compli-detail-placeholder` | "扫描完成后此处显示最新 3 条事件" (line 968) + "完成后可一键导出 Word" (line 977) | ✅ COMPLIANT |
| **riskctrl** | `riskctrl-dsl-gen-cta` (primary) + `riskctrl-demo-run-cta` | `riskctrl-empty-skeleton` + `riskctrl-recent-empty` | "回测报告导出 · 完成后可一键导出 Word / Excel / PDF" (line 789) | ✅ COMPLIANT |

## Verdict 汇总

- ✅ COMPLIANT (4): alert · credit · compliance · riskctrl
- ⚠️ PARTIAL (1): report (有 hint · 缺 visual skel · 不致命 · bullet 已交代将显啥)
- ❌ GAP (1): channel (缺显式完成后 hint)

## 修补决策 (R3 fix-forward budget · 仅修真 GAP)

### channel GAP fix (本批必修)

加一个 `<p data-testid="channel-completion-hint">` 在 channel-empty-state section 末尾 ·
明示完成后 result UI shape: "搜索完成后此处显示候选企业卡 · 9 维评分 + 字段级溯源 evidence drawer + 多源信号 timeline".

预期 diff: `web/src/app/archive/channel/_components/ChannelWorkspace.tsx`
+ ~10 LOC inline style + 1 段文字.

### report PARTIAL (本批跳过 · 不修)

理由:
- 4-bullet 已交代每个阶段后会显啥 (材料解析后 / 章节流式 / QC 9 维 / 审批意见回写)
- 加 visual skel-card 收益边际 · 增加 200+ LOC + 破 report-empty-state.spec.ts 风险高
- R3 fix-forward budget · 不烧 budget 修非真问题
- 标 PARTIAL 留 audit trail · future iter 可补 (next sprint candidate)

### alert · credit · compliance · riskctrl

无改 · 这 4 个已 COMPLIANT.

## IdleScaffold (主活B-1) 适用性

新代码用 IdleScaffold 强制 3-slot · 老代码不强迁:
- alert started=yes idle (主活A 已自填) · 不迁
- alert AlertEmptyState (started=no) · 已富 · 不迁
- 5 其他 workspace · 已审过 *-empty-state.spec.ts · 不迁

IdleScaffold 价值: 防 future Agent / future idle state 再写时再现 PM 截图痛 #4
(只一行文字占满空白). 强 contract 阻止 0 占位卡 / 0 hint 的 idle.

## 验收硬线

- [x] 6 workspace 全审 (本 doc)
- [x] 真 GAP 列出 (channel × 1)
- [ ] channel GAP fix commit (主活B-2 next step)
- [x] PARTIAL 不修理由记录 (report)

## Cross-reference

- 主活B-1 commit (IdleScaffold): `f49d122`
- 主活A-2 commit (alert idle 实现): `2e18eb0`
- onboarding: `docs/onboarding/B.3.4-mesh-onboarding.md`
- IdleScaffold spec: `web/src/app/archive/_shared/IdleScaffold.tsx`
