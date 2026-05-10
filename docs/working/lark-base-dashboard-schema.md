# ALL IN Mesh Dashboard · lark-base Schema · 2026-05-09

> **Owner**: 主 CLI · 6 worker 各自更新自己行
> **Phase**: A 第 4 件交付物 (per `docs/handoff/phase-r3-worker-runbook.md` §A.2.4)
> **创建脚本**: `scripts/mesh/create_lark_dashboard.sh`
> **依赖**: lark-cli `base` skill (per CLAUDE.md Skill 触发映射)

---

## 1. 表名

`ALLIN_2026-05-08_Mesh_Dashboard`

## 2. 字段 schema (12 字段 · per allin-final-exec-2026-05-08.md §6.2)

| # | 字段 (中文) | 字段名 (英文) | 类型 | 必填 | 说明 |
|---|---|---|---|---|---|
| 1 | Agent | agent | text | ✅ | report / credit / alert / riskctrl / compliance / common |
| 2 | 责任人 | owner | person | ✅ | 该 worker CLI 责任人 (默认刘野) |
| 3 | Worktree 路径 | worktree | text | ✅ | e.g. `D:/claude code/credit_report_agent_work_mesh/report` |
| 4 | 写域 | scope | text | ✅ | e.g. `agent_report/ + web/src/app/archive/report/` |
| 5 | 红线 | redline | text | ✅ | 该 agent 必守的红线 (per KT §3.6 stop-the-line 中和 agent 相关条) |
| 6 | 输入合同 | input_contract | text | ✅ | entity-resolution-contract / candidate-identity-contract / signal-commit-contract |
| 7 | 输出合同 | output_contract | text | ✅ | 报告 / 决策 / 预警 / 政策矩阵 / DSL |
| 8 | 最新 signal | latest_signal | text |  | worker fire 的最新 signal commit hash |
| 9 | 证据 | evidence_url | url |  | 截图 / 测试日志 / 性能数据 URL |
| 10 | 阻塞依赖 | blocked_by | text |  | 撞红线时填具体 contract 缺口 |
| 11 | 状态 | status | select | ✅ | doing / ready / merged / blocked |
| 12 | 最后更新 | updated_at | datetime | ✅ | worker fire signal 时自动更新 |

## 3. 5 agent + common 占位行 (Phase A 创表时填)

### 3.1 common 行

| 字段 | 值 |
|---|---|
| agent | common |
| owner | 刘野 |
| worktree | `D:/claude code/credit_report_agent_work_mesh/common` |
| scope | `shared/ + docs/contracts/ + .mesh-launcher/` |
| redline | 不改 agent_*/ + web/src/app/archive/*/ |
| input_contract | (无 · 自己定 contract) |
| output_contract | 3 contract + 3 共性架构 + 6 resume + dashboard + 5 模板 |
| status | doing (Phase A 进行中) |

### 3.2 5 agent worker 行

| agent | scope | redline (top 1) | output_contract |
|---|---|---|---|
| report | `agent_report/` + `web/src/app/archive/report/` | v16 stub 不冒充真源 | ReportJSON + Word |
| credit | `agent_credit/` + `web/src/app/archive/credit/` | 决策必上链 (decision_ledger) | 四维评分 + 额度建议 |
| alert | `agent_alert/` + `web/src/app/archive/alert/` | Managed 不强 SSE 假实时 | 红/黄/绿分级 alert |
| riskctrl | `agent_riskctrl/` + `web/src/app/archive/riskctrl/` | 评分必带回测 (MAX_ROWS=50000) | DSL + KS / 通过率 |
| compliance | `agent_compliance/` + `web/src/app/archive/compliance/` | 监管条款必带原文 hash | 违规冲突点清单 |

所有 5 agent 行:
- input_contract: `entity-resolution-contract / candidate-identity-contract / signal-commit-contract`
- status: pending (Phase A 完后转 doing)

## 4. 创建命令 (主 CLI 跑 · 一次性)

per `lark-cli base` skill:

```bash
# Step 1: 启 lark-cli base 创建 (主 CLI 跑)
lark-cli base table-create \
  --app-token <PM 提供的 base app_token> \
  --name "ALLIN_2026-05-08_Mesh_Dashboard" \
  --description "6 agent ALL IN mesh 状态看板 · per allin-final-exec-2026-05-08.md §6.2"

# Step 2: 加 12 字段 (按 §2 表)
# (lark-cli 需逐字段 add · 或一次性 schema yaml import · 见脚本)
```

完整自动化脚本: `scripts/mesh/create_lark_dashboard.sh` (本 commit 同包).

## 5. worker fire signal 后更新 (Phase B)

worker fire signal commit 后, 主 CLI 收 signal 时自动更新该 agent 行:

```bash
lark-cli base record-update \
  --app-token <token> \
  --table-id <table_id> \
  --record-id <agent 行 record_id> \
  --fields '{
    "latest_signal": "<commit sha>",
    "status": "ready",
    "evidence_url": "<screenshot_url>",
    "updated_at": <timestamp>
  }'
```

(主 CLI cherry-pick 完成后再改 status: ready → merged.)

## 6. 红线

- **schema 不许 break**: Phase A 冻结后 12 字段名 / 类型不许改 (worker 依赖) · 改走 RFC
- **status select 4 值锁定**: doing / ready / merged / blocked · 加 enum 值要更 ABI
- **agent select 6 值锁定**: 6 个 agent 名 · 拼写跟 CLAUDE.md §11 一致
- **不允许手动改 latest_signal**: 必须由主 CLI cherry-pick 流程自动写 (防 worker 自造 signal)

## 7. 待 PM 提供 (主 CLI 创表前)

- [ ] lark base app_token (PM 在飞书 base app 里建一个空 base · 把 app_token 给主 CLI)
- [ ] 责任人 person 字段值 (刘野的飞书 open_id · 默认走 lark-contact +me 自查)

PM 提供后主 CLI 跑 `bash scripts/mesh/create_lark_dashboard.sh` 一次创表 + 6 行占位.

## 8. 后续 Phase

- **Phase A 第 5 件交付物**: 桌面 `launch-all-LIUYE.bat` 7 cmd 一键启 (per KT §7) · 待 PM 拍板路径后落
- **Phase B**: 5 agent worker resume + fire signal · 各自更新自己行
- **Phase C**: 主 CLI cherry-pick 流程自动改 status: ready → merged
