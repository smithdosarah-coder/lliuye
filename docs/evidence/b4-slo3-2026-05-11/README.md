# B.4 SLO-3 · 36 bug 修 evidence (deferred to main CLI)

**Worker**: fix-indep · feat/b34-fix-indep
**Date**: 2026-05-11 (PM 12:55 GO)
**Base**: origin/main `59d32fd` (C1-C4 通病 `9578c98`)
**Status**: 36/36 bug shipped · 6 agent done signals fired · 等主 CLI cherry-pick + Playwright 截图

## artifact 要求 (PM 硬要求)

每 agent done · main CLI 跑:
1. `cd web && npm run dev` (起 dev server)
2. Playwright 跑 `web/tests/regression/*-empty-state.spec.ts` (regression check · 不破)
3. Playwright 跑 visual snapshot · 6 agent `/archive/<agent>` idle 截图
4. Diff before vs after (before = 主 CLI 02:45-02:49 selfreview-*.jpg) 
5. PNG 落 `docs/evidence/b4-slo3-2026-05-11/<agent>-after.jpg`

## before 截图来源

主 CLI 主 worktree `D:/claude code/credit_report_agent_work/`:
- selfreview-channel-idle.jpg (02:45)
- selfreview-credit-idle.jpg (02:46)
- selfreview-alert-idle.jpg (02:46)
- selfreview-compliance-idle.jpg (02:47)
- selfreview-report-idle.jpg (02:48)
- selfreview-riskctrl-idle.jpg (02:49)

## after 截图 (待主 CLI 跑 Playwright 后填)

```
docs/evidence/b4-slo3-2026-05-11/
├── README.md (本文档)
├── channel-after.jpg (待主 CLI)
├── credit-after.jpg (待主 CLI)
├── alert-after.jpg (待主 CLI)
├── compliance-after.jpg (待主 CLI)
├── report-after.jpg (待主 CLI)
└── riskctrl-after.jpg (待主 CLI)
```

## verify 检查清单 (主 CLI cherry-pick 后 + dev server 跑)

### channel
- [ ] KB 3 zone 等高 + 选择文件 btn 同一基线 (bug-1)
- [ ] QUERY panel 跟 KB panel padding/margin 一致 (bug-2)
- [ ] 自由查询 / 一键示例 toggle 字号一致 (bug-3)
- [ ] completion-hint 是完整卡片 · 有 eyebrow + border (bug-4)
- [ ] 形态 A/B section padding/margin 跟上方 panel 对齐 (bug-5)

### credit
- [ ] 板块 tabs 在 top-right 角 · 跟 hero eyebrow 同视觉行 (bug-1)
- [ ] 演示 CTA panel 撑满 100% width (bug-2)
- [ ] 4 占位卡真 2x2 (radar/redlines 上 · cases/advice 下) (bug-3)
- [ ] advice 卡 grid-column auto · 跟其他 3 卡同尺寸 (bug-4)
- [ ] status pill ok+板块 左 · 等待主操作 右 (bug-5)
- [ ] 导出 docx btn 独立行 · 不 inline (bug-6)

### alert
- [ ] CTA row 2 col 撑满 (主操作 + 次操作 100%) (bug-1)
- [ ] 3 traffic light cards (红/黄/绿) 横向填满 (bug-2)
- [ ] HitList skel-row 跟 CTA row 宽一致 (bug-3)
- [ ] SignalMap card min-height 120 跟 traffic 卡视觉重量平衡 (bug-4)
- [ ] status pill 等待主操作 在右 (bug-5)
- [ ] HitList 2 slot 占位行 (TOP 1 红 + TOP 1 黄) (bug-6)
- [ ] 导出榜单 docx btn 独立行 (bug-7)

### compliance
- [ ] hero eyebrow/title/sub 左列 · stats 紧贴右列 (无 1000px 空白) (bug-1)
- [ ] QC chips block/warn/info 各 tone 颜色分隔 (不再 "000") (bug-2)
- [ ] stat labels 11px + left border 2px compli tone (bug-3)
- [ ] trigger-bar 撑满父宽 + "次要触发" label ::before (bug-4)
- [ ] 4 占位卡 padding 14/16 + min-height 72 (bug-5)
- [ ] 等待触发巡检 hint 文字 text-align center (bug-6)

### report
- [ ] stats 破折号 14px 弱化 + labels 11px 加大 (bug-1)
- [ ] 等待触发 panel 高 280-320px (不再 720px) (bug-2)
- [ ] "真 LLM..." 在 sample row 下方 footnote (不再 floating 右端) (bug-3)
- [ ] 5 标签 "PDF / Word / Excel / 图片 / 多文件" 全 " / " 分隔 (bug-4)
- [ ] 开始生成 column 有 "执行" label · 4 column 视觉对齐 (bug-5)
- [ ] 5 sample btn flex 1 平均分宽 · 撑满 row (bug-6)

### riskctrl
- [ ] hero stats 紧贴右 (无 1000px 空白) (bug-1)
- [ ] 4 占位卡 verify 2x2 已生效 (bug-2)
- [ ] empty panel 内容紧凑 · padding 减半 (bug-3)
- [ ] trigger-bar align-items center · toggle/CTA 垂直居中 (bug-4)
- [ ] verify integral page width 100% (C2) (bug-5)
- [ ] status pill ◉ 服务正常 + backend tech + 等待主操作 (bug-6)

## regression spec 必跑 (主 CLI verify)

主 CLI cherry-pick 后必跑:
```bash
cd web
npm run test:snap -- channel-empty-state.spec.ts
npm run test:snap -- credit-empty-state.spec.ts
npm run test:snap -- alert-empty-state.spec.ts
npm run test:snap -- alert-idle-fill.spec.ts  # B.3.4 主活A spec
npm run test:snap -- compliance-empty-state.spec.ts
npm run test:snap -- report-empty-state.spec.ts
npm run test:snap -- riskctrl-empty-state.spec.ts
```

预期: 全部 PASS (本批次仅改 CSS + 少量 TSX 文字/结构 · 不破坏既有 testid 或主流程)

## Cross-reference

- 跟踪表: `docs/working/b4-slo3-bug-list-2026-05-11.md`
- 主 CLI dispatch: `59d32fd`
- 主 CLI 通病 base: `9578c98` (idle-tight.css C1-C4)
- B.3.4 fix-indep evidence (前批 · 沿用模式): `docs/evidence/b34-fix-indep-2026-05-11/README.md`
- 36 bug 全 commit hash 见跟踪表 commit 列
