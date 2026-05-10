# Phase B.2 channel · admin 真号 E2E runbook (PM 2026-05-10)

> **Status**: ⏳ 待 PM/admin 在 production (https://liuye.me) 真号执行 · 留 4 件套证据
> **Owner**: 主 CLI / PM (worker 无 production admin 凭证)
> **Refs**: dispatch `docs/onboarding/B2-phase-b2-dispatch.md` 主活 D · §11

## 4 件套要求 (per dispatch §不可 GO)

每次产品演示完必须有以下 4 件 evidence · 缺任一 = 不 cherry-pick:

1. **录屏** · 完整流程录屏 (≥ 60s · mp4/webm)
2. **截图** · 关键画面 (~ 8 张 · png)
3. **HAR** · 浏览器 dev tools Network → Save all as HAR
4. **run log** · backend uvicorn stderr (≥ 30 行 · 含 SSE 输出)

证据上传到 `data/handoff/e2e/<date>/<phase>-<agent>/` · commit trailer `E2E_EVIDENCE_URL: <link>`

## E2E 流程 (admin · production)

### 准备

- 浏览器 Chrome · 开 DevTools Network → Preserve log + Disable cache
- 录屏工具开始 (OBS/Mac 内置 / Win+G)
- 终端连 ECS · `ssh ecs && journalctl -u uvicorn -f` 留 backend log

### Step 1 · 登录 + 切到 channel workspace

1. 访问 https://liuye.me
2. admin 真号登录 (邮箱 + 密码)
3. 进 `/archive/channel` workspace
4. **截图 1** · channel workspace 首屏 (双形态空状态 grid 2 列对照)

### Step 2 · 验形态切换 toggle (主活 B)

1. 默认 free 形态 active · 顶部 segmented control "自由查询" 高亮
2. 点 "一键示例" tab · sample 形态进入
3. **截图 2** · sample 形态展开 · 3 难度 button 可见 + channel-kb 描述

### Step 3 · 真后端跑 demo · 验真接 Tavily/AI (主活 A · 核心)

1. 点 "运行示例 · 中等" 难度 button
2. 等待 SSE 流跑完 (~ 10-30s)
3. **截图 3** · 实时流面板 · 显 "/api/channel/demo/run · 真后端跑 channel-kb 派生 query"
4. **截图 4** · demo_context 区域 · 显 sample 文件名 (e.g. `2026-Q2-区域重点.docx`) + 派生 seed query
5. **截图 5** · 候选 panel 真候选企业 · live data_source badge 显 "live" + provider="tavily"
6. **截图 6** · 候选 detail drawer 打开 · 显真信号 + Tavily 真 source URL

### Step 4 · 验 evidence drawer 真 wire (§9)

1. 候选选中后 drawer 内 evidence trail 真渲染 · 不空
2. **截图 7** · evidence drawer 显 live 派生证据 (signal source · 不再"福鼎明辉"硬编)

### Step 5 · 验 ledger 上链 (§10)

1. 选定候选点 "移交授信" / handoff button
2. 后端 ledger 写入 · 走 `/api/channel/handoff` · 自动上链
3. 验 ledger:
   ```bash
   ssh ecs
   sqlite3 data/ledger/decisions.sqlite "SELECT decision_id, agent_id, endpoint, retention_class, jurisdiction FROM ledger WHERE agent_id='channel' ORDER BY created_at DESC LIMIT 5;"
   ```
4. **截图 8** · ledger query 结果 · 含 retention=short / jurisdiction=HQ / subject_id 16hex hash

### Step 6 · 验错误降级 typed banner (§5)

1. 临时 unset TAVILY_API_KEY (ECS env override · 仅测试)
2. 重跑 demo · 应显 typed banner `TAVILY_KEY_MISSING_FOR_DEMO`
3. **截图 9 (可选)** · banner 内容 + 不应有 mock_fallback 假数据
4. 恢复 TAVILY_API_KEY

### Step 7 · 收尾

1. DevTools Network 全选 right-click → "Save all as HAR"
2. 录屏停 · 导出 mp4
3. backend log Ctrl+C 停 · 截 ≥ 30 行到 `run.log`
4. 上传 4 件套到 `data/handoff/e2e/2026-05-10/B2-channel/`
5. PR 描述加 `E2E_EVIDENCE_URL: <git URL>`

## 自动化 spec 配套

worker CLI 已写好 Playwright E2E spec (mock backend · 验前端流):
- `web/tests/regression/channel-phase-b2-real-backend.spec.ts` (4 case)

CI 跑通即代表前端形态切换 + endpoint wiring 正确 · 但**不**等于 production 真 admin E2E.
两者是互补 evidence:
- Playwright = 自动化前端流 verify (CI)
- admin 真号 = production 真 backend + 真 LLM/Tavily 全链路 verify

## 不可 GO 检查清单

`E2E_EVIDENCE_URL` 必带 · 缺任一 4 件套 = 不 cherry-pick:

- [ ] 录屏 mp4/webm (≥ 60s 完整流)
- [ ] 截图 8-9 张 png (workspace + 形态 + demo_context + candidates + drawer + ledger)
- [ ] HAR 文件 (浏览器 dev tools 导出)
- [ ] backend run.log (uvicorn stderr ≥ 30 行)
- [ ] PR/commit trailer `E2E_EVIDENCE_URL: <link>` 显式带

## 已验证证据 (worker CLI 可证)

worker 已自动验证以下 (无需 admin 真号):

- pytest tests/agent_channel: **241 passed · 1 skipped** (Tavily env)
- 新增 backend smoke: 6 (demo_run real_backend) + 6 (candidate_identity) + 3 (ledger) + 3 (evidence_drawer) = 18 case
- tsc --noEmit: **EXIT=0 · 0 errors**
- Playwright spec: 4 case 写好 (CI 待跑)

production 真 E2E 4 件套留待 PM/admin 执行 · 上链 trailer 后即可 cherry-pick。
