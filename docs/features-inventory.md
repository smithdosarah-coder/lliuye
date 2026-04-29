# Features Inventory · 已交付前端 feature 清单

> **目的**：防回档。worker 派活前必读·改动后必须在 commit trailer 列 `PRESERVES: F-XXX` 声明保留。
> **约束**：本清单是 worker 改 `web/` 的 contract——任何改动都不能破坏已列 feature·破坏视作 regression。
> **生成于**：2026-04-27·基于 6 个回档 bug 反推首批 entries。后续每修一个 bug / 上线一个新 feature 必须 enrich。

## 模板

```yaml
F-XXX · <短标题>
location: <主文件路径> + 引用点
selector: <DOM data-testid 或类名>
interaction: <一句话描述用户操作 → 系统响应>
introduce: <commit_hash>  <YYYY-MM-DD>  <commit subject 摘要>
lost_at: <commit_hash 或 N/A>
restored: <commit_hash 或 pending>
smoke_test: <web/tests/regression/*.spec.ts 路径·没写就标 pending>
```

---

## F-001 · 退出登录按钮

- **location**: `web/src/components/shell/LogoutButton.tsx` + 引用于 `Masthead.tsx` / `PersonaSwitcher.tsx`
- **selector**: `[data-testid="logout-button"]`（待 cherry-pick 后确认）
- **interaction**: click → `store.logout()` → redirect `/login`
- **introduce**: `05fafcd` 2026-04-23「退出登录 pill · 画布/主题双 pill 对齐」
- **lost_at**: `63107fb` 2026-04-26「Stage 1 · file-snapshot 8 文件」LogoutButton.tsx 文件被删
- **restored**: pending（Phase C.1 cherry-pick `05fafcd`）
- **smoke_test**: `web/tests/regression/logout.spec.ts` pending

## F-002 · 画布开关 pill（CanvasModeToggle）

- **location**: `web/src/components/shell/CanvasModeToggle.tsx`·引用于 `AppShell.tsx`
- **selector**: `[data-testid="canvas-mode-toggle"]`
- **interaction**: click → 切换 `panel-canvas` ↔ `free-drag` mode
- **introduce**: `63107fb` 2026-04-26（毛玻璃）+ `05fafcd` 2026-04-23（双 pill 对齐）
- **lost_at**: `315de1e` 2026-04-22 revert 把 motion tokens 删了·样式降级
- **restored**: pending（Phase C.2）
- **smoke_test**: `web/tests/regression/canvas-toggle.spec.ts` pending

## F-003 · 主题切换 pill（ThemeSwitch · 4 主题）

- **location**: `web/src/components/shell/ThemeSwitch.tsx`
- **selector**: `[data-testid="theme-switch-{canvas|matcha|dusk|ink}"]` × 4
- **interaction**: click theme → set `data-theme` on `<html>` → 切换 4 主题渐变（**不含已下架的 Letterpress / Nebula**）
- **introduce**: 同 F-002（双 pill 升级）
- **lost_at**: 同 F-002（token 降级）
- **restored**: pending（Phase C.2）
- **smoke_test**: `web/tests/regression/theme-switch.spec.ts` pending

## F-004 · Forge（Agent2 风控）Workspace · ScanCTA 触发按钮

- **location**: `web/src/components/shared/ScanCTA.tsx` + `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx`
- **selector**: ScanCTA 内的 `<button>` 触发回测
- **interaction**: click → POST `/api/run/riskctrl`（multiplexer endpoint）→ SSE 流式更新进度
- **introduce**: `ffc60ca` 2026-04-23「5 agent workspace 共享 ScanCTA · 补齐过程感演示」
- **lost_at**: `95437b6` 2026-04-26「Stage 3 微信气泡 + dispatch group/dm split」改了 ScanCTA `onDone` callback
- **restored**: pending（Phase C.3 对比版本 + 小修）
- **smoke_test**: `web/tests/regression/forge-trigger.spec.ts` pending

## F-005 · Scout（Agent1 获客）· 自由搜索标签

- **status**: 🔴 NEVER CORRECTLY DELIVERED·产品定位错·待重做
- **location**: `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` QueryBar 区 + `web/src/lib/mock/agent-channel-session.ts` query 部分
- **interaction (期望)**: 客户经理输入 / 组合 tag → 自由搜索企业·候选基于 tag 命中·**不是** look-alike 找相似
- **introduce (错版)**: `19b6d72` 2026-04-24 实现成 look-alike KB matcher（worker 误解产品定位）
- **regress**: `95437b6` 2026-04-26 placeholder 改为「标杆客户名 / 描述画像」·**仍是错的方向**
- **fix_path**: 重写 QueryBar + ScoutQuery 类型·spec 由 PM 提供后 implement·**不能 cherry-pick · 必须新做**
- **smoke_test**: `web/tests/regression/scout-tag-search.spec.ts`（重写后写）

## F-006 · ScoreRadar 8 维评分雷达图 · 毛玻璃样式

- **location**: `web/src/components/viz/ScoreRadar.tsx` + 各 Workspace 内引用（Scout / Forge / Credit）
- **interaction**: render 8 维 radar（该企业 vs 行业 P50）
- **introduce**: `3a20bdf` v14-v5 baseline 毛玻璃风格首次落地
- **lost_at**: 全局 token 降级（`315de1e` revert）间接波及·CSS 看起来是默认样式
- **restored**: pending（Phase C.5 手动 CSS 恢复）
- **smoke_test**: visual snapshot regression（pending）

## F-007 · Today 页 · 空白状态（不含 worker hallucinate 的 4 块）

- **location**: `web/src/app/today/page.tsx` + `web/src/components/today/Hero.tsx`
- **MUST NOT contain**:
  - PriorityQueue（今日队列 · Priority 5 客户清单）
  - EventTimeline（事件流 · Timeline）
  - 4 KPI 大数字（本月已放款 / 待签卷宗 / 观察名单 / 本周新政）
- **MUST contain**: 空白 hero + 「开始演示」CTA（PM 愿景·worker 自由发挥多了 4 块）
- **introduce (错版)**: `bc70e65` + `a82efe5` 2026-04-20 worker 加 PriorityQueue + EventTimeline
- **fixed_at**: `f1acf66` 2026-04-21 删除 import 和渲染（但 user 截图显示当前 production 还有这些 block·**ECS 跑的可能不是 chore/l0-infra**·待 verify）
- **fix_path**: verify `f1acf66` 是否在 ECS production·不在则 cherry-pick（Phase C.6）
- **smoke_test**: `web/tests/regression/today-empty.spec.ts` 验 DOM **不含** `[data-testid="today-priority-queue"]` / `today-event-timeline` / `today-kpi-belt`

## F-008 · 气泡拖拽到画布 → 缩略图卡片

- **location**: `web/src/components/dispatch/MessageBubble.tsx` + `web/src/components/shell/MessagePinHandle.tsx` + `web/src/app/dispatch/_store/dispatch-store.ts`
- **selector**: `[data-pin-handle="message"]` drag source · drop target Whiteboard
- **interaction**: dispatch 消息气泡 drag handle → 拖到 Whiteboard 区域 → 缩略图卡片渲染（thumbnail·**不是** url 链接）
- **MIME**: `PANEL_PIN_MIME` 双 MIME 拖柄（缩略图 logic 依赖此 MIME）
- **introduce**: `a5572b9` 2026-04-22「任务2 · MessagePinHandle · 双 MIME 拖柄」
- **lost_at**: `95437b6` 2026-04-26 dispatch-store.updateMessage 改·`refs` 字段移除·拖柄 onDragStart 逻辑改
- **restored**: pending（Phase C.7 cherry-pick `a5572b9` + verify dispatch-store 兼容）
- **smoke_test**: `web/tests/regression/bubble-drag-thumbnail.spec.ts` pending

---

## Press（Agent6 报告）Workspace · F-009 ~ F-014

## F-009 · Report Workspace · ScanCTA "生成报告" 5 步 pipeline

- **location**: `web/src/components/shared/ScanCTA.tsx` + `web/src/app/archive/report/_components/ReportWorkspace.tsx`（label="生成报告" · tone="report"）
- **selector**: `[data-view="archive-report"][data-scanned]` 容器 + ScanCTA 内 `<button>`·5 步 `[解析企业材料 OCR / 字段结构化预填 / 段落 Evidence-First 生成 / QC 终审占位符检查 / 导出 Word]`
- **interaction**: click → mock 5 步进度 → 末步 `setScanned(true)` 解锁 hero 数据 fade-in（与 F-004 共享组件·不同 label/tone/steps）
- **introduce**: `ffc60ca` 2026-04-23「5 agent workspace 共享 ScanCTA · 补齐过程感演示」+ `2b4f299` 2026-04-23「全 6 agent 统一空态 CTA」
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/report-scancta.spec.ts` pending（cross-link F-004）

## F-010 · Report 模板选择 + 覆盖率环（TemplatePanel）

- **location**: `web/src/app/archive/report/_components/ReportWorkspace.tsx` `TemplatePanel`
- **selector**: `.rpt-panel.rpt-panel--tpl` · `.rpt-tpl-card` · `.rpt-tpl-ring` SVG（`<circle.rpt-tpl-ring-fill>` + `<text.rpt-tpl-ring-pct>`）· `.rpt-tpl-avail-row` 切换列表
- **interaction**: 显当前模板 `cov.filled / cov.total` 覆盖率（dasharray 圈进度）+ 已填 / 标未填 / 总项 stats + 切换其他可选模板
- **introduce**: `f2aa949` 2026-04-24「rehome 6 Agent workspaces from feat/agent6-dialog-shell」（继承 P2 左栏三块实装）
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/report-template.spec.ts` pending

## F-011 · Report 材料拖拽上传 + 解析 grid（MaterialPanel）

- **location**: `web/src/app/archive/report/_components/ReportWorkspace.tsx` `MaterialPanel`
- **selector**: `.rpt-panel--mat` · `.rpt-mat-drop` 拖拽上传按钮 · `.rpt-mat-grid > .rpt-mat-card[data-k=<kind>]`（含 `.rpt-mat-dot.ok|pending` 解析态）· `.rpt-mat-link` linkedSections chip
- **interaction**: 拖拽 / 点击上传 pdf · docx · xlsx · img ≤ 30 MB → 解析 grid 渲染（每卡片显 kind / 页数 / 字节 / 解析备注 / 联动章节）
- **introduce**: `f2aa949` 2026-04-24 rehome 6 Agent workspaces
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/report-material-upload.spec.ts` pending

## F-012 · Report 时间流 Timeline · 8 类事件 + session 切换

- **location**: `web/src/app/archive/report/_components/ReportWorkspace.tsx` `TimelinePanel`
- **selector**: `.rpt-panel--tl` · `.rpt-tl-list > .rpt-tl-ev[data-prio]` · `.rpt-tl-switch` session 切换 select · 8 kinds: `template.select / material.upload / material.parsed / ai.question / user.reply / section.done / qc.run / export`
- **interaction**: 列出本 session 全部事件（按 priority 排序）·每 ev 显 kind / 时刻 / label / detail · 顶部 select 切 recentSessions
- **introduce**: `f2aa949` 2026-04-24 rehome 6 Agent workspaces
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/report-timeline.spec.ts` pending

## F-013 · Report A4 预览 + TOC + 字段 chip 3 态 + QC tooltip

- **location**: `web/src/app/archive/report/_components/ReportWorkspace.tsx` `PreviewPanel` + `SectionView` + `FieldChip`
- **selector**: `.rpt-pv-paper-wrap` A4 滚动容器 · `.rpt-pv-toc > button[data-status=<ok|needs-review|running|pending>]` · `.rpt-pv-fc[data-state=<filled|unfilled|uncertain>]` · `.rpt-pv-fc-qc[data-l=<block|warn|info>]` 内嵌 `.tip` tooltip · `.rpt-pv-status` footer
- **interaction**: TOC 点击 scrollTo 章节 + IntersectionObserver 联动高亮 · field chip 显 3 态（unfilled 渲染「未能自动填写」F-007 / Evidence-First 一致）· QC 标 hover 弹 tooltip（阻断 / 警告 / 提示 + detail）
- **introduce**: `f2aa949` 2026-04-24 rehome（P4 右栏预览）+ `0cc1ed5` 2026-04-24 UnfilledMarker UI Task C
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/report-preview-fields.spec.ts` pending

## F-014 · Report 预览工具栏 · 5 操作（Word / PDF / 分享 / 版本 / 打印）

- **location**: `web/src/app/archive/report/_components/ReportWorkspace.tsx` `TOOLBAR_ACTIONS` 常量 + `<button.rpt-pv-btn>`
- **selector**: `.rpt-pv-toolbar > .rpt-pv-btn` × 5（`word` / `pdf` / `share` / `vers` / `print`）·每按钮 `<span.ic>` glyph + `<span>` label + `title` 提示
- **interaction**: mock 工具栏（click 不触发真后端导出·留 hook）· title 描述：下载 Word .docx / 导出 PDF / 生成只读分享链接 / 版本时光机对比历史稿 / 打印预览
- **introduce**: `f2aa949` 2026-04-24 rehome
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/report-export.spec.ts` pending

---

## Bench（Agent3 授信）Workspace · F-015 ~ F-019

## F-015 · Credit 模式 tabs · 对公 / 普惠 / 对私三板块

- **location**: `web/src/app/archive/credit/_components/CreditWorkspace.tsx` `TopBar`
- **selector**: `.credit-topbar__mode-btn[data-active]` × 3（`corp / small / retail`）· 容器 `[data-credit-mode="corp|small|retail"]`
- **interaction**: click → `setMode(mode)` → `CREDIT_SESSIONS[mode]` 完整切换三套 mock session（profile / radar / limit / redLines / cases / pipeline 全替换）
- **introduce**: `f2aa949` 2026-04-24 rehome 6 Agent workspaces
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/credit-mode-tabs.spec.ts` pending

## F-016 · Credit ScoreRing + decision badge + CTA "生成授信辅助"

- **location**: `web/src/app/archive/credit/_components/CreditWorkspace.tsx` `PrimaryProfileHero` + `ScoreRing`
- **selector**: `.credit-hero[data-decision=<approved|approved-cut|rejected|pending>]` · `.credit-hero__ring[data-tone=<good|warn|bad>]` SVG 综合分环 · `.credit-hero__decision-txt`（DECISION_LABEL 通过 / 打折批 / 拒 / 待决）· `.credit-hero__cta` button · `.credit-hero__progress-fill` 5 步 450 ms 进度
- **interaction**: click CTA → `startGenerate()` 5 步 mock 进度（`generateSteps`）→ 末步 `setScanned(true)` 解锁 hero 数据 fade-in
- **introduce**: `f2aa949` 2026-04-24 rehome + `ed25abf` 2026-04-26 Stage 4 v2 hero polish（DashboardBand + ScoreRing 整合）
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/credit-decision-cta.spec.ts` pending

## F-017 · Credit 决策看板 3 tab · 四维 Radar / 额度 Gauge / 案例

- **location**: `web/src/app/archive/credit/_components/CreditWorkspace.tsx` `OutputPanel` + `RadarView` / `LimitView` / `CasesView`
- **selector**: `.cr-out__tab[data-active]` × 3（四维 / 额度 / 案例）· `.cr-rd__chart` Recharts `<RadarChart>`·`.cr-lm__g` × 3 Gauge（额度 / 期限 / 利率）含 `.cr-lm__g-applied` 申请值标记 · `.cr-cs__list > .cr-cs__item[data-decision]`
- **interaction**: tab 切换 view · Radar 显 4 维评分 + 权重 + tags · Gauge 显 floor / suggested / applied / ceiling 三段轨道 · Cases 显 ≥ 0.75 sim 召回案例 + 决策结果
- **introduce**: `f2aa949` 2026-04-24 rehome
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/credit-output-tabs.spec.ts` pending

## F-018 · Credit 红线检查 list（pass / warn / fail）

- **location**: `web/src/app/archive/credit/_components/CreditWorkspace.tsx` `LimitView` 底部 `.cr-lm__redlines`
- **selector**: `.cr-lm__rl[data-status="pass|warn|fail"]` × N · `.cr-lm__rl-mark`（`✓ / ! / ✕`）· `.cr-lm__rl-rule` / `.cr-lm__rl-detail` / `.cr-lm__rl-cite` 出处
- **interaction**: 显示 `session.redLines` 全部红线（规则 + 触发明细 + 引用条款出处）·hero footer `.credit-hero__red-summary` 显 pass/warn/fail 计数
- **introduce**: `f2aa949` 2026-04-24 rehome
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/credit-redlines.spec.ts` pending

## F-019 · Credit 证据链 EvidenceLane + L1-3 RiskRadar Preview（Q-033）

- **location**: `web/src/app/archive/credit/_components/CreditWorkspace.tsx` `EvidenceLane` + `RiskRadarPreview` + `web/src/app/archive/credit/_components/RiskRadar.tsx`
- **selector**: `.credit-evi__group[data-tone=<positive|warning|missing>]` × 3 · `.credit-evi__item` · `[data-testid="risk-radar-preview"]` RiskRadar Q-033 wrapper · `.risk-radar-preview-segment`
- **interaction**: 评分细则三段（正向 / 提醒 / 缺失）每项回指资料 / 规则 / 外部接口 · RiskRadar 4 维 segment 派发（`corporate` = 财务 / 行业 / 经营 / 担保；`sme` / `retail` = 还款能力 / 还款意愿 / 稳定性 / 担保）
- **introduce**: `f2aa949` 2026-04-24 rehome（EvidenceLane）+ `439d8ba` 2026-04-26 Stage 2 Q-033 RiskRadar wrapper（closes sub-signal `FRONTEND-RISK-RADAR-LANDED`）
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/credit-evidence.spec.ts` pending；frontend-integration spec V2 已跑过 `risk-radar.spec.ts` × 3 (chromium + edge)

---

## Tower（Agent4 预警）Workspace · F-020 ~ F-023

## F-020 · Alert 红黄绿三灯状态墙（TrafficLightWall）

- **location**: `web/src/app/archive/alert/_components/AlertWorkspace.tsx` `TrafficLightWall`
- **selector**: `.alert-wall-light[data-tier=<red|yellow|green>][data-animate]` × 3 · `.alert-wall-bulb`（含 `.alert-wall-bulb-inner` + `.alert-wall-bulb-ring` 呼吸光晕）· `.alert-wall-count > .num` + `.alert-wall-fill` (% bar)
- **interaction**: 红档 `data-animate="true"` 呼吸 · 黄 / 绿档静态 · 各档显 count / pct / 触达 / 详情（红档显 TOP1 客户 + 金额）
- **introduce**: `f2aa949` 2026-04-24 rehome + `ed25abf` 2026-04-26 Stage 4 v2 hero polish（TrafficLightWall）
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/alert-traffic-light.spec.ts` pending

## F-021 · Alert CTA "启动风险扫描" 5 步 + 队列 ScanQueuePanel

- **location**: `web/src/app/archive/alert/_components/AlertWorkspace.tsx` `HeroSection` + `ScanProgressStrip` + `ScanQueuePanel`
- **selector**: `.al-hero__cta[data-phase=<before|scanning|after>]`（CTA 状态机）· `.al-prog__steps > .al-prog__step[data-status=<done|active|pending>]` × 5 · `.al-queue__list > .al-queue__item[data-tier]`
- **interaction**: click CTA → `startScan()` 500 ms × 5 步 → phase 切到 `after` → queue / heat / sources / kbState / hero summary 五处同步 paint 切到 `scanSnapshotAfter`（pipeline 外链 → 内部 → 流水 → 分级 → 完成）·重复 click = 重新扫描 / 回基线
- **introduce**: `f2aa949` 2026-04-24 rehome + `439d8ba` 2026-04-26 Stage 2 alert codex-fusion 6 step（mock + drop zone + CTA + queue + heat）
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/alert-scan-cta.spec.ts` pending

## F-022 · Alert 看板 3 tab · 分档 / 30 天热力 / 触达率

- **location**: `web/src/app/archive/alert/_components/AlertWorkspace.tsx` `OutputPanel` + `DistView` / `HeatView` / `ReachView`
- **selector**: `.al-out__tab[data-active]` × 3 · `.al-dv__list > .al-dv__row`（按行业 stacked red / yellow / green）· `.al-hv__grid > .al-hv__cell[data-level=0..4]` 30 天热力日历 · `.al-rv__list > .al-rv__item[data-tier]` + `.al-rv__ch-num`（电话 / 短信 / 面访渠道）
- **interaction**: tab 切换 view · DistView 全池 + 行业 stacked + Top 红档 cards · HeatView 30 天日历 (level 0-4 + 峰值 / 均值)·ReachView 三档触达率 + 渠道明细
- **introduce**: `f2aa949` 2026-04-24 rehome
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/alert-output-tabs.spec.ts` pending

## F-023 · Alert 风险信号热区 horizontal bars（SignalHeatmapPanel）

- **location**: `web/src/app/archive/alert/_components/AlertWorkspace.tsx` `SignalHeatmapPanel`
- **selector**: `.al-heatbars__list > .al-heatbars__row` × N · `.al-heatbars__name` / `.al-heatbars__desc` / `.al-heatbars__fill` (% bar) / `.al-heatbars__score`
- **interaction**: 5 信号百分制 bar（外部链接 / 内部规则 / 流水异常 / 行业事件 / 担保链）· 排序 desc · phase=after 显 `.al-heatbars__delta` 「本轮扫描已刷新」
- **introduce**: `f2aa949` 2026-04-24 rehome + `439d8ba` 2026-04-26 alert codex-fusion `#heat`
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/alert-signal-heat.spec.ts` pending

---

## Ledger（Agent5 合规）Workspace · F-024 ~ F-027

## F-024 · Compliance 行内 / 外部政策上传 + CTA "开始政策比对"

- **location**: `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx` `UploadRail` + `DropZoneCard`
- **selector**: `.compliance-drop-card[data-side=<inner|outer>]` × 2 · `.compliance-drop-zone` (label 包 hidden `<input type=file multiple>`) · `.compliance-upload-btn[data-state=<idle|running|done>]` · `.compliance-upload-step[data-state]` × 5
- **interaction**: 行内 / 外部双拖拽区上传政策文档 → click "开始政策比对" → 5 步 520 ms 进度（解析行内 / 解析外部 / 映射条款 / 识别冲突 / 比对完成）→ done 后矩阵 tab 可查看对照
- **introduce**: `f2aa949` 2026-04-24 rehome + `439d8ba` 2026-04-26 Stage 2 compliance codex-fusion 6 step（mock + drop zone + matrix drawer + 修订意见栏）
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/compliance-upload.spec.ts` pending

## F-025 · Compliance 政策 Ticker · 最新 3 条

- **location**: `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx` `PolicyTicker`
- **selector**: `.compliance-ticker-list > .compliance-ticker-item[data-sev=<high|mid|low>][data-scan=<done|scanning|pending>]` × 3 · `.sev-chip` / `.scan-chip` 状态 chip · `.compliance-ticker-card`
- **interaction**: 最新 3 条政策（`policies.slice(0, 3)`）显发布 / 扫描状态 + 冲突计数 + 已排出处置清单 / 无冲突 chip · 顶部 head 显冲突合计 (block / warn)
- **introduce**: `ed25abf` 2026-04-26 Stage 4 v2 hero polish（PolicyTicker 加入）
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/compliance-policy-ticker.spec.ts` pending

## F-026 · Compliance 冲突矩阵（doc × clause）+ drawer 左右对照纸

- **location**: `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx` `MatrixView` + `CellDrawer` + `ClauseMapRowItem`
- **selector**: `.cp-mx__cell[data-severity=<block|warn|info|pass>][data-active]` 矩阵单元 · `.cp-drawer[data-severity]` 展开层 · `.cp-paper[data-side=<inner|outer>]` × 2 行内 / 外部条款对照纸（`dangerouslySetInnerHTML`）· `.cp-mapping__row[data-diff=<bad|warn|info>]`
- **interaction**: 矩阵 cell click → `setSel({docId, clauseId})` → drawer 展开「左右对照纸 + 条款映射 + 整改建议 + cite 出处」·4 严重度（block ✕ / warn ! / info i / pass ✓）
- **introduce**: `f2aa949` 2026-04-24 rehome（基础矩阵）+ `439d8ba` 2026-04-26 codex-fusion（drawer 左右对照纸 + 字段映射）
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/compliance-matrix.spec.ts` pending

## F-027 · Compliance 修订意见 改 / 补 / 强 三类列（RevisionPanel）

- **location**: `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx` `RevisionPanel`
- **selector**: `.compliance-revise-col[data-kind=<fix|add|strengthen>]` × 3 · `.compliance-revise-item` · `.compliance-revise-item-due` 截止日 · `.compliance-revise-chip[data-kind]`（改 / 补 / 强 chip）
- **interaction**: 三类建议（fix 冲突调整 / add 缺失新增 / strengthen 措辞强化）·每项含建议语句 + 对应制度 + 截止日 · TODO 派工单走 `/dispatch /handoff`
- **introduce**: `439d8ba` 2026-04-26 Stage 2 compliance codex-fusion（底部修订意见栏）
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/compliance-revision.spec.ts` pending

---

## Forge（Agent2 风控）Workspace · F-028 ~ F-031

## F-028 · Forge DSL 规则树 viewer（IF / AND / OR / THEN 4 op）

- **location**: `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx` `DslView` + `DslNodeView`
- **selector**: `.rc-dsl-tree > .rc-dsl-node[data-op=<IF|AND|OR|THEN>][data-depth]` 递归层级 · `.rc-dsl-action[data-action=<pass|block|review>]` 终端动作 · `.rc-dsl-expr` `<code>` 表达式 · `.rc-dsl-legend` 4 op 图例
- **interaction**: 渲染 `RISKCTRL_SESSION.dsl` 3 层决策树 · 每节点显 op / field / expr / 终端动作（通过 / 拒绝 / 复核） + 规则原因
- **introduce**: `f2aa949` 2026-04-24 rehome 6 Agent workspaces
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/forge-dsl-tree.spec.ts` pending

## F-029 · Forge KS / AUC / 通过率 三大指标卡 + KS 双线图

- **location**: `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx` `RiskIndicatorRow` + `KSView`
- **selector**: `.riskctrl-row-card[data-tone=<good|warn|bad>]` × 3（KS / AUC / PASS）· `.riskctrl-row-fill` (% bar) · `.rc-ks-chart` Recharts `<LineChart>`（TPR / FPR / KS 三 line · 10 分位 P10-P100）· `.rc-ks-kpi` peak 标
- **interaction**: 三大指标卡（`ksPeak.toFixed(3)` / `auc.toFixed(3)` / `passRate%` + 坏账率）· LineChart 显 TPR 好客户累计 / FPR 坏客户累计 / KS 差值（dashed）
- **introduce**: `f2aa949` 2026-04-24 rehome + `ed25abf` 2026-04-26 Stage 4 v2 hero polish（RiskIndicatorRow 三大指标卡）
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/forge-ks-chart.spec.ts` pending

## F-030 · Forge 样本分布 stacked bars（pass / review / block）

- **location**: `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx` `SampleView` + `RiskIndicatorRow` 内 `riskctrl-row-dist` 紧凑 stacked
- **selector**: `.rc-sp-list > .rc-sp-row[data-k=<pass|review|block>]` 3 档 · `.rc-sp-bar-fill` (% 长度) · `.rc-sp-bad` 坏账率 · `.riskctrl-dist-bar > span.seg[data-k]`（顶部紧凑版）+ `.riskctrl-dist-legend`
- **interaction**: 通过 / 复核 / 拒绝 三档样本（`samples` array）·占比 + 坏账率 + count · 顶部紧凑版 stacked seg 与详情 list 数据同源
- **introduce**: `f2aa949` 2026-04-24 rehome + `ed25abf` 2026-04-26 RiskIndicatorRow dist seg
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/forge-sample-dist.spec.ts` pending

## F-031 · Forge ScanCTA "样本回测" 5 步（cross-link F-004）

- **location**: `web/src/components/shared/ScanCTA.tsx` + `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx`（label="样本回测" · tone="riskctrl"）
- **selector**: 见 F-004（同实例·此处保留为 inventory 完整索引）·5 步 `[装载 DSL 规则 3 条件 / 采样 50K · 30 日 / 计算 KS · 通过率 / AB 对比现行版 / 报告完成]`
- **interaction**: click → 5 步 mock 进度 → `setScanned(true)` 解锁数据 fade-in（与 F-009 / F-016 等共享 ScanCTA · 此处 step labels 为 riskctrl 专属）
- **introduce**: `ffc60ca` 2026-04-23 共享 ScanCTA · 同 F-004
- **lost_at**: 同 F-004（`95437b6` 2026-04-26 dispatch group/dm split 改了 ScanCTA `onDone` callback）
- **restored**: pending（同 F-004 · Phase C.3）
- **smoke_test**: `web/tests/regression/forge-scancta.spec.ts` pending；F-004 cross-link

---

## Dispatch IM · F-032 ~ F-035

## F-032 · Dispatch ComposerBar slash 菜单 · 4 命令

- **location**: `web/src/app/dispatch/_components/ComposerBar.tsx` + `web/src/app/dispatch/_components/SlashMenu.tsx` + `web/src/app/dispatch/_components/composer-commands.ts`
- **selector**: `<form.dpx-composer>` · `.dpx-composer-input` textarea · `.dpx-slash` 浮层 · `.dpx-slash > ul > li.on` 高亮项 · 4 命令 `/run | /handoff | /assign | /clear`
- **interaction**: 输入 `/` 触发菜单 · ↑↓ 切高亮 · Tab 选 · Enter 提交 · `/run agent6 cust_xxx` → router.push `/archive/<agent>?customer=<id>` + event-bus `handoff.requested` · `/handoff <recipeId>` → addMessage `handoff_card` + ticketId · `/assign u_xx` → appendSystemEvent · `/clear` → clearThread
- **introduce**: `7c2fc83` 2026-04-20 3-pane Slack-style IM + dispatch-store + `ca7c72c` 2026-04-20 ComposerBar + /run quick command + `7de7eff` 2026-04-20 event-bus + HandoffCard
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/dispatch-slash.spec.ts` pending

## F-033 · Dispatch 微信气泡 wc-msg（user / ai / system 三档）

- **location**: `web/src/app/dispatch/_components/MessageBubble.tsx`（`wc-msg` 类与 archive workspace ChannelWorkspace / ReportWorkspace 共享设计）
- **selector**: `.wc-msg.wc-msg--<user|ai|system>` · `.wc-msg-bubble.wc-msg-bubble--<variant>` · `.wc-msg-avatar.wc-msg-avatar--<variant>`（含 agent tint 边色）· `.wc-msg-foot.wc-msg-foot--<variant>` · `.wc-msg-author-name` / `.wc-msg-author-role`
- **interaction**: user 右气泡 + ai 左气泡（agent tint border + glyph）+ system 横排 chip · author 解析自 `byUserId` / `agentMeta` / "system" 三路 · 含 F-008 MessagePinHandle 拖柄
- **introduce**: `95437b6` 2026-04-26 Stage 3 ConversationPanel 微信气泡 + dispatch group/dm split + `5d4ae17` 2026-04-27 微信气泡 + IM 实装（DeepSeek 真接）
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/dispatch-wechat-bubble.spec.ts` pending

## F-034 · Dispatch ThreadList GROUPS / DIRECT 分段

- **location**: `web/src/app/dispatch/_components/ThreadList.tsx`
- **selector**: `.dpx-list-section` × 2（GROUPS / DIRECT）· `.dpx-list-section-head .lbl` + `.num` · `.dpx-row` · `.dpx-row.on` 选中 · `.dpx-row-avatar.stage-<lead|prep|review|approved|served|dm>` · `.dpx-row-badge` 未读数
- **interaction**: 左侧线程按 `lastMessageAt desc` 排序 · 群组（`thread.kind ?? "group"`）/ 私聊（`kind === "dm"`）两段 · click → `selectThread(id)` 切 `currentThreadId` · `unreadCount > 0` 显徽章
- **introduce**: `7c2fc83` 2026-04-20 3-pane Slack-style IM + dispatch-store + `418ccf4` 2026-04-22 群组 / 私聊两段
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/dispatch-thread-list.spec.ts` pending

## F-035 · Dispatch 拖到 Composer · cross-MIME reference marker（cross-link F-008）

- **location**: `web/src/app/dispatch/_components/ComposerBar.tsx` `handleDragOver` / `handleDrop` + `web/src/lib/store/whiteboard-store.ts`（`CARD_PIN_MIME`）+ `web/src/lib/store/panel-canvas-store.ts`（`PANEL_PIN_MIME`）
- **selector**: ComposerBar `<form.dpx-composer>` 作 drop target · panel/card 拖 drop → `setText(prev + "\n📎 ${title} · ${subtitle}")`（panel）或 `📌`（card）
- **interaction**: 把 archive panel handle (`PANEL_PIN_MIME`) 或 whiteboard card (`CARD_PIN_MIME`) 拖入 composer textarea → 显 reference marker 文本（📎 panel / 📌 card · 不显 url 链接 · 用户明确反馈不要 link）· 反向拖到 Whiteboard = F-008 缩略图（双向独立）
- **introduce**: `e13feec` 2026-04-27「画布拖到 composer 不显示 url」（MIME 接受 + setText marker 实装）
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/dispatch-drag-marker.spec.ts` pending；反向 F-008 见 `bubble-drag-thumbnail.spec.ts`

---

## Auth · F-036 ~ F-038

## F-036 · LoginForm · 5 用户密码 + persona dropdown

- **location**: `web/src/app/login/_components/LoginForm.tsx` + `web/src/lib/store/auth-store.ts`（`DEMO_USERS` / `useAuthStore.login`）
- **selector**: `.login-form` · `<select#lf-persona[data-role]>` 5 用户 · `<input#lf-pass type=password>` · `.lf-submit[data-role]` · `<div role="alert">` 错误 banner · `PASSWORD_MAP`（`u_wangzhe / u_lihua / u_zhoumin / u_chenkai / u_liuye` → 名拼音小写）
- **interaction**: 选 persona → 输入密码 → submit → 校验 `expected !== password` 显 banner「账号或密码错误」/ 通过 `useAuthStore.login(userId)` → `useEffect(currentUser)` redirect `/today`
- **introduce**: `090f69e` 2026-04-21 3D earth hero + persona dropdown + `858f77f` 2026-04-23 L2 figure-1 shape + `6f96121` 2026-04-27 5 真密码 login + `3c1c2f3` 2026-04-27 AuthGate race fix + `de2d947` 2026-04-27 删密码提示
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/login-5-users.spec.ts` pending

## F-037 · Persona Switcher · Masthead 顶栏 popover

- **location**: `web/src/components/shell/PersonaSwitcher.tsx`
- **selector**: `.persona-sw` 容器 · `.persona-sw-trigger` button (含 `.dot` / `.name` / `.role`) · `.persona-sw-pop[role="menu"]` 浮层 · `.persona-sw-item[role="menuitemradio"][aria-checked]` × 5 · `.persona-sw-avatar[data-role]` · `.persona-sw-logout` 底部退出
- **interaction**: 顶栏 click trigger → popover 列 5 用户 + 当前态 ✓ · click item → `useAuthStore.login(u.id)` 切 persona · `.persona-sw-logout` → `logout() + router.replace("/login")` · Esc / 外部 mousedown 关
- **introduce**: `ef8d03e` 2026-04-20 PersonaSwitcher popover + live authStore wiring + `ad33bee` / `823e0db` 2026-04-22 avatar 修
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/persona-switch.spec.ts` pending

## F-038 · Logout Button · Masthead 顶栏常驻（cross-link F-001）

- **see**: F-001 · 同一组件 · 此条目仅作 inventory 完整索引（F-036~F-038 onboarding 要求 cross-link F-001）
- **location**: `web/src/components/shell/LogoutButton.tsx` + 引用于 `Masthead.tsx` `.shell-op` 段
- **selector**: `.logout-btn`（button）· `.logout-btn .ic`（↪ glyph）· `.logout-btn .lbl`（"退出" 文本）
- **introduce / lost_at / restored**: 见 F-001（注：当前 HEAD 上 LogoutButton.tsx 已存在 · `eaeb209` 2026-04-23 已 restore；F-001 entry 内 `restored: pending` 状态需主 CLI 复核 · 本 worker 不改 F-001~F-008 per onboarding §Boundary）
- **smoke_test**: 同 F-001 · `web/tests/regression/logout.spec.ts` pending

---

## Layout shell · F-039 ~ F-040

> 注：**主题切换 ThemeSwitch** 已纳入 F-003 · 此处 cross-link · 不重复登记。

## F-039 · Masthead · 4 tabs（今日 / 对话 / AI 助手 / 任务）+ live clock

- **location**: `web/src/components/shell/Masthead.tsx`
- **selector**: `.shell-bar` 容器 · `.shell-logo`（乾策 Studio）· `.shell-tabs > a` × 4（`/today` / `/dispatch` / `/archive` / `/warroom` · `a.on` 高亮当前路由）· `.shell-op`（CanvasModeToggle / AuditEntry / PersonaSwitcher / LogoutButton / `.time` live clock）
- **interaction**: 4 tab 走 Next.js `<Link>` · `match(pathname)` 确定高亮（archive 含 `/archive` + 6 旧 legacy alias）· `.time` `setInterval(tick, 20000)` 20 s 刷分
- **introduce**: `1cee58b` 2026-04-19 AppShell + Desk + Masthead + ThemeSwitch (Task B) + `94db10e` 2026-04-19 Task B Masthead/FloatBadge/ThemeSwitcher 1:1 + `e5dad4b` 2026-04-19 4 view + mock fixtures + `e4599c8` 2026-04-27 "画布" 按钮重命名 "编辑" 挪 Masthead
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/masthead-tabs.spec.ts` pending；ThemeSwitch / CanvasModeToggle 见 F-002 / F-003

## F-040 · Desk · 左抽屉（hover-from-edge < 22px / pin / Esc / ⌘K / drag rows / resize）

- **location**: `web/src/components/shell/Desk.tsx` + `web/src/components/shell/DeskCustomerRow.tsx` + `web/src/components/shell/DeskSearch.tsx` + `web/src/components/shell/_desk-store.ts`
- **selector**: `aside.drawer.open.pin` · `.dr-panel` · `.dr-pin` 钉按钮（`aria-pressed`）· `.dr-customers` + `.dr-filter > button[role=tab][data-active]`（全部 / 我负责 / 协同）· `.dr-subsec`（置顶 / 我负责 / 协同 / 全部）· `.dr-row[draggable]` 可拖客户行 · `.dr-qc`（新建 quick create）· `body[data-desk-pinned="true"]`（pin 时 main 留宽）
- **interaction**: 鼠标 < 22 px 触发开 · pin 钉住 · Esc 关 · ⌘K / Ctrl+K focus 搜索 · 16 ms throttle mousemove · 客户分组按 pinned > owned > shared > rest 优先级 · drag row 到 main 视图 = 加载 customer context · resize handle 拖宽 260-480 px 持久 localStorage
- **introduce**: `1cee58b` 2026-04-19 AppShell + Desk + Masthead + `bf79aff` 2026-04-19 Desk 抽屉 ⌘K + 16 ms throttle + `b1850e6` 2026-04-20 Desk 客户列表动态化 + `1d65d79` 2026-04-20 draggable rows drop onto main + `ee1fe46` 2026-04-20 push main right when pinned + `207daef` 2026-04-23 resize handle 260-480
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/desk-drawer.spec.ts` pending

---

## Channel Workspace · multi-session mock state · F-041

## F-041 · Channel mock_sessions multi-pattern session select · panel state hoist

- **location**: `web/src/lib/mock/agent-channel-sessions.ts` (新建 5 ChannelSession · MOCK_SESSIONS_MAP + DEFAULT_SESSION_ID export) + `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (selectedSessionId useState + handleSelectSession + 5 panel function 接 sessionData props)
- **selector**: `[data-testid="channel-session-select"]` 下拉 · `[data-testid="channel-session-option"]` × 5 选项
- **interaction**: 选下拉 → 切到 5 标杆 session 之一 (sess_haichao SaaS B 轮 / sess_zhirong 智能制造 A 轮 / sess_yuemao 跨境电商成长期 / sess_kangyuan 生物医药早期 / sess_jiarui 新消费成熟期) → 全 5 panel (Hero / Funnel / Radar / Candidates / SignalTimeline) 实质切换数据 (radar / signals / funnel / candidates / conversation 各 session 物理不同 · 反 5 原则 §3.5 难度分层)
- **introduce**: 2026-04-28 master plan §B.1 (mock_sessions ≥ 3) + §B.2 (panel state hoist) · workspace-state-protocol.md §2 4-useState gate 框架 · agent-channel-spec.md §6 多 session 标杆数据要求
- **fixes**: master plan gap #2 (mock 单 const 不切 session) + gap #3 (panel 全 import 不接 props · radar/timeline/funnel 永远 mock)
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/channel-mock-switch.spec.ts` (3 case · default render + zhirong panel 全切 + kangyuan 极端档)
- **依赖**: `docs/contracts/workspace-state-protocol.md` (本 entry 是该协议的 Channel 第一波实装) · 后续 Stage C 5 Agent (Report/Credit/Alert/Compli/Riskctrl) 复制本 pattern · 各自加 F-XXX

## F-042 · Channel Candidate Detail Drawer · radar / 匹配明细 / 产品 / 话术

- **location**: `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (`selectedCandidateId` useState · ESC 关 hook · `CandidateDetailDrawer` inline component) + `web/src/lib/mock/agent-channel-sessions.ts` (3 新类型 `MatchDimension` / `ProductRec` / `PitchScript` · 5 mock session 各 candidate 都填) + `web/src/app/archive/channel/channel-workspace.css` (`.ch-drawer*` 50+ rules)
- **selector**: `[data-testid="channel-candidate-drawer"]` 主容器 · `[data-testid="channel-candidate-drawer-backdrop"]` 半透蒙层 · `[data-testid="channel-candidate-drawer-name"]` 标题 · `[data-testid="channel-candidate-drawer-close"]` 关闭按钮 · `[data-testid="candidate-match-dim-chip"]` × 3-6 匹配维度 chip · `[data-testid="candidate-product-card"]` × 3 产品卡 · `[data-testid="candidate-pitch-script"]` × 3-5 话术 · `[data-testid="channel-candidate-card"][data-clickable="yes"]` 触发源
- **interaction**: candidate card click → `setSelectedCandidateId(c.id)` → 右抽屉 220ms slide-in · 4 区: ① header (name + similarity + meta) · ② §一 RadarView 8 维 + 该候选 SignalTimeline · ③ §二 匹配维度明细 chip 列表 (B.4b · 每 chip 显 dim_name / display / score / hit_evidence 来源) · ④ §三 Top3 产品推荐卡 (B.4c · product_name + fit_score + intro + amount_range + rate_band) + §四 切入话术 list (B.4c · customer_name_placeholder + script_text 60-150 字 · 含产品 + 卖点 + 政策红利) · ESC / backdrop click / close button 任一关 drawer · 切 session / live SSE 重置时自动 reset selectedCandidateId
- **introduce**: 2026-04-28 master plan §B.4 (gap #5 候选不可点 detail) + §B.4b (匹配维度明细 · "为什么像") + §B.4c (Top3 产品推荐 + 切入话术 · "打开电话即用") · PRD v2 用户故事核心
- **fixes**: master plan gap #5 (候选无 detail drawer · 体验残缺) + PRD v2 客户经理"打开电话即用"诉求
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/channel-candidate-drawer.spec.ts` (4 case · default render 无 drawer / click 候选 4 区都渲染 / ESC + backdrop 关 / 切 session 自动关)
- **数据契约 (反 5 原则 §3.5)**: 5 mock session × 5 candidate · 各 candidate 都有 `match_dimensions` (3-6 条 · score 0-100 · 不含 is_match 答案字段) + `product_recommendations` (3 条 · fit_score 0-100 + intro + 额度 + 利率) + `pitch_scripts` (3 条 · 60-150 字含 customer_name_placeholder + 关键卖点 + 不虚构数字) · 难度分层覆盖 简单 20% / 中等 50% / 困难 20% / 极端 10%
- **依赖**: `docs/contracts/workspace-state-protocol.md` §2 (4) selectedCandidate gate + §5 candidate detail drawer pattern · `docs/contracts/agent-channel-spec.md` §2 C7/C8/C9 + §6.3 candidate 数据契约
- **复用**: 后续 Stage C 5 Agent 复制本 pattern · drawer 4 区结构是跨 Workspace 模板

---

## Channel Workspace · live SSE wire · F-043

## F-043 · Channel live SSE wire · candidate 全字段 normalize (industry/geo/scale + drawer 三件套)

- **location**: `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (`normalizeBackendCandidate` 函数 · `runRealSearch` SSE done event 解析 · `liveCandidates` setLive 注入) · 后端 `agent_channel/sse_extras.py` + `agent_channel/realtime_stream.py:_build_final_output` (snake_case enrich)
- **selector**: `[data-testid="channel-candidate-card"]` (live mode 显 backend 真值 industry/geo/scale 而非 "—" 占位) · `[data-testid="channel-candidate-drawer"]` (live mode 内 `[data-testid="candidate-match-dim-chip"]` × N + `[data-testid="candidate-product-card"]` × 3 + `[data-testid="candidate-pitch-script"]` × N 全是 backend 返的 snake_case `match_dimensions` / `product_recommendations` / `pitch_scripts` 字段映射来 · 不是 mock fallback)
- **interaction**: 用户 textbox 提交 query (或 "开始扫描" CTA) → fetch `/api/channel/run` SSE → done event 每候选 normalize 含 `match_dimensions` / `product_recommendations` / `pitch_scripts` / `radar_8axis` / signals 转 timeline `SignalEvent[]` → setLive(norm) → CandidatesPanel + drawer 全消费 live 数据 (drawer 4 区在 live mode 显 backend 真生成内容)
- **introduce**: 2026-04-28 master plan §B.5b · workspace-state-protocol.md §4 后端 SSE done event 必须返完整 panel 数据 · agent-channel-spec.md §5.3 SSE 契约 · Q-041 candidate metadata 路由 (industry/geo/scale 不再硬编 "未获取")
- **fixes**: master plan gap #3 (panel 不接 props · radar/timeline/funnel 永远 mock 部分修 · 候选 drawer 三件套从 mock 切到 live) + gap #4 (后端 SSE 只返 candidates 现已扩 snake_case 全字段 · 前端 wire) + Q-041 candidate metadata `[object Object]` / "未获取" 占位的彻底解
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/channel-live-wire.spec.ts` (3 case · 3 dropzone 渲染 + 上传 → 画像 → 12 chip + 点扫描 → drawer 4 区全 wire)
- **数据契约**: backend `candidate.match_dimensions: [{dim_name, hit_evidence, score, display}]` × ≥3 · `product_recommendations: [{product_name, fit_score, intro, category, amount_range?, rate_band?}]` × 3 · `pitch_scripts: [{customer_name_placeholder, script_text, source}]` × ≥1 · 前端 normalize 兼容 snake_case + 兼容 mock camelCase fallback
- **依赖**: `docs/contracts/agent-channel-spec.md` §5.3 · `docs/contracts/workspace-state-protocol.md` §4 · backend `agent_channel/sse_extras.py` (Worker A1 Stage B 实装)

---

## Channel Workspace · KB upload UI · F-044

## F-044 · Channel KB upload UI · 3 类 dropzone (客户名录 / 政策 / 行业指引)

- **location**: `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (`KbUploadStrip` + `KbDropzone` 组件 · `handleKbUpload` callback · `kbIds` / `kbStatus` / `kbSummaries` / `kbErrors` useState) · 后端 `agent_channel/kb_upload.py` + `/api/channel/upload_kb`
- **selector**: `[data-testid="kb-upload-strip"]` 容器 · `[data-testid="kb-dropzone-customer-list"]` / `[data-testid="kb-dropzone-policy"]` / `[data-testid="kb-dropzone-industry-guide"]` 3 dropzone · 各 dropzone 含 `[data-testid="<kb>-input"]` (隐藏 file input · 拖拽用) + `[data-testid="<kb>-btn"]` (显式选择按钮) + `[data-testid="<kb>-summary"]` (上传成功后显 kb_id + filename + summary_text)
- **interaction**: 用户点 "选择文件" 按钮 OR 拖文件到 dropzone → `<input type="file">` 选定 → `handleKbUpload(type, file)` → multipart/form-data POST `/api/channel/upload_kb` (字段: kb_type · file) → 后端解析 xlsx/pdf/docx → 返 `{kb_id, source_filename, summary_text, n_rows? | n_pages?}` → 前端写 `kbIds[type] = kb_id` + `kbStatus[type] = "success"` → dropzone 边框变青绿 (data-has-upload=yes) + 显 summary card · 失败时 `kbStatus = "error"` + 显错误 banner
- **introduce**: 2026-04-28 master plan §B.6 · agent-channel-spec.md §C1 KB 多文件上传 · 后端 W-B-A2 worker 实装 (kb_upload.py · POST /api/channel/upload_kb · 50MB cap)
- **fixes**: master plan gap #1 (KB 上传) frontend 缺 - PRD v2 必须 · 客户经理上传 "已有客户名录 + 政策 + 行业指引" 才能抽 IdealProfile look-alike · 不能直接走 query 兜底
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/channel-live-wire.spec.ts` test #1 (3 dropzone 渲染) + test #2 (上传 customer_list mock 路径走通 · summary card 显)
- **数据契约**: kb_type ∈ {customer_list, policy, industry_guide} · file ext ∈ {xlsx, xls, csv, pdf, docx} · ≤ 50MB · 单文件 per request · 后端持久化 `data/channel_kb/{kb_id}.json`
- **依赖**: backend `agent_channel/kb_upload.py` (W-B-A2 worker) · `docs/onboarding/W-B-A2-channel-kb-upload.md` · `docs/contracts/agent-channel-spec.md` §5.2

---

## Channel Workspace · IdealProfile 12 维 + 用户 confirm · F-045

## F-045 · Channel IdealProfile card · 12 维 chip + reasoning + "开始扫描" CTA

- **location**: `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (`IdealProfileCard` 组件 · `idealProfileToQuery` helper · `idealProfile` / `profileFetching` / `profileError` useState · `externalTrigger` state + `QueryBar` `externalTrigger` prop wire) · 后端 `agent_channel/ideal_profile.py` (IdealProfile12 schema · LLM chat_json) + `/api/channel/profile`
- **selector**: `[data-testid="ideal-profile-card"]` 主容器 · `[data-testid="ideal-profile-chip"]` × 12 (industry_focus / scale_preference / geo_coverage / customer_type / product_keywords / growth_signals / risk_signals 列表字段 + stage / capital_relation / business_size / employee_size / value_chain_position 字符串字段) · `[data-testid="ideal-profile-loading"]` / `[data-testid="ideal-profile-error"]` 状态 · `[data-testid="ideal-profile-reasoning"]` 解析说明段 · `[data-testid="start-scan-cta"]` "开始扫描" 按钮
- **interaction**: customer_list KB 上传成功 → `handleKbUpload` 内自动 POST `/api/channel/profile` `{kb_id, kb_type}` → 后端 `extract_ideal_profile` 用 DeepSeek temperature 0.2 抽 12 维 + confidence + reasoning_text → 前端 `setIdealProfile(pdata)` → IdealProfileCard 渲染 12 chip grid + reasoning · 用户 click "开始扫描" → `idealProfileToQuery(profile)` 转 query 字符串 → `setExternalTrigger({input, nonce: Date.now()})` → QueryBar `useEffect[externalTrigger]` 自动 call `runRealSearch(query)` → 走标准 SSE 全字段 wire (F-043) · 用户 confirm 才扫描 (PRD v2 "看一眼画像确认 → 才扫" 体验红线)
- **introduce**: 2026-04-28 master plan §B.6b · agent-channel-spec.md §C2 IdealProfile LLM 抽取 · §C3 用户确认后才"开始扫描" · 后端 W-B-A3 worker 实装 (ideal_profile.py · IdealProfile12 schema · POST /api/channel/profile)
- **fixes**: master plan gap #2 (IdealProfile 缺) frontend - PRD v2 必须 · 客户经理上传完不能直接黑盒扫 · 必须看 12 维画像 + reasoning + 自己确认才扫 (autopilot 期需要)
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/channel-live-wire.spec.ts` test #2 (上传 customer_list → IdealProfile 自动抽 + 12 chip 显 + start-scan-cta 显) + test #3 (点 CTA → live SSE wire 链路通)
- **数据契约**: 12 维 schema 见 `agent_channel/ideal_profile.py:IdealProfile12` (Pydantic BaseModel · 7 list[str] 字段 + 5 str 字段) + `confidence_score` (0-1) + `reasoning_text` (80-150 字 · 解析说明) · LLM 失败时降级返空 profile + reasoning_text 标降级原因 · 不抛异常
- **依赖**: backend `agent_channel/ideal_profile.py` (W-B-A3 worker) · `docs/onboarding/W-B-A3-channel-ideal-profile.md` · `docs/contracts/agent-channel-spec.md` §5.2 · F-044 (KB upload 是上游) · F-043 (扫描 SSE 是下游)

---

## Credit / Compli Workspace · 空白启动 + 完整 production-grade pipeline · F-048 / F-050 / F-053 / F-054

## F-048 · Credit empty state · default started=false → Hero + 3 CTA + skeleton + status pill

- **status**: live
- **owner**: Worker A2 (W-CF-A2)
- **goal**: 满足 empty-state-design-protocol v1.0 §2-§5 落地 · Credit Workspace 默认空白启动 · 不渲染 mock 数据 · 用户主动触发 (CTA) 才 setStarted(true) · 信任模型 P0 (银行用户对假数据零容忍)
- **location**: `web/src/app/archive/credit/_components/CreditWorkspace.tsx` (`started` useState + `CreditEmptyState` 子组件 · 顶层 fork render `if (!started) return EmptyState`) · `web/src/app/archive/credit/credit-workspace.css` (`.credit-empty__*` 类 ~250 行)
- **selector**: `[data-credit-started="no"]` 根 · `[data-testid="credit-empty-skeleton"]` skeleton 容器 · `[data-testid="credit-empty-skeleton-panels"]` 3 panel grid · `[data-testid="credit-empty-status-pill"]` 状态 pill · `[data-testid="credit-stage-tab-{corporate,small_business,retail}"]` 3 stage tabs · `[data-testid="credit-decision-cta"]` primary CTA · `[data-testid="credit-decision-cta-secondary"]` secondary CTA · `[data-testid="credit-history-tertiary"]` tertiary 历史 (示例) · `[data-testid="credit-redlines-list"]` 红线 placeholder · `[data-testid="credit-export-docx-btn"]` Word 导出 (default disabled)
- **interaction**: default 进 `/archive/credit` → `started=false` → 渲染 EmptyState (Hero "授信决策辅助 · 4 维评分 + 红线 + 案例 + 决策建议书" + 3 stage_tab 切换 + 3 CTA 分级 + 3-card panel skeleton + status pill) · primary CTA "选材料 + 起决策" → `runDecision({mockMode: false})` → POST `/api/credit/decision` SSE (stage_tab + preset_name) · secondary CTA "演示模式起决策" → `runDecision({mockMode: true})` → backend mock SSE fixture · tertiary "历史 (示例)" → `selectHistoricalDemo()` → setStarted=true + scanned=yes 看 mock 演示 · 任一 CTA 触发都 `setStarted(true)` 切到完整 workspace
- **introduce**: 2026-04-28 W-CF-A2 worker · empty-state-design-protocol v1.0 §6 Credit 改造点 (主 CTA 选材料 + 起决策 / secondary 直接输入 / tertiary 历史 dropdown 标 (示例)) · onboarding §Acceptance 列 6 必加 testid
- **fixes**: master plan gap #6 (5 archive Workspace 仅 Channel 部分实装 · Credit 部分实装但 default 已渲染 mock data 违反 trust model) · empty-state-design-protocol §1.1 信任 + §1.2 数据归属 + §1.4 Show Its Work
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/credit-empty-state.spec.ts` (4 test: default render skeleton + 3 stage_tab 切换 + tertiary trigger started + tertiary 标 (示例) tag)

---

## F-050 · Compli Workspace · 空白启动 + 3 CTA 分级

- **location**: `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx` (`started` state + `TriggerBar` + `EmptyStateSkeleton`) + `compliance-workspace.css` 末尾 Stage CF 段
- **selector**: `[data-testid="compli-workspace"][data-started="no"]` · `[data-testid="compli-empty-skeleton"]` · `[data-testid="compli-history-dropdown"]` · `[data-testid="compli-template-check-cta"]` · `[data-testid="compli-policy-scan-cta"]`
- **interaction**:
  - default `started=false` · 仅 Hero + UploadRail + TriggerBar + 空骨架
  - Primary 上传 + 「开始政策比对」 → `setStarted(true)` + POST `/api/compliance/policy_scan` (SSE) → 落 `scanId`
  - Secondary 「用模板快速比对」 → POST `/api/compliance/matrix_check` 同步 demo
  - Tertiary 历史 dropdown 标 `(示例)` → demo banner 显示
- **contract**: `docs/contracts/empty-state-design-protocol.md` v1.0 · production / mock 路径分离 · mock 不 default load
- **introduce**: pending Stage CF 第 1 批 cherry-pick (c75488f → main · 2026-04-28)
- **lost_at**: N/A (新 feature · 此前 ComplianceWorkspace 默认 load mock 数据 · 无 empty state)
- **smoke_test**: `web/tests/regression/compli-empty-state.spec.ts` (5 case · 默认空 + dropdown 标 + 3 CTA 分级 + tertiary trigger + primary CTA mock SSE)

## F-053 · Credit 完整 workspace · LLM SSE 决策 + Word 导出 (started=true 路径)

- **status**: live
- **owner**: Worker A2 (W-CF-A2 · backend W-C2-A2 v4.0 复用)
- **goal**: started=true 后渲染完整授信决策 panel + 真接 backend SSE 流 + LLM advice 实时 fade-in + decision_id 缓存 + Word 导出 (.docx)
- **location**: `web/src/app/archive/credit/_components/CreditWorkspace.tsx` (`runDecision()` async fn · POST `/api/credit/decision` SSE 解析 advising_done event · `liveAdvice/decisionId/decisionRunning/decisionError` useState · `CreditDecisionAdvicePanel` 子组件 · 动态生成 anchor 触发 .docx 下载) · `credit-workspace.css` (`.credit-advice-live__*` ~120 行)
- **selector**: `[data-credit-started="yes"]` 根 · `[data-testid="credit-decision-advice-live"]` advice panel 容器 (live SSE 完成后渲) · `.credit-advice-live__verdict-lbl/grade/score` 决策结论 + 风险等级 + 综合分 · `.credit-advice-live__meta` dt/dd 额度/期限/利率 · `.credit-advice-live__cond` 附加条件列表 · `[data-testid="credit-export-docx-btn"]` Word 导出 button (live 完成后启用)
- **interaction**: 用户在 EmptyState 点 primary/secondary CTA → `runDecision()` POST `/api/credit/decision` SSE (`stage_tab + preset_name + mock`) → 流式解析: `advising_done` event 注 `liveAdvice` + `decision_cached` event 拿 `decision_id` → `CreditDecisionAdvicePanel` fade-in 渲 LLM 建议 + 决策卡 + 红线解释 + 附加条件 → 用户点 export_docx → POST `/api/credit/export_docx` `{decision_id}` (优先 cache) 或 `{advice}` (passthrough) → 拿 .docx blob → 动态 anchor click 触发浏览器下载 `授信决策建议书_{stage_tab}_{ts}.docx` · `decision_id` 不存在/过期 → 后端 404 + ttl_sec hint
- **introduce**: 2026-04-28 W-CF-A2 worker · 复用 W-C2-A2 v4.0 backend 的 `decision SSE event=decision_cached` + `export_docx body{decision_id}` (in-memory cache 30min TTL) · empty-state-design-protocol §3 状态机 trigger 之一
- **fixes**: master plan gap #8 (Agent3 后端 stub) · gap #12 (6 Agent Word 导出·后端只有 xlsx) Credit 闭环
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/credit-empty-state.spec.ts` test #3 (点 tertiary trigger 完整 workspace · RiskRadarPreview 渲染验证) · live SSE wire 完整 e2e (含 docx 下载) 留 Stage D dry-run 阶段补 (本批 acceptance 不要求 · 因 LLM key 环境依赖 + binary blob assert 复杂)
- **依赖**: F-048 (empty state 是入口) · backend `/api/credit/decision` SSE v4.0 + `/api/credit/export_docx` (W-C2-A2 已 deliver) · `web/AGENTS.md` Next 16 注意 (use client + fetch streaming reader 标准模式)

---

## F-049 · Alert empty state · default started=false → Hero + 3 CTA + 红黄绿 skeleton + status pill

- **status**: live
- **owner**: Worker A2 (W-CF2-A2)
- **goal**: 满足 empty-state-design-protocol v1.0 §2-§5 落地 · Alert Workspace 默认空白启动 · 不渲染 mock topCases / hitlist · 用户主动触发 (3 CTA 之一) 才 setStarted(true) · 信任模型 P0 (银行用户对假数据零容忍 · 假"红黄绿户数"看着像真分级会让用户混淆 production / demo)
- **location**: `web/src/app/archive/alert/_components/AlertWorkspace.tsx` (`started` useState + `AlertEmptyState` 子组件 · 顶层 fork render `if (!started) return EmptyState`) · `web/src/app/archive/alert/alert-workspace.css` (`.alert-empty__*` 类 ~220 行 + `.alert-export-bar__*` + `.alert-drill-drawer__*` + `.alert-demo-banner` ~140 行)
- **selector**: `[data-alert-started="no"]` 根 · `[data-testid="alert-workspace"]` workspace 容器 · `[data-testid="alert-empty-skeleton"]` skeleton · `[data-testid="alert-empty-skeleton-panels"]` 3 灯 + hitlist + signalmap grid · `[data-testid="alert-empty-status-pill"]` 状态 · `[data-testid="alert-scan-cta"]` primary · `[data-testid="alert-scan-cta-secondary"]` secondary · `[data-testid="alert-history-tertiary"]` tertiary 历史 (示例) · `[data-testid="alert-traffic-light-{red,yellow,green}"]` 三灯 skeleton · `[data-testid="alert-export-docx-btn"]` Word 导出 (default disabled)
- **interaction**: default 进 `/archive/alert` → `started=false` → 渲染 EmptyState (Hero "贷中风险预警 · 在贷客户池批量扫描 + 红黄绿分级榜单" + 3 CTA + 红黄绿三灯 skeleton + hitlist 占位 + signalmap 占位 + status pill) · primary CTA "启动风险扫描" → `triggerPrimaryScan()` → setStarted=true + 现有 startScan() 跑 mock 5 步 · secondary CTA "选规则集 + 调阈值" → `triggerSecondaryScan()` → 同 primary 但留 hook 后续可拆 · tertiary "历史 (示例)" → `triggerTertiaryDemo()` → 跳过 scanning · phase=after 直接展示 mock + alert-demo-banner 提示 "示例数据 (training mode)"
- **introduce**: 2026-04-28 W-CF2-A2 worker · empty-state-design-protocol v1.0 §6 Alert 改造点 (主 CTA 启动扫描 (KB 已加载即可) · panel 默认空 · 历史 secondary) · onboarding §Acceptance 6 必加 testid
- **fixes**: master plan gap #6 (Alert Workspace 部分实装但 default 直接渲 mock topCases / hitlist 违 trust model) · empty-state-design-protocol §1.1 信任 + §1.2 数据归属 + §1.4 Show Its Work + §1.5 Demo / Production 路径分离
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/alert-empty-state.spec.ts` (4 test · chromium 4/4 + edge 4/4 = 8/8 PASS · default render skeleton + 6 testid 全可见 + tertiary trigger started+demo banner + tertiary 标 (示例) + primary trigger started)

---

## F-055 · Alert 完整 workspace · drill drawer + Word 导出 + demo banner (started=true 路径)

- **status**: live
- **owner**: Worker A2 (W-CF2-A2)
- **goal**: started=true 后渲染完整贷中预警 workspace (TrafficLightWall + ScanQueuePanel + SignalHeatmap + drill drawer + 顶部 export bar) · 客户 click → drill drawer 显风险等级/授信余额/触发信号/处置建议 · phase=after 后启用 export_docx button (POST /api/alert/export_docx) · tertiary trigger 显 demo banner 提示
- **location**: `web/src/app/archive/alert/_components/AlertWorkspace.tsx` (`AlertExportPanel` + `AlertDrillDrawer` 子组件 · `drillCustomer/scanError/demoBanner` useState · `triggerPrimaryScan/triggerSecondaryScan/triggerTertiaryDemo` 三 handler) · `alert-workspace.css` (`.alert-export-bar__*` + `.alert-drill-drawer__*` + `.alert-demo-banner` ~180 行)
- **selector**: `[data-alert-started="yes"]` 根 · `[data-testid="alert-export-bar"]` 顶部导出条 · `[data-testid="alert-drill-cta"]` 详情入口 (phase=after 显) · `[data-testid="alert-export-docx-btn"]` Word 导出 (phase=after 启用) · `[data-testid="alert-drill-drawer"]` 客户详情 drawer · `[data-testid="alert-hitlist-row"]` hitlist row · `[data-testid="alert-demo-banner"]` tertiary trigger 提示
- **interaction**: 用户在 EmptyState 点 primary/secondary CTA → setStarted=true · phase=before → startScan 跑 5 步 (500ms 间隔) → phase=after · TrafficLightWall + ScanQueuePanel + SignalHeatmap 全 panel 渲 · 顶部 alert-export-bar 出现 · 用户点 alert-drill-cta → setDrillCustomer(TOP customer) → AlertDrillDrawer fade-in (右上角 fixed) 显 风险等级 + 授信余额 + 触发信号 (triggers) + 处置建议 (advice) · 用户点 alert-export-docx-btn → POST /api/alert/export_docx (后端 endpoint 待 backend 补 · 本批前端按 contract 实装 · 失败 console.error 不抛 UI 阻断) → blob → anchor click 下载 `贷中预警榜单_{ts}.docx`
- **introduce**: 2026-04-28 W-CF2-A2 worker · empty-state-design-protocol §3 状态机 trigger 之一
- **fixes**: master plan gap #6 (Alert Workspace 完整 production-grade) + gap #12 (6 Agent Word 导出 · 后端只有 xlsx) Alert 闭环 frontend
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/alert-empty-state.spec.ts` test #2 (tertiary trigger → started=yes + alert-wall 渲 + alert-hitlist-row 出现 + alert-demo-banner 显) · 完整 e2e 含 drill drawer + docx 下载留 Stage D dry-run
- **依赖**: F-049 (empty state 入口) · backend `/api/alert/scan` (Stage A.5 上批) + `/api/alert/export_docx` (Stage D 待后端补 · 本批前端按 contract 实装) · `web/AGENTS.md` Next 16 注意

---

## F-049 · Alert empty state · default started=false → Hero + 3 CTA + 红黄绿 skeleton + status pill

- **status**: live
- **owner**: Worker A2 (W-CF2-A2)
- **goal**: 满足 empty-state-design-protocol v1.0 §2-§5 落地 · Alert Workspace 默认空白启动 · 不渲染 mock topCases / hitlist · 用户主动触发 (3 CTA 之一) 才 setStarted(true) · 信任模型 P0 (银行用户对假数据零容忍 · 假"红黄绿户数"看着像真分级会让用户混淆 production / demo)
- **location**: `web/src/app/archive/alert/_components/AlertWorkspace.tsx` (`started` useState + `AlertEmptyState` 子组件 · 顶层 fork render `if (!started) return EmptyState`) · `web/src/app/archive/alert/alert-workspace.css` (`.alert-empty__*` 类 ~220 行 + `.alert-export-bar__*` + `.alert-drill-drawer__*` + `.alert-demo-banner` ~140 行)
- **selector**: `[data-alert-started="no"]` 根 · `[data-testid="alert-workspace"]` workspace 容器 · `[data-testid="alert-empty-skeleton"]` skeleton · `[data-testid="alert-empty-skeleton-panels"]` 3 灯 + hitlist + signalmap grid · `[data-testid="alert-empty-status-pill"]` 状态 · `[data-testid="alert-scan-cta"]` primary · `[data-testid="alert-scan-cta-secondary"]` secondary · `[data-testid="alert-history-tertiary"]` tertiary 历史 (示例) · `[data-testid="alert-traffic-light-{red,yellow,green}"]` 三灯 skeleton · `[data-testid="alert-export-docx-btn"]` Word 导出 (default disabled)
- **interaction**: default 进 `/archive/alert` → `started=false` → 渲染 EmptyState (Hero "贷中风险预警 · 在贷客户池批量扫描 + 红黄绿分级榜单" + 3 CTA + 红黄绿三灯 skeleton + hitlist 占位 + signalmap 占位 + status pill) · primary CTA "启动风险扫描" → `triggerPrimaryScan()` → setStarted=true + 现有 startScan() 跑 mock 5 步 · secondary CTA "选规则集 + 调阈值" → `triggerSecondaryScan()` → 同 primary 但留 hook 后续可拆 · tertiary "历史 (示例)" → `triggerTertiaryDemo()` → 跳过 scanning · phase=after 直接展示 mock + alert-demo-banner 提示 "示例数据 (training mode)"
- **introduce**: 2026-04-28 W-CF2-A2 worker · empty-state-design-protocol v1.0 §6 Alert 改造点 (主 CTA 启动扫描 (KB 已加载即可) · panel 默认空 · 历史 secondary) · onboarding §Acceptance 6 必加 testid
- **fixes**: master plan gap #6 (Alert Workspace 部分实装但 default 直接渲 mock topCases / hitlist 违 trust model) · empty-state-design-protocol §1.1 信任 + §1.2 数据归属 + §1.4 Show Its Work + §1.5 Demo / Production 路径分离
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/alert-empty-state.spec.ts` (4 test · chromium 4/4 + edge 4/4 = 8/8 PASS · default render skeleton + 6 testid 全可见 + tertiary trigger started+demo banner + tertiary 标 (示例) + primary trigger started)

---

## F-055 · Alert 完整 workspace · drill drawer + Word 导出 + demo banner (started=true 路径)

- **status**: live
- **owner**: Worker A2 (W-CF2-A2)
- **goal**: started=true 后渲染完整贷中预警 workspace (TrafficLightWall + ScanQueuePanel + SignalHeatmap + drill drawer + 顶部 export bar) · 客户 click → drill drawer 显风险等级/授信余额/触发信号/处置建议 · phase=after 后启用 export_docx button (POST /api/alert/export_docx) · tertiary trigger 显 demo banner 提示
- **location**: `web/src/app/archive/alert/_components/AlertWorkspace.tsx` (`AlertExportPanel` + `AlertDrillDrawer` 子组件 · `drillCustomer/scanError/demoBanner` useState · `triggerPrimaryScan/triggerSecondaryScan/triggerTertiaryDemo` 三 handler) · `alert-workspace.css` (`.alert-export-bar__*` + `.alert-drill-drawer__*` + `.alert-demo-banner` ~180 行)
- **selector**: `[data-alert-started="yes"]` 根 · `[data-testid="alert-export-bar"]` 顶部导出条 · `[data-testid="alert-drill-cta"]` 详情入口 (phase=after 显) · `[data-testid="alert-export-docx-btn"]` Word 导出 (phase=after 启用) · `[data-testid="alert-drill-drawer"]` 客户详情 drawer · `[data-testid="alert-hitlist-row"]` hitlist row · `[data-testid="alert-demo-banner"]` tertiary trigger 提示
- **interaction**: 用户在 EmptyState 点 primary/secondary CTA → setStarted=true · phase=before → startScan 跑 5 步 (500ms 间隔) → phase=after · TrafficLightWall + ScanQueuePanel + SignalHeatmap 全 panel 渲 · 顶部 alert-export-bar 出现 · 用户点 alert-drill-cta → setDrillCustomer(TOP customer) → AlertDrillDrawer fade-in (右上角 fixed) 显 风险等级 + 授信余额 + 触发信号 (triggers) + 处置建议 (advice) · 用户点 alert-export-docx-btn → POST /api/alert/export_docx (后端 endpoint 待 backend 补 · 本批前端按 contract 实装 · 失败 console.error 不抛 UI 阻断) → blob → anchor click 下载 `贷中预警榜单_{ts}.docx`
- **introduce**: 2026-04-28 W-CF2-A2 worker · empty-state-design-protocol §3 状态机 trigger 之一
- **fixes**: master plan gap #6 (Alert Workspace 完整 production-grade) + gap #12 (6 Agent Word 导出 · 后端只有 xlsx) Alert 闭环 frontend
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/alert-empty-state.spec.ts` test #2 (tertiary trigger → started=yes + alert-wall 渲 + alert-hitlist-row 出现 + alert-demo-banner 显) · 完整 e2e 含 drill drawer + docx 下载留 Stage D dry-run
- **依赖**: F-049 (empty state 入口) · backend `/api/alert/scan` (Stage A.5 上批) + `/api/alert/export_docx` (Stage D 待后端补 · 本批前端按 contract 实装) · `web/AGENTS.md` Next 16 注意

---

## F-054 · Compli Workspace · 完整 production-grade pipeline (3 endpoints + Word 导出)

- **location**: `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx` (`triggerPolicyScan` / `triggerTemplateCheck` / `triggerExportDocx` handlers · `RevisionPanel` 接 `scanId/exportInfo/onExportDocx` props) · `web/src/lib/api/compliance.ts` (W-FIX2-A3 加 · runPolicyScan / runMatrixCheck / exportDocx)
- **selector**: `[data-testid="compli-policy-upload-cta"]` · `[data-testid="compli-business-upload-cta"]` · `[data-testid="compli-matrix-cell"]` · `[data-testid="compli-conflict-chip"]` · `[data-testid="compli-revision-draft"]` · `[data-testid="compli-export-docx-btn"]` · `[data-testid="compli-live-fail-banner"]`（W-FIX2-A3 加） · `[data-testid="compli-live-fail-retry"]`（W-FIX2-A3 加）
- **interaction**:
  - 上传政策 + 业务制度 → SSE 抽规则 → 抽事件 → N×M 矩阵 → 改/补/强 LLM 修订
  - 矩阵 cell click 展开左右对照纸 + 条款映射
  - RevisionPanel 改/补/强 三 chip + 展开建议列表
  - 「导出修订意见 Word」 → POST `/api/compliance/export_docx` → blob → a.click() 触发下载
- **backend wire**: Stage C.4 `agent_compliance/api.py` 3 endpoints (`a76cea2` → MERGED `fb78b85`)
- **introduce**: pending Stage CF 第 1 批 cherry-pick (c75488f → main · 2026-04-28)
- **lost_at**: N/A (新增 backend wiring · ComplianceWorkspace 既有 mock viz 转为 SSE 真接 + Word 导出)
- **smoke_test**: `web/tests/regression/compli-empty-state.spec.ts` (部分覆盖 · 完整 SSE 解析跑通待 Stage D playwright)
- **W-FIX2-A3 fix (2026-04-29)**: bug #5 修复 · 之前 primary CTA 路径 hardcode `force_mock: true` (line 113) 静默走 mock policy corpus · UI 标 live · 用户欺骗 (违反 live-fallback-banner-spec.md §1.5 production / demo 路径分离)。
  - **fix**: primary path 现 `force_mock: false` · 真接后端 SSE · 失败 → live-fail banner（per spec §2 规则 1）· `mock` 仍只在 tertiary `(示例)` dropdown 路径
  - **新 selector**: `compli-live-fail-banner` + `compli-live-fail-retry` (status / endpoint data-attrs)
  - **新 client**: `web/src/lib/api/compliance.ts` 复用 `_live.ts` LiveFailError + streamSse · Pattern 与 riskctrl/alert client 一致

## F-051 · Riskctrl/Forge Workspace · 空白启动 + 3 CTA 分级

- **location**: `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx`（`started` state + `RiskTriggerBar` + `RiskEmptySkeleton`）+ `riskctrl-workspace.css` 末尾 Stage CF2 段
- **selector**: `[data-testid="riskctrl-workspace"][data-started="no"]` · `[data-testid="riskctrl-empty-skeleton"]` · `[data-testid="riskctrl-history-dropdown"]` · `[data-testid="riskctrl-preset-dropdown"]` · `[data-testid="riskctrl-dsl-gen-cta"]`
- **interaction**:
  - default `started=false` · 仅 Hero + RiskTriggerBar + 空骨架（4 panel placeholder）
  - Primary 「选样本 + 写策略 · 生成 DSL」按钮 → `setStarted(true)` + POST `/api/riskctrl/dsl_gen` (SSE) → 落 `rulesetId`
  - Secondary 预置规则集 dropdown → `setStarted(true)` + 直接展示
  - Tertiary 历史回测 dropdown 标 `(示例)` → demo banner 显示
- **contract**: `docs/contracts/empty-state-design-protocol.md` v1.0 · production / mock 路径分离
- **introduce**: pending Stage CF2 第 2 批 cherry-pick (2e0f49f → main · 2026-04-28)
- **lost_at**: N/A（新 feature · 此前 RiskctrlWorkspace 默认 load mock 数据 · 无 empty state）
- **smoke_test**: `web/tests/regression/riskctrl-empty-state.spec.ts`（6 case · 默认空 + dropdown 标 + 3 CTA 分级 + tertiary trigger + secondary trigger + primary mock SSE）

## F-056 · Riskctrl Workspace · 完整 production-grade pipeline (3 endpoints + Word 导出)

- **location**: `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx`（`triggerDslGen` / `triggerBacktest` / `triggerExportDocx` handlers · `RiskOutputPanel` 接 `rulesetId/exportInfo/onExportDocx` props）
- **selector**: `[data-testid="riskctrl-dsl-editor"]` · `[data-testid="riskctrl-ks-chart"]` · `[data-testid="riskctrl-sample-dist"]` · `[data-testid="riskctrl-backtest-cta"]` · `[data-testid="riskctrl-export-docx-btn"]`
- **interaction**:
  - 写策略文本 → POST `/api/riskctrl/dsl_gen` SSE → 真 LLM 生成 DSL 树 → 落 ruleset_id
  - 「样本回测」CTA → POST `/api/riskctrl/backtest` SSE → KS / AUC / 通过率 / 样本分布刷新
  - DSL 树展示 4 op (IF / AND / OR / THEN) · KS 双线图 · sample stacked bars
  - 「导出回测报告 Word」 → POST `/api/riskctrl/export_docx` (后端 stub · 404 时 fallback banner) → blob → a.click() 下载
- **backend wire**: Stage C.5 backend (cb8bff1 · `agent_riskctrl/api.py` `/dsl_gen` + `/backtest`)
- **introduce**: pending Stage CF2 第 2 批 cherry-pick (2e0f49f → main · 2026-04-28)
- **lost_at**: N/A（新增 backend wiring · DSL editor / KS chart 转为 SSE 真接 + Word 导出 placeholder）
- **smoke_test**: `web/tests/regression/riskctrl-empty-state.spec.ts`（部分覆盖 · 完整 SSE + 导出待 Stage D playwright）

## F-047 · Report Workspace 空白启动 · 3 CTA + empty skeleton + status pill

- **location**: `web/src/app/archive/report/_components/ReportWorkspace.tsx` 主函数 + `ReportLaunchBar` / `ReportEmptySkeleton` / `ReportStatusPill` / `ReportLiveStrip` / `ReportLiveSections` 组件
- **selector**: `[data-view="archive-report"][data-started="no"]` (default) · `[data-testid="report-launch-bar"]` · `[data-testid="report-upload-cta"]` (primary) · `[data-testid="report-template-select"]` (secondary) · `[data-testid="report-history-dropdown"]` (tertiary · 选项标 `(示例)`) · `[data-testid="report-empty-skeleton"]` · `[data-testid="report-status-pill"][data-mode="mock|live"][data-llm-connected]` · `[data-testid="report-mock-banner"]` (started+mock 才显)
- **interaction**: empty-state-design-protocol §3 状态机 · `started` 默认 false · 不 auto-fire LLM · 上传材料 (primary) → POST `/api/report/upload` → setReportId + setStarted(true) + mode="live" · 选模板 (secondary) → setStarted(true) + mode="live" · 选历史 (tertiary) → setStarted(true) + mode="mock" · 操作按钮 (开始生成 / 导出 Word) 仅 started 时显
- **introduce**: `b014813` 2026-04-28 backend C.1 (5 endpoint mount) + W-CF-A1 frontend (`23857b0` → main · 2026-04-28)
- **lost_at**: N/A
- **smoke_test**: `web/tests/regression/report-empty-state.spec.ts` (5 case · chromium + edge 双 browser PASS)

## F-052 · Report Workspace 完整 panel + v16 backend wire

- **location**: `web/src/app/archive/report/_components/ReportWorkspace.tsx` (1700+ lines) + `web/src/lib/api/report.ts` (4 endpoint client) + 既有 panel 函数 (`ReportHero` / `ReportPipelineBand` / `TemplatePanel` / `MaterialPanel` / `TimelinePanel` / `ConversationPanel` / `ReportComposer` / `PreviewPanel`) + 新组件 (`ReportLaunchBar` / `ReportEmptySkeleton` / `ReportStatusPill` / `ReportLiveStrip` / `ReportLiveSections`)
- **selector**: 详见 F-047 testid · 加 `[data-testid="report-live-strip"][data-generating]` · `[data-testid="report-section-nav"]` · `[data-testid="report-section-active"]` · `[data-testid="report-refine-btn"]` · `[data-testid="report-generate-btn"]` · `[data-testid="report-export-btn"]`
- **interaction**: full v16 wire · 上传 → POST `/api/report/upload` (multipart 落 `data/kb/report/{report_id}/`) · 触发生成 → POST `/api/report/v16/fill` SSE (5 stage `ingest/extract/infer/write/audit` + done event 含 sections / qc / stats / pending_questions · `mock_pipeline=true` 显式标 demo) · 章节重写 → POST `/api/report/refine_section` (LLM rewrite + session writeback · 无 key 走 fallback 拼接) · 导出 → POST `/api/report/export_docx` 返 docx blob + RFC 6266 中文文件名 → `triggerDownloadBlob` 触发浏览器下载 · status pill 轮询 `/api/report/health` 显 LLM 连接态
- **introduce**: 同 F-047 (W-CF-A1 frontend `23857b0`) + backend `b014813` 2026-04-28 (5 endpoint mount)
- **lost_at**: N/A
- **smoke_test**: `web/tests/regression/report-empty-state.spec.ts` (empty + 触发) · 完整 SSE / refine / export 真路径需 backend live 验 (deferred)

---

## F-057 · AuthGate enforce real backend · 5 user RBAC + httpOnly cookie + /403 redirect

- **status**: live
- **owner**: Worker A2 (W-D1F-A2 · 复用 W-D1-A2 backend `bd143b5`)
- **goal**: 闭环 master plan §D.1 frontend (gap #10 5 user RBAC enforce 缺) · production-grade · 前端不再硬编 PASSWORD_MAP · 走 backend `auth_service/` (bcrypt + JWT + ACCESS matrix)
- **location**: `web/src/lib/api/auth.ts` (3 endpoint client) · `web/src/lib/store/auth-store.ts` (refactor backend-driven · 移除 frontend PASSWORD_MAP · 加 `bootstrap()/login(uid,pwd)/logout()` async · `accessibleAgents` 从 /me 读) · `web/src/components/shell/AuthGate.tsx` (refactor `bootstrap()` GET /me + ACCESS matrix enforce + /403 redirect) · `web/src/app/login/_components/LoginForm.tsx` (移除 PASSWORD_MAP · 调 `login(userId, password)` 真接) · `web/src/app/403/page.tsx` (新建 friendly forbid 页) · `web/src/components/shell/LogoutButton.tsx` (logout async wait) · `web/src/components/shell/PersonaSwitcher.tsx` (demo 期 password = userId.replace("u_","")) · `web/src/app/today/_components/MorningBrief.tsx` (移除 fallback login(FALLBACK_USER)) · `web/next.config.ts` (`/api/auth/*` proxy 到 AUTH_BACKEND)
- **selector**: `[data-testid="login-error-banner"]` 错误条 · `[data-testid="login-user-select"]` user 下拉 · `[data-testid="login-password-input"]` password input · `[data-testid="login-submit"]` 登录按钮 · `[data-testid="auth-403-page"]` 403 页 · `[data-testid="auth-403-back-today"]` 返 today link
- **interaction**: 用户进 protected path (e.g. `/archive/credit`) → AuthGate `bootstrap()` GET `/api/auth/me` · 200 → 拿 user + accessibleAgents · 401 → router.replace("/login") · 已登录但访问无权 archive → router.replace("/403") · LoginForm 用户填 password → `login(userId, password)` async POST `/api/auth/login` · 成功 backend Set-Cookie zhongan_auth (httpOnly · 浏览器接管) · 失败 lastError 显错误条 · LogoutButton 点击 → `logout()` async POST `/api/auth/logout` 清 cookie + redirect `/login`
- **introduce**: 2026-04-28 W-D1F-A2 worker · 配 W-D1-A2 backend `bd143b5` (auth_service/{users,jwt_util,rbac,dependencies}.py · POST /login + GET /me + POST /logout + Depends factory · 37 pytest PASS)
- **fixes**: master plan gap #10 (5 user RBAC enforce 缺 · production 必修) full stack · auth-protocol.md v1.0 §1-§7 frontend 落地 · 前端不再 view-source 看见 password (`LoginForm.tsx:35-41` PASSWORD_MAP 彻底移除)
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/auth-gate.spec.ts` (5 case · chromium 5/5 + edge 5/5 = 10/10 PASS · 未登录 redirect login + lihua credit_officer access 自身 + lihua blocked from channel + liuye admin full + logout 后 redirect)
- **依赖**: backend `auth_service/` (W-D1-A2 `bd143b5` MERGED) · 3 endpoint live · `web/next.config.ts` 加 `/api/auth/*` rewrite 到 `AUTH_BACKEND` (默认 8000) · 安全: cookie httpOnly + SameSite=Lax + 24h exp · production https 加 Secure (`AUTH_COOKIE_SECURE=true`)

## F-058 · IM WebSocket 实时 + Thread 持久化 + 6 kind 渲染 (Stage D.2F frontend)

- **location**:
  - `web/src/lib/im/websocket.ts` (ImWebSocketClient · reconnect exponential backoff · heartbeat 30s)
  - `web/src/lib/api/im.ts` (REST: listThreads / listMessages / sendMessage / markThreadRead / createThread)
  - `web/src/app/dispatch/_components/ImLiveBridge.tsx` (mount-once · fetch threads + connect ws + subscribe + pruneTyping)
  - `web/src/app/dispatch/_components/MessageStream.tsx` (WS state pill + typing indicator + history-load + mark-read)
  - `web/src/app/dispatch/_components/MessageBubble.tsx` (PinRefThumbnail · pin_ref kind 渲染缩略图卡)
  - `web/src/app/dispatch/_components/ComposerBar.tsx` (typing debounce 1s + sendMessage REST 持久化)
  - `web/src/app/dispatch/_store/dispatch-store.ts` (ingestRemoteMessage / setRemoteThreads / noteTyping / pruneTyping / liveMode + wsState)
  - `web/src/lib/store/types.ts` (ImMessage.kind 加 "pin_ref" · refs 加 agentId/href/fullText/thumbDataUrl/agentRunId · additive · Q-037 precedent)
- **selector**: `[data-testid="dispatch-view"]` · `[data-testid="im-ws-state"]` · `[data-testid="im-typing-indicator"]` · `[data-testid="im-thread-history-load"]` · `[data-testid="im-pin-ref-thumbnail"]`
- **interaction**:
  - mount: ImLiveBridge listThreads → setRemoteThreads + connect ws · fallback `live_with_seed_fallback` 兜底
  - switch thread: 自动 listMessages + ws.subscribe(tid) + markThreadRead
  - send message: optimistic local + sendMessage REST 持久化 · WS broadcast 给其他 user · ingest 时 id dedup
  - typing: ComposerBar input debounce 1s emit ws.sendTyping · 其他 user 收 → noteTyping → indicator 3s expire
  - 重连: exponential backoff (1s→30s cap) · re-subscribe 历史 thread
  - heartbeat: 30s · backend 60s timeout 安全 buffer
- **backend wire**: Stage D.2 backend (ab59186 · 7c2afaf MERGED · 14d64e1 → main · 2026-04-28)
- **contract**: `docs/contracts/im-protocol.md` v1.0 (§3 schema · §4 ws · §5 6 kind · §7 pin_ref · §10 migration)
- **introduce**: 2026-04-28 W-D2F-A3 worker (`14d64e1` → main)
- **lost_at**: N/A (新 feature · 此前 dispatch 走 polling fetch + seed only · 无 WebSocket / 无持久化)
- **smoke_test**: `web/tests/regression/im-websocket.spec.ts` (5 case · route + WS state + history-load + pin_ref + typing indicator)
- **NB**: seed 兜底 `live_with_seed_fallback` · D.1 frontend AuthGate (W-D1F-A2) 提供 cookie auth_token · 本批 fallback `getImToken()` 取 cookie/localStorage/demo

---

## F-060 · IM Send wire + pin_ref 严格 thumbnail + live-fail banner

- **status**: live
- **owner**: Worker A2 (W-FIX · 2026-04-28)
- **goal**: 修 user 报 production bug 3: (1) dispatch composer 是摆设 send fail silent · (2) 画布拖到 composer 是 url 链接 · 不是 thumbnail (违 F-008 + live-fallback-banner-spec §2 规则 4)
- **location**:
  - `web/src/app/dispatch/_components/ComposerBar.tsx` (handleSubmit `.catch` → setSendFailError + handleDrop dispatch kind="pin_ref" message · NOT setText 文本 marker)
  - `web/src/app/dispatch/_components/MessageStream.tsx` (新 ImBanners 组件 · sendFailError + wsFailSince 30s threshold)
  - `web/src/app/dispatch/_store/dispatch-store.ts` (sendFailError state + setSendFailError action + wsFailSince 自动追踪 in setWsState)
  - `web/src/app/dispatch/dispatch-im.css` (.dpx-stream-banners + .dpx-banner--err/warn ~60 行)
- **selector**: `[data-testid="im-send-fail-banner"]` send 失败 banner · `[data-testid="im-send-fail-dismiss"]` 关 banner · `[data-testid="im-ws-fail-banner"]` ws 持续 ≥ 30s fail banner · `[data-testid="im-pin-ref-thumbnail"]` (复用 F-058 · 已存) · `[data-testid="im-ws-state"]` (复用 F-058)
- **interaction**:
  - composer Enter / send button → `addMessage` optimistic local + `sendMessageRest` POST `/api/im/messages`
  - send 4xx/5xx · network error → `setSendFailError({message, code})` → 顶部 banner + dismiss button
  - 拖拽 PANEL_PIN_MIME / CARD_PIN_MIME → `addMessage` 立即创建 `kind="pin_ref"` (refs.agentId/href/fullText 来自 PanelPinPayload/CardPinPayload) → MessageBubble PinRefThumbnail 渲缩略图 · NOT setText 文本 marker · live mode 同步 `sendMessageRest` 持久化
  - ws state !== "open" 持续 ≥ 30s → ws-fail-banner 显 (1s tick 检 wsFailSince) · 自动重连 (D.2F WebSocket client 已实装 exponential backoff)
- **introduce**: 2026-04-28 W-FIX-A2-im-send-pinref worker · 复用 D.1 (sendMessage REST) + D.2F (WebSocket state · pin_ref types.ts) + D.1F (cookie 自动带)
- **fixes**:
  - master plan gap user-bug 3 (composer 摆设 + 拖拽 url 链接) production-grade 闭环
  - live-fallback-banner-spec.md §1 规则 1 (live 失败 silent ban) + §2 规则 4 (pin_ref 严格 thumbnail)
- **smoke_test**: `web/tests/regression/im-fix.spec.ts` (3 case · chromium 2 PASS + 1 skip + edge 2 PASS + 1 skip = 4/6 + 2 skip)
  - case 1 send fail banner: route mock 502 → banner 显 + dismiss button works ✓
  - case 2 pin_ref strict thumbnail: skip · seed 无 pin_ref message · 真 drag-drop e2e 留 Stage F dry-run (PinRefThumbnail render path 已 compile-verified · MessageBubble.tsx:42-47 严格 if/else)
  - case 3 ws fail banner: 验 wsState pill + banner 默认 0 (open state 不该显) ✓
- **依赖**: F-008 (拖柄 + 缩略图 base) · F-058 (D.2F WebSocket + im REST client) · D.1 backend POST /api/im/messages · cookie 自动带

---

## F-061 · Riskctrl + Alert live-fallback banner (W-FIX-A3 · live-fallback-banner-spec v1.0)

- **location**:
  - `web/src/lib/api/_live.ts` (LiveFailError class · postLive · streamSse helper)
  - `web/src/lib/api/riskctrl.ts` (runDslGen / runBacktest / exportDocx · 不 silent swap)
  - `web/src/lib/api/alert.ts` (runAlertScan / fetchHitlist / fetchDrill · 4xx/5xx 抛 LiveFailError)
  - `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx` (`liveFail` state + banner JSX)
  - `web/src/app/archive/alert/_components/AlertWorkspace.tsx` (`startScan` 真接 SSE + banner JSX + scanSessionId state)
  - `web/src/app/archive/riskctrl/riskctrl-workspace.css` (+60 LOC · `.riskctrl-live-fail-banner*`)
  - `web/src/app/archive/alert/alert-workspace.css` (+60 LOC · `.alert-live-fail-banner*`)
- **selector**:
  - `[data-testid="riskctrl-live-fail-banner"]` · `[data-testid="riskctrl-live-fail-retry"]`
  - `[data-testid="alert-live-fail-banner"]` · `[data-testid="alert-live-fail-retry"]`
  - `[data-testid="alert-workspace"][data-scan-session-id]` (scan 通时落 sessionId)
- **interaction**:
  - Riskctrl backtest: HTTP 422 root cause = backend 必填 instruction + uploaded_files (Pydantic 默认无 default factory) · frontend `runBacktest({uploadedFiles: []})` 已显式传 [] 防 422 · 失败时 banner 显 "后端 X 调用失败 (HTTP 422) · 当前显 fallback 演示数据" + retry button + body excerpt detail
  - Riskctrl dsl_gen / export_docx: 同处理 · 5xx / network / SSE error → banner
  - Alert startScan: 不再纯本地 mock toggle · `runAlertScan({forceMock: true})` 真 POST /api/alert/scan SSE · 失败 banner · 成功 setScanSessionId
  - 失败时仍渲染 fallback mock viz · 但 banner 显式标 "fallback 演示数据" · 不静默
  - retry button 重跑同一调用 · dismiss × 关 banner
- **contract**: `docs/contracts/live-fallback-banner-spec.md` v1.0 §2 规则 1-4
- **introduce**: 2026-04-28 W-FIX-A3 worker (cherry-pick → chore/l0-infra)
- **lost_at**: N/A (新 feature · 此前 silent swap mock · 用户怒"左右脑互博")
- **smoke_test**: `web/tests/regression/riskctrl-alert-fix.spec.ts` (4 case · riskctrl 422 + dsl_gen 500 + alert scan 503 + alert scan 200)
- **NB**:
  - 422 root cause 已 verify (TestClient 真打 backend) · backend Pydantic schema 严格 · 缺 uploaded_files / instruction 都返 422
  - LiveFailError 含 status / endpoint / bodyExcerpt 三字段 · banner 渲染 detail · 帮 ops 一眼看根因
  - export_docx 404 (后端未上线) 显式视为 pending · 不弹 banner · 走原 exportInfo error 状态

## F-059 · Report Live-Fallback Banner + UI fix · 模板真 wire / button 不溢出 / mock-banner align

- **location**: `web/src/app/archive/report/_components/ReportWorkspace.tsx` 内 `ReportLiveFailBanner` + `ReportMockBanner` 新组件 + `TemplatePanel` 加 `tplInputRef` + ScanCTA wrapper
- **selector**: `[data-testid="report-live-fail-banner"]` (live mode 失败顶部 alarm) · `[data-testid="report-live-fail-retry"]` + `[data-testid="report-live-fail-dismiss"]` · `[data-testid="report-mock-banner"]` (root-level role=status margin 16px 0 与 hero 对齐) · `[data-testid="report-upload-template-cta"]` (TemplatePanel 真 wire) + 跟随 `<input type="file" hidden accept=".docx,.doc">` · `[data-testid="report-scancta-wrapper"]` (max-width 480 px) · `[data-testid="report-uploaded-template-name"]`
- **interaction**: live mode 调 `/api/report/v16/fill` 或 `/api/report/upload` 4xx/5xx/network err → setLiveFailErr → 顶部 alarm 显 endpoint + status + message · 重试按钮触发 triggerV16Fill · dismiss 关闭 · "上传模板" button 真 wire hidden file input → onChange POST /api/report/upload · "模板库" button disabled + tooltip (规则 3 不允许摆设) · "生成报告" ScanCTA wrapper max-width 480 px (规则 §3 不允许 100% panel) · mock-banner 提为 root-level component · 跟 LiveFailBanner / Hero 同 margin
- **introduce**: 本批 W-FIX-A1 commit (per docs/contracts/live-fallback-banner-spec.md v1.0)
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `web/tests/regression/report-fix.spec.ts` (6 case · chromium + edge 双 browser PASS · 11/11 cross-browser)

## F-060 · 移至 audit_service · skip slot

> 本 slot 在内部记账中保留 · 实际无前端 inventory 项 (W-E1 后端 audit middleware · 前端无入口)

## F-061 · 移至 audit_service · skip slot

> 同上 · 后端 E.4 测试覆盖加固 · 前端无入口

## F-062 · Compli ForceMock Hardcode 删除 + Live-fallback banner (W-FIX2-A3 · live-fallback-banner-spec v1.0)

- **location**:
  - `web/src/lib/api/compliance.ts` (新 · runPolicyScan / runMatrixCheck / exportDocx · 复用 `_live.ts` LiveFailError + streamSse pattern)
  - `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx` (`liveFail` state + recordLiveFail/clearLiveFail + banner JSX · 删 hardcode `force_mock: true`)
  - `web/src/app/archive/compliance/compliance-workspace.css` (+62 LOC · `.compliance-live-fail-banner*`)
- **selector**:
  - `[data-testid="compli-live-fail-banner"]` (status / endpoint data-attrs)
  - `[data-testid="compli-live-fail-retry"]` (retry button)
- **interaction**:
  - **bug #5 (修)**: primary CTA「开始政策比对」之前 (Stage CF · `c75488f`) hardcode `force_mock: true` · 用户点 → 实际跑 mock policy corpus · UI 仍标 live · 静默欺骗（左右脑互博）
  - **fix**: primary path 现 `force_mock: false` · 真接后端 SSE · 失败 → live-fail banner（per spec §2 规则 1）· mock 仅 tertiary `(示例)` dropdown 显式 demo banner
  - secondary template_check 同处理: 4xx/5xx/network → liveFail banner · 不再 silent
  - export_docx 404 (Stage 未上线) 仍走 exportInfo pending error · 不弹 banner（与 riskctrl 同 fallback pattern）
- **contract**: `docs/contracts/live-fallback-banner-spec.md` v1.0 §1.5 (production / demo 路径必须显式分开) · §2 规则 1 (live failed → 显式 banner)
- **introduce**: pending W-FIX2-A3 cherry-pick
- **lost_at**: N/A (修 Stage CF `c75488f` 引入的 hardcode bug · 之前 user 投诉「左右脑互博」)
- **smoke_test**: `web/tests/regression/compli-empty-state.spec.ts` (新加 2 case · primary force_mock:false body verify + primary 503 → live-fail banner)
- **NB**:
  - 与 F-061 (Riskctrl + Alert) 同 pattern · 复用 `_live.ts` LiveFailError + streamSse
  - tertiary mock dropdown 路径 `compli-demo-banner` 已 wire (Stage CF) · 本 fix 不动
  - test runner 见 `web/tests/regression/compli-empty-state.spec.ts` · 加 case 「force_mock:false body verify」 + 「primary path 失败 → live-fail banner 显」

---

## 待补（用户暗示"还有很多其他的"）

F-009 ~ pending · 等用户继续指出 → enrich 此清单

---

## F-063 · IM Cookie Auth Chain Fix (W-FIX2-A2-im-cookie-auth · bug #8 P0)

- **status**: live
- **owner**: Worker A2 (W-FIX2 · 2026-04-29)
- **goal**: 修 Codex 找的 P0 bug #8 (IM dead 真根源 · cookie 名错): frontend `web/src/lib/api/im.ts:34` 读 `auth_token` cookie · 但 D.1 backend 真 cookie 名 `zhongan_auth` + httpOnly (JS 不可读) · 整 IM 链断 · 真 user permission fail / 401
- **location**:
  - `web/src/lib/api/im.ts` (移除 `getImToken()` 读 cookie · 全 fetch 已有 `credentials: "include"` · header 注释更新)
  - `web/src/app/dispatch/_components/ComposerBar.tsx` (`/api/im/send` fetch 加 `credentials: "include"`)
  - `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (`/api/im/send` fetch 加 `credentials: "include"`)
  - `im_service/auth.py` (新 helper `decode_jwt_cookie(zhongan_auth)` 走 `auth_service.jwt_util.verify` 严格 D.1)
  - `im_service/websocket.py` (`im_websocket_endpoint` 加 `cookie_token` 参数 · cookie 优先 · query token fallback)
  - `api_server.py` (`_resolve_im_user(zhongan_auth, authorization, token_q)` 三 source 优先级 · 6 IM endpoint signature 加 `zhongan_auth: str | None = Cookie(default=None)` · WS endpoint 读 `websocket.cookies["zhongan_auth"]`)
- **selector**: 后端无新 testid · 验证走 cookie jar (`zhongan_auth=...` httpOnly · curl `-b jar.txt`)
- **interaction**:
  - 真 user 流程: POST `/api/auth/login` → backend Set-Cookie `zhongan_auth=<JWT>` httpOnly · browser 自动 store · 后续所有 IM fetch `credentials: "include"` 自动带 cookie · backend `_resolve_im_user` 优先 `decode_jwt_cookie` (D.1 jwt_util.verify HS256) · 成功立即 hit 真 user_id
  - demo / e2e 流程: 无 cookie / cookie 无效 · fallback Authorization Bearer (含 `demo-u_<id>` legacy 格式) · 不影响 production
  - WebSocket: same-origin 自动带 cookie · `/ws/im` 优先 cookie · 失败回退 `?token=<jwt>` query (legacy / 非 same-origin)
  - 6 endpoint 清单 (per onboarding W-FIX2-A2-im-cookie-auth.md §Acceptance):
    POST `/api/im/messages` · GET `/api/im/threads` · GET `/api/im/threads/{tid}/messages` ·
    POST `/api/im/threads/{tid}/read` · POST `/api/im/threads` (create) ·
    POST `/api/im/send` (legacy · cookie param 兼容 · 不强制) · WS `/ws/im` (cookie 优先)
- **contract**: `docs/contracts/auth-protocol.md` v1.0 §5 cookie spec (zhongan_auth · httpOnly · SameSite=Lax · 24h) · `docs/onboarding/W-FIX2-A2-im-cookie-auth.md`
- **introduce**: 2026-04-29 W-FIX2-A2 worker (cherry-pick → chore/l0-infra)
- **lost_at**: N/A (新 fix · 此前 frontend 读错 cookie 名导致 IM auth dead)
- **smoke_test**:
  - `im_service/tests/test_cookie_auth.py` 12 case PASS (decode_jwt_cookie 单元 4 + REST endpoint 8 含真 D.1 cookie / cookie 优先 / fallback Bearer / expired cookie / 缺 cookie + Bearer / 全无效 / messages 完整流 / mark_read)
  - im_service/tests/ 全套 61 PASS · auth_service/tests/ 全套 43 PASS · 无回归
  - curl smoke 三 path verified: `POST /api/auth/login` → cookie jar 有 `zhongan_auth` (httpOnly) · `GET /api/im/threads` 仅带 cookie 返 200 + `user_id=u_wangzhe` (真 user · 不是 demo fallback) · 缺 cookie 返 401 MISSING_TOKEN · demo Bearer fallback 仍接受
- **NB**:
  - 不增 `/api/im/token` endpoint (Codex 建议过度工程) · 不增 IM-specific token 概念 · 复用 D.1 cookie + jwt_util
  - cookie 优先级原则: 真 D.1 JWT 命中 > Authorization Bearer (含 demo) > query token · 任一成功立即返 · 不进 fallback
  - frontend `getImToken()` 仍保留 (作 demo / e2e localStorage fallback) · 但不再 reach for `document.cookie` (httpOnly 不可读)
  - `/api/im/send` legacy LLM 单 turn endpoint 加 cookie param signature 但不强制 (向后兼容)

## F-064 · Alert 命中清单 Word 导出 + live-fail banner (W-FIX2 修 bug #6)

- **location**: `web/src/app/archive/alert/_components/AlertWorkspace.tsx` 内 `handleExportDocx` + 顶部 export-error banner + HeroSection 内 `导出命中清单 (.docx)` button (phase=after 才显) · backend `agent_alert/word_export.py` (新建) + `agent_alert/api.py` 加 `POST /api/alert/export_docx`
- **selector**: `[data-testid="alert-export-docx-cta"]` (HeroSection 内 export 按钮) · `[data-testid="alert-export-error-banner"]` (live fail 顶部红 banner role=alert) · `[data-testid="alert-export-error-retry"]` · `[data-testid="alert-export-error-dismiss"]`
- **interaction**: phase=after 显 "导出命中清单 (.docx)" → POST `/api/alert/export_docx` (session_id + summary + cases + totals + scan_range + stage) · 200 → blob download 触发浏览器下载 · 4xx/5xx/network err → setExportError(msg) → 顶部 banner 显 endpoint + 错误信息 · retry 重发 · dismiss 关 banner · 不静默 console-only (live-fallback-banner-spec v1.0)
- **introduce**: 本批 W-FIX2-A1 commit · 修 Codex peer review bug #6 (silent fail · backend route 缺失)
- **lost_at**: N/A
- **restored**: N/A
- **smoke_test**: `agent_alert/tests/test_export_docx_endpoint.py` (4 case · TestClient · 200 + Content-Type docx + Content-Disposition RFC 6266 + zip magic) · `agent_alert/tests/test_word_export.py` (33 case docx render 各分支)

---

## F-062 · IM Cookie Auth Chain Fix (W-FIX2-A2-im-cookie-auth · bug #8 P0)

- **status**: live
- **owner**: Worker A2 (W-FIX2 · 2026-04-29)
- **goal**: 修 Codex 找的 P0 bug #8 (IM dead 真根源 · cookie 名错): frontend `web/src/lib/api/im.ts:34` 读 `auth_token` cookie · 但 D.1 backend 真 cookie 名 `zhongan_auth` + httpOnly (JS 不可读) · 整 IM 链断 · 真 user permission fail / 401
- **location**:
  - `web/src/lib/api/im.ts` (移除 `getImToken()` 读 cookie · 全 fetch 已有 `credentials: "include"` · header 注释更新)
  - `web/src/app/dispatch/_components/ComposerBar.tsx` (`/api/im/send` fetch 加 `credentials: "include"`)
  - `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (`/api/im/send` fetch 加 `credentials: "include"`)
  - `im_service/auth.py` (新 helper `decode_jwt_cookie(zhongan_auth)` 走 `auth_service.jwt_util.verify` 严格 D.1)
  - `im_service/websocket.py` (`im_websocket_endpoint` 加 `cookie_token` 参数 · cookie 优先 · query token fallback)
  - `api_server.py` (`_resolve_im_user(zhongan_auth, authorization, token_q)` 三 source 优先级 · 6 IM endpoint signature 加 `zhongan_auth: str | None = Cookie(default=None)` · WS endpoint 读 `websocket.cookies["zhongan_auth"]`)
- **selector**: 后端无新 testid · 验证走 cookie jar (`zhongan_auth=...` httpOnly · curl `-b jar.txt`)
- **interaction**:
  - 真 user 流程: POST `/api/auth/login` → backend Set-Cookie `zhongan_auth=<JWT>` httpOnly · browser 自动 store · 后续所有 IM fetch `credentials: "include"` 自动带 cookie · backend `_resolve_im_user` 优先 `decode_jwt_cookie` (D.1 jwt_util.verify HS256) · 成功立即 hit 真 user_id
  - demo / e2e 流程: 无 cookie / cookie 无效 · fallback Authorization Bearer (含 `demo-u_<id>` legacy 格式) · 不影响 production
  - WebSocket: same-origin 自动带 cookie · `/ws/im` 优先 cookie · 失败回退 `?token=<jwt>` query (legacy / 非 same-origin)
  - 6 endpoint 清单 (per onboarding W-FIX2-A2-im-cookie-auth.md §Acceptance):
    POST `/api/im/messages` · GET `/api/im/threads` · GET `/api/im/threads/{tid}/messages` ·
    POST `/api/im/threads/{tid}/read` · POST `/api/im/threads` (create) ·
    POST `/api/im/send` (legacy · cookie param 兼容 · 不强制) · WS `/ws/im` (cookie 优先)
- **contract**: `docs/contracts/auth-protocol.md` v1.0 §5 cookie spec (zhongan_auth · httpOnly · SameSite=Lax · 24h) · `docs/onboarding/W-FIX2-A2-im-cookie-auth.md`
- **introduce**: 2026-04-29 W-FIX2-A2 worker (cherry-pick → chore/l0-infra)
- **lost_at**: N/A (新 fix · 此前 frontend 读错 cookie 名导致 IM auth dead)
- **smoke_test**:
  - `im_service/tests/test_cookie_auth.py` 12 case PASS (decode_jwt_cookie 单元 4 + REST endpoint 8 含真 D.1 cookie / cookie 优先 / fallback Bearer / expired cookie / 缺 cookie + Bearer / 全无效 / messages 完整流 / mark_read)
  - im_service/tests/ 全套 61 PASS · auth_service/tests/ 全套 43 PASS · 无回归
  - curl smoke 三 path verified: `POST /api/auth/login` → cookie jar 有 `zhongan_auth` (httpOnly) · `GET /api/im/threads` 仅带 cookie 返 200 + `user_id=u_wangzhe` (真 user · 不是 demo fallback) · 缺 cookie 返 401 MISSING_TOKEN · demo Bearer fallback 仍接受
- **NB**:
  - 不增 `/api/im/token` endpoint (Codex 建议过度工程) · 不增 IM-specific token 概念 · 复用 D.1 cookie + jwt_util
  - cookie 优先级原则: 真 D.1 JWT 命中 > Authorization Bearer (含 demo) > query token · 任一成功立即返 · 不进 fallback
  - frontend `getImToken()` 仍保留 (作 demo / e2e localStorage fallback) · 但不再 reach for `document.cookie` (httpOnly 不可读)
  - `/api/im/send` legacy LLM 单 turn endpoint 加 cookie param signature 但不强制 (向后兼容)

---

## F-065 · Channel pilot 4-gate state model + done envelope 7 panels + Tavily warn (Phase A worker-A3)

- **location**:
  - frontend: `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (4-gate useState · `started` / `selectedSession` / `liveData` / `selectedCandidate` · `sessionData` 单点派生 · `normalizeBackendDone` · `streamSse` 接 `_live.ts` · `bannerKind` info|error)
  - backend: `agent_channel/realtime_stream.py` (`make_done(panels=...)` + 6 aggregator helper · `warnings` 收集 · stage status=warning event yield)
- **selector**:
  - `[data-testid="channel-pilot-{radar,funnel,candidates,signals,conversation}"]` 5 panel section root
  - `[data-testid="channel-pilot-banner-mock-fallback"]` (info 黄 · `data-banner-kind="info"`) · `[data-testid="channel-pilot-banner-live-fail"]` (error 红 · `data-banner-kind="error"`)
  - `[data-mode="live"|"mock"]` on `[data-testid="channel-pilot-candidates"]`
- **interaction**:
  - 默认 `started=false` · 渲染等待提示
  - 选下拉历史 session + 切换演示 → setSelectedSession + setStarted(true) → 5 panel 全 swap (mock 模式)
  - 自由文本 + AI 搜索 → streamSse `/api/channel/run` → done envelope 扁平 7 panels → normalizeBackendDone → setLiveData → 5 panel 全 swap to live
  - LiveFailError → bannerKind=error · 红 banner (banner-spec rule 1)
  - backend stage status=warning OR done.warnings non-empty → bannerKind=info · 黄 banner (banner-spec rule 2)
  - 候选 click → setSelectedCandidate → CandidateDetailDrawer · ESC 关
- **introduce**: 2026-04-29 Phase A worker-A3 channel pilot (`docs/onboarding/A3-channel-pilot.md` · `docs/onboarding/A3-design-draft.md`)
- **lost_at**: N/A (新 feature · 接 Cat 2/3/4/11 channel audit fix · `docs/audit/conflict-register-v1.md`)
- **endpoints**:
  - `POST /api/channel/run` 升 SSE done event 形态 · 改用 `shared.sse_envelope.make_done(panels=...)` (扁平 7 panel · 与 V2 helper 实装对齐)
  - `POST /api/channel/demo/run` (新 · 见下 F-066)
- **contract**:
  - `docs/contracts/workspace-state-protocol.md` v1.1 §2 4-gate state model · §4 后端 SSE done payload · §10 AgentSession shape
  - `docs/contracts/sse-envelope.md` v1.0 §3.1 Channel payload tail
  - `docs/contracts/live-fallback-banner-spec.md` v1.0 §2 rule 1 + rule 2
  - `shared/sse_envelope.py` `CHANNEL_PANEL_KEYS = (candidates, signals, radar, funnel, match_dimensions, product_recommendations, pitch_scripts)`
- **smoke_test**: `web/tests/regression/channel-pilot-4gate.spec.ts` (4 case · T1 mock session + T2 live envelope + T3 candidate drawer + T4 banner-spec rule 2 · 4/4 PASS chromium 19.5s)
- **NB**:
  - V1 spec sse-envelope §2.1 描述嵌套 envelope 但 V2 helper `make_done` 实装为扁平 (panels expand 顶层) · A3 跟 V2 实装走 (drift 详情 `docs/onboarding/A3-design-draft.md` §3)
  - `warnings` 走 `**extras` 通道塞 done envelope 顶层 (A2 helper 不 first-class warnings param · A2 V2.1 升级时再 promote)

## F-066 · /api/channel/demo/run + 3 scenario JSON (Phase A worker-A3)

- **location**: `agent_channel/api.py` (`channel_demo_run` endpoint + `_SCENARIO_DIR`) + `data/mock/workspace/channel/scenarios/{easy,medium,hard}.json`
- **interaction**:
  - 前端 POST `/api/channel/demo/run` body `{scenario_id: "easy"|"medium"|"hard"}` (默认 medium)
  - 后端读 `<scenarios>/<id>.json` · 6 stage running/done 流 (parse/signal_scan/aggregate/enrich/pitch/rank · 各 0.25s sleep) · 末尾 `make_done(panels=7, data_source="mock_forced")`
  - scenario 文件不存在 / 加载失败 / id 非法 → `make_error(code=DEMO_SCENARIO_{INVALID,MISSING,LOAD})`
- **introduce**: 2026-04-29 Phase A worker-A3
- **lost_at**: N/A (新 endpoint · 与 live `/api/channel/run` 路径分开 · 客户走访稳定 demo 路径)
- **contract**: `shared/sse_envelope.py make_done` + `workspace-state-protocol.md` §4 (frontend 同消费路径)
- **scenario data 反 5 原则** (CLAUDE.md §3.5):
  - easy (信号密度高 · 3 候选 · radar 全亮 · metrics signalTotal=42 final=8)
  - medium (中等 · 3 候选 · radar 半亮 · 1 路降级 1 路 off · metrics signalTotal=21 final=5)
  - hard (稀疏 · 3 候选 · 多家风险标签 · 2 路 off 1 路降级 · metrics signalTotal=11 final=3)
  - 锚定 A 股年报 + 工信部 + 银保监公告形态 · 改名改数字保量级 · 不含答案字段
- **smoke_test**:
  - `python -c "..."` in-process: easy/medium/hard 各 12 stage + 1 done + 7/7 panels · INVALID 1 error code=DEMO_SCENARIO_INVALID
  - Playwright T2/T4 走 page.route 注入 (UI demo button wire 后再加专属 spec)
- **NB**:
  - UI 上的 "demo run" 按钮尚未 wire (deferred · 留待客户演示场景明确后定 popover UX)
  - scenario JSON 是 SSOT · 视觉调整 / 文案改 / 难度档调 → 改 JSON 即可 · 不需重启后端

---

## 维护规则

1. **新 feature 落地必须加 entry**·worker 在 commit message 内 trailer `INVENTORY-ADDED: F-XXX`
2. **修复回档必须更新 entry**·trailer `RESTORED: F-XXX <commit_hash>`
3. **改 web/ 不动 inventory feature**·trailer `PRESERVES: F-001, F-005, ...` 列保留 id
4. **smoke test 写完后**·把 `pending` 替换为实际路径
5. **每周巡检**：grep `web/` 找未列入 inventory 的 critical interaction（按钮 / 拖拽 / 跳转）补 entry
