# Phase 3-Final · 轨 6 · L3 POC 证据链 Onboarding

**状态**：Phase 3-Final GO（**Wave 3 起 · 硬依赖轨 4 frontend-integration 完成**）
**发布日期**：2026-04-25
**Signal 入口**：`PHASE-3-FINAL-T6-ACK`
**前置**：轨 4 `READY-FOR-FRONTEND-INTEGRATION-REVIEW` APPROVED merged + 轨 1/2/3 全 merged + Q-032
**参照决策**：`docs/handoff/decisions-log.md` Q-032 + `docs/handoff/session-2026-04-25-phase-3-final-handoff.md` §4.6 + `docs/scorecard/dod-current-status-2026-04-24.md` §2.4 L3 + §2.1 L0-12/L0-13
**worker 建议**：新建 worktree `code-poc-evidence`（fork from `chore/l0-infra` · 新分支 `feat/poc-evidence` · Wave 3 dispatch）
**Final Signal**：`READY-FOR-POC-EVIDENCE-REVIEW`
**中间 signal 链**：`POC-EVIDENCE-ACK` → `E2E-3-PATHS-DONE` → `SCREENSHOT-3-PATHS-DONE` → `P95-LOAD-TEST-DONE` → `OPS-DOCS-DONE` → `READY-FOR-POC-EVIDENCE-REVIEW`

---

## 1. 背景与目标

DoD L3 客户 POC 当前 45% · Phase 3-F 目标 85%。轨 1/2/3/4 合流后产品功能齐，**真正卡 L3 的是"证据链"**——客户演示 / RFP 提交时必须给：

| DoD 条 | 缺什么 | 本轨产 |
|---|---|---|
| L3-9 关键路径 E2E ≥ 3 | Playwright 脚本 + 跑通记录 | Task A |
| L3-10 截屏留证 ≥ 3 | 起点/过程/终点截屏 | Task B |
| L0-12 P95 延时 ≤ 1.5s | load test 报告 | Task C |
| L0-13 运维文档 起/停/监/回 | 4 份 ops md | Task D |
| L3-5 P95 首字延时 | 同 L0-12 一并产 | Task C 兼 |

**硬依赖轨 4**：E2E 跑需要完整前端 + 后端联调（Stage 2 EvidenceTrail + Stage 3 dispatch IM + Stage 4 hero polish 全合后才能跑跨 Agent 联动 E2E）。**Wave 3 dispatch · 不能与 Wave 2 并行**。

**硬边界**：本轨产物全在 `docs/` + `web/tests/e2e/` + `scripts/` 域内。**不动**：`agent_*/` / `shared/` / `web/src/` 业务代码 / `v16_*.py` / `evaluation/runner/` / 红区文件。

---

## 2. Task 清单

### Task A · Playwright E2E × 3 关键路径

**目标**：3 条核心业务路径 E2E 自动化跑通 · 每条覆盖跨 Agent 联动 / 单 Agent 完整闭环 / 数据导出闭环。

**3 条路径**：

#### A-1 · Agent6 → Agent3 → Agent5 跨 Agent 联动
- 入口：`/archive/report` workspace
- 步骤：上传材料 → Agent6 生成 ReportJSON → 点 "推送给 Agent3" handoff button → Agent3 决策（四维评分 + 红线检查）→ 点 "送合规复核" → Agent5 政策冲突扫描
- 终点：Agent5 输出冲突清单 · L1-11 联动闭环验证
- 脚本：`web/tests/e2e/cross-agent-6-3-5.spec.ts`

#### A-2 · Agent1 获客 → look-alike 匹配 → 候选导出
- 入口：`/archive/channel` workspace
- 步骤：填客户画像 → 触发 lookalike 搜索（mock + Tavily 双源）→ 候选企业列表 + 信号时间线 → 点 "导出 xlsx"
- 终点：xlsx 文件下载（含候选企业 + 信号 + 推荐理由）· L1-4 Agent1 + L3-8 Agent1 飞轮验证
- 脚本：`web/tests/e2e/agent1-lookalike-export.spec.ts`

#### A-3 · Agent4 扫描 → 红灯客户台账导出
- 入口：`/archive/alert` workspace
- 步骤：触发批量扫描（mock alert-pool）→ 红黄绿盘 + queue + heat → 点 "导出红灯客户台账"
- 终点：xlsx / pdf 导出（含红灯客户 + 触发原因 + 处置建议）· L1-3 Agent4 + L1-4 Agent4 验证
- 脚本：`web/tests/e2e/agent4-redlight-export.spec.ts`

**约束**：
- 用 `webapp-testing` skill 跑 Playwright（CLAUDE.md 全局规则映射）
- 后端走 mock-session 端点（轨 4 已合 `/api/credit/mock-session`）· 不依赖真 LLM key
- 每条 spec 独立 · 失败不阻塞其他
- spec exit 0 = 100% pass

**完成信号**：`Signal: E2E-3-PATHS-DONE`

---

### Task B · 关键截屏 ≥ 3 张 / 路径

**目标**：每条 E2E 路径取 3 张关键截屏（起点 / 过程 / 终点）· 共 9 张。

**路径**：
- `docs/screens/poc-evidence/cross-agent-6-3-5/{start,middle,end}.png`
- `docs/screens/poc-evidence/agent1-lookalike-export/{start,middle,end}.png`
- `docs/screens/poc-evidence/agent4-redlight-export/{start,middle,end}.png`

**截屏要求**：
- 分辨率 ≥ 1440×900
- 全屏（含 Masthead + Desk + Float-badge）
- 起点 = 入口 view 加载完成
- 过程 = 关键交互后中间态（联动按钮触发后 / 候选返回后 / 扫描进度中）
- 终点 = 最终结果可见 + 导出按钮可见

**生成方式**：
- 跑 Task A 的 Playwright 脚本时挂 `page.screenshot()` 钩子自动生成
- 或独立 `web/tests/e2e/screenshots.spec.ts` 专门跑截屏

**完成信号**：`Signal: SCREENSHOT-3-PATHS-DONE`

---

### Task C · P95 load test

**目标**：100 次采样健康检查端点 + 首字节延时 · 报告 P95 ≤ 1.5s。

**步骤**：
1. 新脚本 `scripts/load_test.py` · 采样：
   - 健康端点：`GET /api/{agent}/health` × 6 agent · 各 100 次
   - 首字节（SSE）：`POST /api/report/fill` 拿首 chunk 时延 · 100 次
   - 端到端（关键路径）：上传材料 → ReportJSON 返回 · 50 次
2. 报告：`docs/perf/p95-2026-04-XX.md`（XX = 实跑日期）
3. 对照：P95 ≤ 1.5s 闸门 · 超阈在 body 单独标
4. 同时跑 P50 / P95 / P99 三档 · 给完整分布画像

**约束**：
- 单线程顺序采样 · 不并发（避免压垮本地 demo 服务器）
- 取样间隔 ≥ 100ms
- 首字节延时 = 从 POST 发出到第一个 SSE chunk 的耗时
- Tavily 等外部 key 缺失时端点降级到 mock · 不算超阈

**完成信号**：`Signal: P95-LOAD-TEST-DONE`

---

### Task D · 运维文档 起/停/监/回

**目标**：4 份 ops md · 客户演示 / 银行 POC 部署的运维基础。

**路径与内容**：

#### D-1 · `docs/ops/start.md`
- demo-start.bat 脚本说明 · 单机 / 多机部署
- 端口约定 · `.env` 必填项清单
- 启动后健康检查命令（curl 6 个 /api/{agent}/health）
- 5 分钟可定位的快速 troubleshooting

#### D-2 · `docs/ops/stop.md`
- demo-stop.bat 脚本说明
- 优雅停机 vs 强制 kill
- 资源回收检查（端口占用 / log 文件 rotate）

#### D-3 · `docs/ops/monitor.md`
- 关键指标：6 agent 健康 / 评估 baseline runner 状态 / SSE 长连数 / Tavily 配额
- 日志位置 + 关键 grep 命令
- 异常 pattern 识别（template_leakage 上升 / hallucination 异动 / EvidenceFirstPipeline 报错）
- 告警阈值建议（不实装监控系统 · 提供阈值供客户对接）

#### D-4 · `docs/ops/rollback.md`
- 回滚到上一稳定 commit 步骤
- 数据库回滚（如有）
- 已知风险点（Phase 3-F 后红区 financial_analyzer/quality_scorer/truth_fill 任何变动需 RFC）
- 紧急联系人（占位 · 客户对接时填）

**约束**：
- 命令均为 Windows + Linux 双平台标注（`bash` vs `cmd`）
- 路径用环境变量化（`$PROJECT_ROOT` / `%PROJECT_ROOT%`）
- 不暴露任何真实生产环境配置（账号 / 密码 / 内网 URL）

**完成信号**：`Signal: OPS-DOCS-DONE`

---

### Task E · READY commit + body 自检

**Final commit body 必含**：
1. 3 条 E2E 路径 spec 文件路径 + pytest/playwright 跑通日志摘要（pass count）
2. 9 张截屏文件路径
3. P95 load test 报告 path + 6 agent 健康 + 首字节 + 端到端 三档 P95 数值 + 是否 ≤ 1.5s 闸门通过
4. 4 份 ops md 路径 + 行数
5. 解 DoD 自检：L3-9 ✓ / L3-10 ✓ / L0-12 ✓ / L0-13 ✓ / L3-5 ✓
6. 红区 0 漂移声明：`agent_*/` + 红区 3 文件 0 改动

**完成信号**：`Signal: READY-FOR-POC-EVIDENCE-REVIEW`

---

## 3. 验收硬指标（T6-1 ~ T6-12 · 12 项）

| # | 指标 | 阈值 | 判定 |
|---|---|---|---|
| T6-1 | E2E 3 spec 全绿 | `web/tests/e2e/{cross-agent-6-3-5,agent1-lookalike-export,agent4-redlight-export}.spec.ts` 全过 | playwright exit 0 |
| T6-2 | 9 张截屏齐 | 3 路径 × 3 节点 = 9 张 PNG · 各 ≥ 1440×900 全屏 | ls + 视觉 |
| T6-3 | P95 load test 报告齐 | `docs/perf/p95-2026-04-XX.md` 含 6 agent + 首字节 + 端到端 三档 P95 | grep |
| T6-4 | P95 ≤ 1.5s 闸门 | 健康端点 P95 + 首字节 P95 均 ≤ 1.5s · 端到端 P95 ≤ 30s（生成型 acceptable） | 报告读 |
| T6-5 | 4 份 ops md 齐 | `docs/ops/{start,stop,monitor,rollback}.md` 全在 | ls |
| T6-6 | ops md 双平台命令 | grep `bash` + `cmd` 在 4 份 md 中各出现 ≥ 1 次 | grep |
| T6-7 | Signal trailer 4 段齐 | E2E + SCREENSHOT + P95 + OPS-DOCS + READY 共 5 段 | git log grep |
| T6-8 | 红区 0 漂移 | git diff name-only 不含 `agent_*/` 业务代码 / `web/src/` 业务代码 / 红区 3 文件 | git diff |
| T6-9 | diff 白名单 | 改动限于 `web/tests/e2e/` / `scripts/` / `docs/perf/` / `docs/ops/` / `docs/screens/poc-evidence/` | git diff |
| T6-10 | 解 DoD 5 项自检 | final body 5 条 ✓ | body grep |
| T6-11 | 不依赖真 LLM key | E2E + load test 全走 mock 路径 · Tavily / DeepSeek 缺失 key 不阻测试 | spec 验证 |
| T6-12 | A-024 路径规范 | `evaluation/runner/base_evaluator.py` / `cli.py` 0 改动（虽然不直接相关 · 守纪律） | stat 0 |

---

## 4. 红线

- ❌ **不动业务代码**（`agent_*/` / `shared/` / `web/src/`）· 本轨纯证据链 · 业务 bug 走 Q-NNN askout
- ❌ **不动红区**（`financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` / `web/src/lib/store/*`）
- ❌ **不动 v16_*.py / evaluation/runner/ 业务**
- ❌ **不依赖真 LLM key**（Tavily / DeepSeek 缺失时 spec 仍跑 · 走 mock）
- ❌ **不并发压测**（单线程顺序采样 · 避免本地 demo 失真）
- ❌ **不 git push**
- ✅ 用 `webapp-testing` skill 跑 Playwright
- ✅ 截屏分辨率 ≥ 1440×900 全屏
- ✅ 4 份 ops md 双平台命令（bash + cmd）
- ✅ Final body 含 5 条解 DoD 自检 + 红区 0 漂移声明 + P95 三档具体数值
- ✅ E2E spec / load test / ops md 三类失败 → Q-NNN askout · 不硬解

---

## 5. 工期

- Task A · Playwright × 3 spec 写 + 调通 · 1.5 天
- Task B · 截屏（自动生成或独立 spec） · 0.25 天
- Task C · load test 脚本 + 跑 + 报告 · 0.5 天
- Task D · 4 份 ops md · 0.5 天
- Task E · final body + 自检 · 0.25 天
- 合计 **2-3 天实做**（不计等轨 4 完成的 wait time）
