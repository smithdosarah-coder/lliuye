# Agent6 报告 · Phase 1 Finalize Onboarding（95% → 100%）

**对应 worktree**：`D:\claude code\demo-agent6`（`feat/agent6-v16`）
**发布日期**：2026-04-19
**前置**：已读 `AGENT_IDENTITY.md` + `CLAUDE.md` + 本文
**目标**：把 DoD L2/L3 挂着的 6 个尾巴一次收了，Agent6 从 95% → 100%（可卖）。

---

## 这是两条线里的哪一条

Agent6 当前挂两条线：

1. **质量线**（MAINTENANCE 等触发）：Rule 17 `unfilled_marker_accuracy` 0.625 gap / `PHASE-2-GO-CORPORATE` 对公真材料回归 —— 等外部触发，**本 onboarding 不动这条**
2. **产品化线**（本批次）：DoD L2/L3 尾巴（审计日志 + 合作机构 + 数据分级 + 模型卡 + 演示脚本 + 反馈飞轮 E2E）—— **本 onboarding 就是干这条**

两条线红区不冲突：质量线改 `v16_*` + prompts + `quality_scorer.py`，产品化线改 `session_store` + `api_server.py` 钩子 + `docs/model_cards/` + `docs/demo_script/` + `data/audit/` + `data/feedback/`。

---

## Task A · 审计日志接通（0.5 天，对应 DoD L2-12）

### 目标
所有 Agent6 调用落地 `data/audit/YYYY-MM-DD.jsonl`，每条带：timestamp / user_id（mock 王哲）/ endpoint / input_hash / output_status / latency_ms。

### 实现
- 在 `session_store` 加钩子（不改现有接口，只加 `audit_log(event)` 写文件）
- `api_server.py` 在 `/api/report/*` 路径处理完成后调用 `audit_log`
- `data/audit/.gitkeep` 保留目录，`data/audit/*.jsonl` 进 `.gitignore`

### DoD
- [ ] 跑 Agent6 一次报告生成 → `data/audit/2026-04-19.jsonl` 有 1+ 行
- [ ] JSONL schema: `{timestamp, user_id, endpoint, input_hash, output_status, latency_ms}`
- [ ] 不破坏现有 session_store API（调用方不需要改）

### 冒烟
```bash
py /tmp/start_uvicorn.py &
# 等 2s 后手动触发一次报告生成（或用 `evaluation/runner/adapters/agent6_report.py` 冒烟）
ls data/audit/*.jsonl
head -n 1 data/audit/2026-04-*.jsonl | py -c "import sys,json; print(json.dumps(json.loads(sys.stdin.read()), ensure_ascii=False, indent=2))"
```

---

## Task B · 合作机构 + 数据分级文档（0.5 天，对应 DoD L2-13 / L2-14）

### 目标
把银行交付必备的两份 RFC 级文档落盘。

### 交付物
- `docs/compliance/partners.md` —— 合作机构清单：Tavily / DeepSeek / akshare / gov.cn / pbc.gov.cn / flk.npc.gov.cn；每个列出：数据类型、合规依据、是否涉境外、降级策略
- `docs/compliance/data-grading.md` —— 数据分级：企业工商（公开）/ 财务报表（客户授权）/ 个人信息（最小化）/ 审贷员修改（feedback 内部）；每级列出：保留期 / 访问权限 / 销毁机制

### DoD
- [ ] 两份文档落盘，每份 ≥ 80 行
- [ ] 明确标注哪些字段走 `shared/sources/` 分层架构、哪些走内部 KB
- [ ] 与 CLAUDE.md 第 12 节开发约束一致

---

## Task C · 模型卡片 + 演示脚本（0.5 天，对应 DoD L3-11 / L3-12）

### 目标
给业务方 / 监管写两份"能拿出去给人看"的文档。

### 交付物
- `docs/model_cards/agent6.md` —— 模板：Agent 定位 / 输入输出 / 训练/推理数据 / 核心指标（v7.23 基线 93.5% 自动化率、QC 90.0）/ 已知局限（unfilled_marker 0.625 gap）/ 合规声明
- `docs/demo_script/agent6.md` —— 10-15 min 演示流程：加载企业材料 → 触发报告 → 看 Evidence 链 → QC Blocker 拦截示范 → feedback 录入

### DoD
- [ ] 模型卡片遵循 Google Model Cards for Model Reporting 结构（9 sections）
- [ ] 演示脚本含 3 个关键截图点位（用 placeholder `[screenshot: xxx]`，先不实截）
- [ ] 演示脚本的每一步命令都在当前 `feat/agent6-v16` tip 能跑

---

## Task D · 反馈飞轮 E2E 验证（0.5 天，对应 DoD L3-8）

### 目标
证明 `/api/feedback` 真能落盘到 `data/feedback/YYYY-MM-DD.jsonl`（当前 `data/feedback/` 是空的，L3-8 挂着）。

### 实现
- 如果 `/api/feedback` endpoint 不存在 → 在 `api_server.py` 补上
- Schema：`{timestamp, user_id, report_id, field_path, original, corrected, reason}`
- E2E 测试：`agent_report/tests/test_feedback_e2e.py`

### DoD
- [ ] `py -m pytest agent_report/tests/test_feedback_e2e.py -v` → passed
- [ ] 手动 `curl -X POST http://localhost:8000/api/feedback -d '...'` → `data/feedback/2026-04-19.jsonl` 有新行
- [ ] JSONL 格式与 CLAUDE.md §6 四环数据飞轮 step 3 对齐

---

## 红区边界

- ❌ `shared/` / `docs/contracts/` —— A-004 §〇
- ❌ 其他 agent_* 目录
- ❌ `web/` 前端（前端 Stage 2 另一条线在做）
- ❌ `evaluation/runner/` framework 核心
- ❌ `v16_op_handlers.py` / `v16_generator.py` / `v16_pipeline.py` / `section_generator.py` / `truth_fill.py` / `quality_scorer.py` —— 质量线红区，本批次不动
- ❌ **本批次不做 Rule 17 / PHASE-2-GO-CORPORATE** —— 等外部触发

允许：
- ✅ `session_store` 加 `audit_log()` 钩子（不改现有接口）
- ✅ `api_server.py` `/api/report/*` + `/api/feedback` 路径
- ✅ `data/audit/` + `data/feedback/` 目录初始化
- ✅ `docs/compliance/*.md` + `docs/model_cards/agent6.md` + `docs/demo_script/agent6.md`
- ✅ `agent_report/tests/test_feedback_e2e.py`
- ✅ `.gitignore` 扩展（`data/audit/*.jsonl` / `data/feedback/*.jsonl`）

---

## Commit / Signal

R-A/B/C 硬规则同其他 agent。

### Milestone

| 时点 | Signal |
|---|---|
| 读完 onboarding | `AGENT6-PHASE-1-FINALIZE-ACK` |
| Task A 审计日志接通 | `AGENT6-AUDIT-WIRED` |
| Task B 合规文档落盘 | `AGENT6-COMPLIANCE-DOCS-READY` |
| Task C 模型卡+演示脚本落盘 | `AGENT6-MODEL-CARD-READY` |
| Task D 反馈飞轮 E2E 通过 | `AGENT6-FEEDBACK-LOOP-VALIDATED` |
| 所有收尾全绿 | `AGENT6-PHASE-1-FINALIZE-READY-FOR-REVIEW` |
| Review 通过收工 | `WINDOW-CLOSED-CLEAN` |

---

## Q/A

疑问 → `docs/handoff/decisions-log.md` `Q-NNN` → trailer `Signal: Q-NNN-RAISED`。

---

## ACK

```bash
git commit --allow-empty -m "ack(agent6): Phase 1 finalize onboarding absorbed" -m "" -m "Signal: AGENT6-PHASE-1-FINALIZE-ACK"
```

Task A → B → C → D 顺序推进，每 Task 收敛 commit 一次。
