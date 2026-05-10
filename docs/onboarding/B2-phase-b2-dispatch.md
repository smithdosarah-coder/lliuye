# Phase B.2 派活 · 6 worker 通用 brief (PM 2026-05-10 真意 reframe)

## PM 真意 (verbatim 02:00 AM)

> "我要的演示不是一键切换 · 而是把本地的 mock 数据真实上传 · 通过真实后端代码跑一遍 · 最后给出结果"

= 演示 ≠ ModePill 切假数据 (Phase A.6 + B.1 fix #2-#7 错方向 · 已 revert)
= 演示 = 上传 sample 文件 → **真后端 pipeline** (LLM/Tavily/算法不变) → 真返结果
= mock **只能 mock 输入** · 不能 mock 结果

## 优质 mock batch (用这个 · 不要简单档)

| Agent | 内部优质 batch (输入) | 外部源 (改真) |
|---|---|---|
| channel | `data/mock/channel-kb/` (历史成交 + 营销倾向 + 产品目录) | Tavily 真搜 + 8 源 |
| report | `data/mock/deep-pillar/DP001_龙峰精工/` (真材料 PDF/xlsx/docx) | 无 |
| credit | `data/mock/deep-pillar/DP001_龙峰精工/` | 无 |
| alert | `data/mock/alert-pool/` (clients.csv + external-signals/ + transactions/) | Tavily 真接 |
| compliance | `data/mock/compliance-kb/` (制度 SOP/KYC/风偏) + sample 政策 | Tavily 真接 |
| riskctrl | `data/mock/agent2-samples/loans.csv` (7500 行 · MAX_ROWS=50000) | 无 |

**禁止用**: `data/mock/workspace/<x>/scenarios/easy.json` 等 (v1 简单清洗版 · 答案给嘴边 · 反 5 原则违)

## codex 复盘 5 漏项 (你必须真闭环)

1. 不只删 ModePill · **全仓审计** fixtures.ts / demo_mode / 假候选 / 假评分 / 假结论
2. sample 不是 UI 资产 · **是输入契约** (manifest.json schema)
3. **加"形态切换" toggle** (不是 ModePill 切假 · 是输入来源切换 · backend 都真跑)
4. 必须 admin 真号 E2E 留证据 (录屏/截图/HAR/run log 4 件套)
5. mock 只能 mock 输入 · **不能 mock 结果**

## 4 主活 (per agent · 看你自己的 B2-<X>.md 取详细)

A. **`/api/<x>/demo/run` 改真后端跑** (不再 yield fixture event)
B. **`<X>Workspace.tsx` 加形态切换 toggle** (真实 default · demo 自动加载优质 batch)
C. **空状态 + 排版 + 错误降级 redesign** (PM 截图痛点)
D. **admin 真号 E2E 4 件套** (commit trailer `E2E_EVIDENCE_URL: <link>` 必带)

## 11 step 硬规

0. **PM 真意复述** (3-5 句 fire `RESUMED` commit · 等主 CLI verify · 不复述 REJECT)
1. PM 真意确认 (Step 0 已做)
2. /demo/run 真跑 backend (主活 A)
3. UI 形态切换 (主活 B)
4. UI 空状态/排版/错误态 (主活 C)
5. 错误降级 (NotImplementedError / API key missing / Tavily down 显 typed banner · 不 silent · 不 fallback fake)
6. §3.5 表 (per agent 内部 mock 保留 · 外部源改真)
7. 信息密度 (折叠 default 改展开 · 主 CTA 突出 · 大空白填示例)
8. unique id (per candidate-identity-contract v1.1 · 无 regression)
9. evidence drawer 真 wire (live 数据触发 · grep <X>_EVIDENCE 0 命中)
10. ledger 上链 (per CLAUDE.md §3.7.5)
11. admin E2E 4 件套 (主活 D · commit trailer 必带)

## 不可 GO 条件 (任 1 触发主 CLI REJECT 不 cherry-pick)

- `/demo/run` 仍 `yield fixture_event` (后端不真跑)
- `fixtures.ts` 任何 import (前端假证据)
- `ModePill` 残留 (错设计未删)
- silent fallback fake 数据
- `NotImplementedError` 任何运行路径 raise
- channel 单 Tavily 无降级 banner
- 评分都一样 (3 候选 1 评分 · 没 LLM 抽字段)
- 47 分 D 级假分残留 (credit)
- 监管条款无 hash (compliance · ViolationReason 缺 clause_text_hash)
- **无 `E2E_EVIDENCE_URL` trailer** (commit 不带 E2E 4 件套 = 不 cherry-pick)

## fire signal 模板

```
chore(mesh): signal worker <X> Phase B.2 ready

Worker: <X>
Phase: B.2
Refs: ALLIN-2026-05-10
Signal: READY
Root: 40f881f
E2E_EVIDENCE_URL: <link>
```

body 7 段 (per signal-commit-contract §2): 完成摘要 / 改文件清单 / 测试 verify / 红线自检 10 条 / 依赖合同 / base dashboard 行 / 证据

## 撞 BLOCKER 立刻 fire

```
chore(mesh): signal worker <X> Phase B.2 BLOCKED

Worker: <X>
Phase: B.2
Refs: ALLIN-2026-05-10
Signal: BLOCKED
具体卡点: <自然语言>
```

主 CLI 收 BLOCKED 立刻仲裁。
