# B.4 SLO-3 · 36 bug 跟踪 (fix-indep worker)

**Worker**: fix-indep · feat/b34-fix-indep
**Date**: 2026-05-11 (PM 12:55 GO)
**Base**: origin/main `59d32fd` (含主 CLI C1-C4 通病 `9578c98`)
**总计**: 36 bug = 33 真修 + 3 verify-only (主 CLI C2/C4 已覆盖)

## 主 CLI 已修通病 (`9578c98` · `web/src/app/archive/_shared/idle-tight.css`)
- **C1** viewport 下半 ground gradient 大空白 → `.v-archive--canon` min-height calc(100vh - 64px) flex col
- **C2** panel max-width 不够 → `.rpt-workspace` width 100%
- **C3** stats 跟 hero ~1000px 空白 → hero gap 16px
- **C4** 占位卡 grid 不平衡 → 2x2 grid + padding 减半

## 我的修复路线
- **优先 shared CSS** (`_shared/idle-tight.css`) · 1 处影响全局 · 不动 workspace.tsx 结构
- **必要时局部 CSS** (`<agent>-workspace.css`) · 仅 agent 特殊情况
- **避免动 TSX** · 除非必须 (e.g. 状态条缺补 / panel 结构错位)
- **commit 粒度** = 1 bug 1 commit · per PM 硬要求

## 36 bug 清单 · 状态

### channel (5 bug · ✅ 全 ship)

| # | bug | 文件/区域 | 状态 | commit |
|---|---|---|---|---|
| 1 | KB 知识库上传 3 panel 排版乱 | channel-workspace.css · `.ch-kb-zone` 等高 | ✅ done | `722a904` |
| 2 | QUERY panel 跟 KB panel 间距不一致 | channel-workspace.css · `.ch-querybar` padding 18/22 + margin 18/0 | ✅ done | `f610bab` |
| 3 | 自由查询 / 一键示例 toggle 字号不一致 | ChannelWorkspace.tsx inline · fontWeight 500 统一 | ✅ done | `7409e55` |
| 4 | "搜索完成后此处显示候选企业卡..." 单行浮 | ChannelWorkspace.tsx · `<p>` → `<div>` 完整卡片 | ✅ done | `afa04e0` |
| 5 | 形态 A / 形态 B 2 panel 跟上下不对齐 | ChannelWorkspace.tsx inline · padding 18/22 + margin 18/0 | ✅ done | `58072f5` |

### credit (6 bug · ✅ 全 ship · bug-3 真修 · 非 verify-only)

| # | bug | 文件/区域 | 状态 | commit |
|---|---|---|---|---|
| 1 | 板块 toggle (对公/普惠/对私) + AGENT eyebrow 上下错位 | credit-workspace.css · tabs absolute top-right + hero padding-right 240 | ✅ done | `f3d3901` |
| 2 | 演示数据 panel 横向只占 60% · 右 40% 空 | credit-workspace.css · cta-row + cta width 100% | ✅ done | `3ef8b57` |
| 3 | 4 占位卡 grid 3+1 → 2x2 | credit-workspace.css · skel-row display:contents (C4 真生效) | ✅ done | `baf45f6` |
| 4 | 决策建议书 panel 占整行 · 内容只 1 行 | credit-workspace.css · --wide grid-column auto · 单 cell | ✅ done | `2ccff44` |
| 5 | 状态条飘左 · 右大块空 | credit-workspace.css · status-item--demo margin-left auto | ✅ done | `4ba8bab` |
| 6 | "导出 .docx (待决策完成启用)" 飘右 · 字突兀 | CreditWorkspace.tsx + credit-workspace.css · 独立 .skel-cta-row | ✅ done | `8dcab76` |

### alert (7 bug · ✅ 全 ship)

| # | bug | 文件/区域 | 状态 | commit |
|---|---|---|---|---|
| 1 | 2 行 2 列 panel 占 60% · 右 30% 空 | alert-workspace.css · cta-row 3 cols → 2 cols | ✅ done | `49c4c3d` |
| 2 | 3 档预览 (红/黄/绿) 横向均分但没填满整宽 | alert-workspace.css · skel-traffic width 100% | ✅ done | `16cc6be` |
| 3 | HitList panel 跟上方 60% panel 不一致 | alert-workspace.css · skel-row width 100% (HitList + SignalMap 共用) | ✅ done | `7a17892` |
| 4 | SignalMap panel 同样不一致 | alert-workspace.css · signalmap+hitlist min-height 120 | ✅ done | `9af1d9f` |
| 5 | 状态条横向占满但内容飘左 | alert-workspace.css · status-item--demo margin-left auto | ✅ done | `260612e` |
| 6 | HitList 内容很短 · 中间右边都空 | AlertWorkspace.tsx + css · 加 2 slot 占位行 (TOP 1 红/黄) | ✅ done | `d020388` |
| 7 | "导出榜单 .docx (待扫描完成启用)" 字突兀 | AlertWorkspace.tsx + css · btn 移出 hint · 独立 .skel-cta-row | ✅ done | `33425c1` |

### compliance (6 bug · ✅ 全 ship)

| # | bug | 文件/区域 | 状态 | commit |
|---|---|---|---|---|
| 1 | hero 跟 stats 间 ~1000px 巨大空白 | compliance-workspace.css · rpt-hero grid 1fr auto · eyebrow/title/sub 左列 + stats 右列 | ✅ done | `3a0c4ae` |
| 2 | stats "000" 像孤字 (3 零意义不清) | compliance-workspace.css · rpt-hero__qc-chip tone bg/border/color 定义 | ✅ done | `c59566e` |
| 3 | stats 4 数字飘右上 · 不知啥意思 | compliance-workspace.css · dt 字号 11/0.08em + dd 18 + stat left border | ✅ done | `8fadde0` |
| 4 | "用模板快速比对" 小 button 孤飘左 | compliance-workspace.css · bar width 100% + ::before 上下文 label | ✅ done | `936921d` |
| 5 | 4 占位卡 padding 浪费 | compliance-workspace.css · padding 28/18 → 14/16 + min-height 88 → 72 | ✅ done | `4522bb0` |
| 6 | "等待触发巡检" panel 引导文字飘左 | compliance-workspace.css · hint text-align center | ✅ done | `e2a768c` |

### report (6 bug)

| # | bug | 文件/区域 | 状态 | commit |
|---|---|---|---|---|
| 1 | stats 3 破折号孤飘右上 · 字突兀 | report-workspace.css · stats label 显式 | pending | — |
| 2 | "等待触发" panel 中间 500-600px 巨大空白 | report-workspace.css · panel padding/min-height | pending | — |
| 3 | "真 LLM (DeepSeek) + 真 9 维 QC..." 飘右 · 不对齐 sample button | report-workspace.css · 同行 align | pending | — |
| 4 | "PDF / Word / Excel / 图片 / 多文件" 5 标签间距不一致 | report-workspace.css · `.rp-tag-*` gap uniform | pending | — |
| 5 | "上传自定义模板 或 选预制" 飘左 · 跟"开始生成" button 不同行 | report-workspace.css · same row | pending | — |
| 6 | 5 个 sample button 横向占 70% · 右 30% 空 | report-workspace.css · button row width 100% | pending | — |

### riskctrl (6 bug · 2 verify)

| # | bug | 文件/区域 | 状态 | commit |
|---|---|---|---|---|
| 1 | stats 飘右上 · 跟 hero 间空白 | riskctrl-workspace.css · stats layout | pending | — |
| 2 | 4 占位卡 2x2 (C4 已修 · verify) | _shared/idle-tight.css C4 | verify-only | — |
| 3 | "等待触发策略" panel 占 1 整行但短文 | riskctrl-workspace.css · panel min-height/content stretch | pending | — |
| 4 | 真实/演示 toggle 在左 · 主 CTA 在中 · 不同行 | riskctrl-workspace.css · `.rc-mode-toggle` 同行 | pending | — |
| 5 | 整页只占左 70% · 右 30% 空 (C2 已修 · verify) | _shared/idle-tight.css C2 | verify-only | — |
| 6 | 状态条没显 (跟其他 5 助手不一致 · 应补) | RiskctrlWorkspace.tsx · 加状态条 | pending | — |

## 完成 SLA
- 每 bug → 1 commit (PM 硬要求)
- 每 agent done → fire `STEP-<AGENT>-BUG-FIXED` signal
- 全 6 agent → fire `WORKER-SLO-3-36-BUG-FIXED-READY-FOR-MERGE`
- artifacts: `selfreview-<agent>-idle.jpg` after 截图 · 入 `docs/evidence/b4-slo3-2026-05-11/`
- BLOCKER → 立刻 fire `Signal:BLOCKED`

## Cross-reference
- 主 CLI dispatch commit: `59d32fd`
- 主 CLI C1-C4 通病: `9578c98`
- 主 CLI before 截图: `D:/claude code/credit_report_agent_work/selfreview-{channel,credit,alert,compliance,report,riskctrl}-idle.jpg` (02:45-02:49)
- B.3.4 fix-indep PM 真意 (沿用): 主 CTA + 占位 + 完成后显啥提示 三件套
