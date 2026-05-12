# Liuye BFF Module · 工作纪律 (Tier 3 scoped CLAUDE.md)

> **scope**: 本文件仅约束 `credit_report_agent_work/liuye_service/` 后端 BFF 模块 · v3 spec lockdown 后 Liuye Phase 1 新前端的后端 facade.
> **上游 SSOT**: `docs/contracts/liuye-architecture.md` (Tier 1) + `D:\claude code\_temp\liuye-final-spec-v3.md` (Tier 1 完整实施) + root `CLAUDE.md` (Tier 2 全局).
> **冲突裁决**: 与 Tier 1-2 冲突时 Tier 1-2 赢; 本 scoped 仅"窄化补充", 不允许"反向放宽".
> **版本**: v1.0 (W0 准备周 · sub-agent A 写 · 2026-05-11)

---

## 1. 模块身份

- **path**: `credit_report_agent_work/liuye_service/` (老仓内新模块 · 与 6 agent `agent_*/` 平级)
- **形态**: FastAPI router (mount 到 `api_server.py` 3-6 行) + 编排层 + adapter 层 + worker
- **目的**: 给新前端 `credit_matrix_next/` 提供唯一后端入口 · 把 5 协议 (LiuyeChatEvent / Artifact / ToolCall / KBDoc / EvidenceRef) 翻译成老 6 agent 的 SSE v1.0 / REST 调用
- **关系**: in-process 调老仓 `shared/*` 共享层 · HTTP 调老仓 `agent_*/api.py` 6 agent (见 v3 §1 + §5)

## 2. 边界硬线 (与老仓 6 agent 共存)

### 2.1 in-process 调老仓共享层 (允许)

**允许 import** (per v3 §1 + §5):
- `from shared.llm_caller import LLMCaller, ...` (LLM 唯一化层 · 见 root §3.6)
- `from shared.decision_ledger import record_decision, query_jurisdiction, ...` (BE7 决策账本 · 见 root §3.7.5)
- `from audit_service.decorators import audit_llm_call` (FastAPI 路由级 audit)
- `from shared.kb_scan import ...` (知识库扫描共享底座)
- `from shared.sources import ...` (分层数据源 BaseSource / Router / Degrader)
- `from auth_service.dependencies import require_user` (RBAC dependency · 见 root §3.7.5 BE7 admin endpoints)
- `from shared.sse_envelope import make_stage, make_section, make_done, ...` (SSE 共形 helper)
- `from shared.evidence_freshness import FRESHNESS_SLA_DAYS, ...` (第 6 原则 · root §3.5.1)
- `from shared.data_tiers import DataTier` (第 6 原则 · 4 Tier)
- `from shared.recommendation_schema import RecommendationReason` (第 6 原则)

### 2.2 HTTP 调老仓 6 agent (允许)

**允许 HTTP** (per v3 §5 + 附录 A.2 #1):
- `httpx.AsyncClient().post('http://localhost:8000/api/channel/run', ...)`
- `httpx.AsyncClient().post('http://localhost:8000/api/credit/...', ...)`
- `httpx.AsyncClient().post('http://localhost:8000/api/report/v16/...', ...)`

每个 agent 一个 `adapters/{agent}.py` · `liuye_service` 不直接拼 SSE / REST 调用 · 通过 adapter 抽象.

### 2.3 禁止 import agent_* 内部函数 (硬线)

**绝对禁止** (per v3 附录 A.2 #1):
- `from agent_channel.signal_search import ...`
- `from agent_credit.scoring_model_corporate import ...`
- `from agent_report.api import _build_llm_caller, ...`
- `from agent_riskctrl.backtesting import MAX_ROWS, ...`
- 任何 `agent_*/*.py` 内部模块的直接 import (api.py / 内部 helper / private 函数)

**例外**: **无**. 6 agent 内部边界与 `liuye_service` 是 HTTP 隔离 · 任何 in-process import 都破坏 §3.1.1 Cowork/Managed 二分.

## 3. SSE v1.0 → liuye 11 event adapter (唯一 wire 兼容层 · PM 2026-05-11 ratify 加 permission.request 11th)

**位置**: `liuye_service/adapters/sse_v1_to_liuye.py` (v3 §2.1.5 + 附录 A 锁).

**规则** (v3 §2.1.5 + 附录 A.2):
1. **adapter 是唯一兼容层**: 新前端禁直接 connect 老 `/api/agents/*/stream` · 必须走 `liuye_service` BFF
2. **老 v1.0 不废**: `docs/contracts/sse-envelope.md` v1.0 兼容保留 · 6 agent backend 不动
3. **seq 重新生成**: 老 v1.0 无 seq · BFF adapter 注入单调递增 (基于 redis `INCR liuye:seq:{turn_id}` 或 in-memory counter · Phase 1 in-memory 即可)
4. **idempotency**: 老 event 二次推送 · BFF 用 `dedup_key = (event, data_hash)` 去重
5. **降级**: BFF 转换失败 → 转 `turn.error code=SSE_ADAPTER_FAILED fallback_available=true` + 触发 full snapshot

**11 event 映射** (v3 附录 A.1 verbatim · permission.request 11th 由 `permissions.py::emit_permission_request` 直接 emit · 不经 adapter 转换):

| 老 v1.0 | liuye | adapter handler |
|---|---|---|
| `profile_loaded` | `turn.started` | `on_profile_loaded` |
| `stage` | `tool.progress` | `on_stage` |
| `stream` (token-by-token) | `message.created` (首帧) + delta | `on_stream` |
| `tool_call` | `tool.started` | `on_tool_call` |
| `tool_result` | `tool.completed` | `on_tool_result` |
| `done` | `turn.completed` | `on_done` |
| `error` | `turn.error` (9 字段) | `on_error` |
| (新) | `artifact.patch` | `emit_artifact_patch` (BFF 监听 mutate) |
| (新) | `evidence.attached` | `emit_evidence_attached` |
| (新) | `heartbeat` 15s | `heartbeat_loop` |

**禁**:
- 新前端绕过 adapter 直接 fetch 老 SSE
- adapter 内 import `agent_*` 内部模块 (走 HTTP)
- adapter 修改 6 agent backend 的 SSE 格式 (老 v1.0 是 SSOT · 改了破坏 Phase A worker-A2 + 6 老 agent consumer)

## 4. Cowork vs Managed 二分硬线 (root §3.1.1)

**Phase 1 scope** (v3 §1):
- **Cowork agent**: `channel` / `credit` / `report` → SSE 流式 + `liuye_service/adapters/{channel,credit,report}.py`
- **Managed agent**: `riskctrl` / `alert` / `compliance` → Phase 2 才做 · Phase 1 占位 adapter (`adapters/riskctrl.py` / `alert.py` / `compliance.py` 留 stub + `NotImplementedError("Phase 2")`)

**硬线** (root §3.1.1 + v3 必修 #73):
- **Cowork agent 不可跑超 5s SLA 的任务** — 超时即拆 Managed pipeline (job_id + 后台跑 + 通知前端) · 不在 SSE 内强等
- **Managed agent 不可强 SSE 假装实时** — 用 job_id + 前端 poll 或 webhook · SSE 仅 status update 不传业务结果
- **跨 mode 调用走 `shared/job_runtime/` 或 SkillInvocation** (Phase D 起 · 当前 Phase C 不强制 · 但新代码不允许直 in-process call 跨 mode agent)

**反模式**:
- ❌ Phase 1 `liuye_service` 内嵌 Managed long-task 用 `asyncio.create_task` 假后台 (进程重启即丢)
- ❌ `adapters/riskctrl.py` Phase 1 真接 backtest 走 SSE (50000 行 KS · 5s SLA 必爆 · 见 root §3.7.1)

## 5. decision_ledger in-process 调用 (BE7 · root §3.7.5)

**规则** (v3 §6.1 #2 + 必修 #31 + root §3.7.5):
- 任何跨 Agent 决策 (A3-NEW Credit submit / LE-05 review) → in-process 调 `shared.decision_ledger.record_decision(...)`
- **不允许** 走 HTTP 调 `ledger_service/api.py` 5 admin endpoints (那是给 admin UI 用 · `liuye_service` BFF 用 in-process 更快 + 失败隔离一致)
- **subject_id 必须 hash** (16-hex prefix · `hash_subject_id()` · plain PII 禁入)
- **retention default 见 root §3.7.5** (credit standard 5y / report long 10y / alert short 90d / compliance standard 5y)
- **jurisdiction default = HQ** (env `LIUYE_LEDGER_JURISDICTION` 可覆盖)
- **失败隔离**: ledger 写入失败 silent-fail · decision flow 不破 (per Agent3 BE2 wrapper 模式)

**LedgerReviewEvent append-only** (v3 §2.5 + §5 LE-05):
- `liuye_service/ledger_review.py` 处理 `POST /api/liuye/ledger/decisions/{id}/review_events`
- **只 append event · 不 mutate 原 decision** (v3 必修 #30 + #69)
- event 含 `event_id` / `decision_id` / `reviewer_id` / `action` / `comment` / `idempotency_key` / `signature?` / `appended_at`

## 6. LLM PIPL fallback chain (root §3.6 + §3.7.3)

**规则**:
- 所有 LLM 调用走 `shared.llm_caller.LLMCaller(agent_id="liuye", endpoint="/api/liuye/...")` · **禁** 裸 `OpenAI(...)` / 裸 `httpx` 调 LLM
- **PIPL 合规 fallback chain**: `DEFAULT_FALLBACK_CHAIN = ("deepseek", "dashscope")` 全境内 (root §3.6 + Stage E.3)
- `moonshot` (海外路由) **仅** `LLM_PROVIDER=moonshot` 显式触发 · audit log 必含 `region` 字段
- 调用必带 `with_audit(...)` ctx (silent-fail) · 与 `audit_service.decorators.audit_llm_call` 三层互补

**禁**:
- 任何 `import openai` / `from openai import OpenAI` 在 `liuye_service/` 内
- 任何硬编 LLM endpoint URL 在 adapter 内 (从 `shared.llm_caller` 拿)
- 任何"为了快"绕过 audit (silent-fail 不等于 silent-skip)

## 7. outbox_retry.py 60s 重试 ledger silent-fail (v3 §5.x · P1-12)

**位置**: `liuye_service/workers/outbox_retry.py` (W1 backend worker 必交付).

**规则** (v3 §5.x verbatim):
- 每 **60s** 扫 `data/liuye/outbox/`
- ledger write 最多 retry **5 次**
- exponential backoff: **60s / 120s / 240s / 480s / 960s**
- 超 5 次 → 写 `data/liuye/dead-letter/` + Sentry alert
- 部署: systemd `liuye-outbox.service` 或 supervisord (W0 sub-agent D 出 systemd unit)
- idempotency_key 防重复写
- **silent-fail 模式**: ledger 写入失败 · decision flow 不破 · event 进 outbox 重试 (audit chain 保完整)

**禁**:
- 用 `asyncio.create_task` 在主进程内做 outbox 重试 (进程重启即丢)
- 把 outbox 写 sqlite (`data/ledger/decisions.sqlite` 是 ledger 主库 · outbox 是 JSON lines 文件 · 隔离)
- 重试次数 / backoff 自己改 (v3 P1-12 锁定)

## 8. PermissionRequest 3 风险分级 (v3 §2.5 + #21)

**规则** (v3 §2.5):

| 风险 | UI 形态 | Liuye 实例 |
|---|---|---|
| **low** | inline notice (E) | F-001 logout / pin / 发送 IM / **LE-04a 下载已生成 manifest** |
| **medium** | blocking modal (B) | F-053 上链 / PASS handoff / **F-052-export 导出 docx** / **A3-NEW Decision submit** |
| **high** | drawer with reason (D) | LE-05 签字 / PARTIAL handoff / 越权 persona 操作 / **LE-04b drawer + Managed job ZIP** |

**`liuye_service/permissions.py` 必须**:
- 返回 `PermissionRequest` 含 `risk` / `rule_source` / `scope` / `explanation` / `consequences[]` / `idempotency_key?`
- 不可逆动作 (high risk) 必带 `idempotency_key` (v3 必修 #21)
- `required_persona[]` / `disabled_reason` / `required_permission` 来自后端 ArtifactAction registry (v3 必修 #22) · 前端不硬编

## 9. 不准发明新 prompt SSOT (root §3.7.7 灰度)

**规则** (root §3.7.7 verbatim):
- 6 Agent system prompt 从 inline `SYSTEM_*` 常量切到 `shared/prompts/contract.py:build_system_prompt(agent_id, ...)` 必须**渐进式落地** (flag + canary + evaluation gate)
- **一次性切 6 Agent 不被允许** · 回归不可控 · 没有 fallback 路径

**对 `liuye_service` 的具体约束**:
- `liuye_service` 自己 **不持有** system prompt SSOT · prompt 仍归 `shared/prompts/contract.py` (Phase A worker-A2 立) + 各 agent `agent_*/prompts.py`
- adapter 调 agent 时透传业务参数 · **不**自己拼 system prompt
- 若 `liuye_service` 需要"BFF 级"辅助 prompt (e.g. 把 5 候选 ranking 描述翻译给 LLM rerank · 见 v3 §6.3 step 3) · 走 `shared/llm_caller` + 在 `liuye_service/orchestrator.py` 内 inline string · **禁建新 SSOT 目录**

**反模式** (root §3.7.7):
- ❌ `liuye_service/prompts/` 新目录 (绕开 `shared/prompts/contract.py`)
- ❌ 一次 PR 6 agent SYSTEM_* 全替 (走 Phase 1 / 2 / 3 flag canary · root §3.7.7)
- ❌ 不开 flag 直替 SYSTEM_* (REJECT-V2)

## 10. 部署走 `bash scripts/deploy_to_ecs.sh` (root §13)

**规则** (root §13 + §13.1):
- 改 `liuye_service/*.py` / `api_server.py` (mount router) → `bash scripts/deploy_to_ecs.sh --skip-build` (仅 backend restart · 不需 npm build)
- 改 `data/liuye/fixtures/*.json` / `data/liuye/outbox/` 配置 → 同上 (后端 restart 即可)
- 部署涉及 systemd `liuye-outbox.service` / `liuye-bff.service` 配置 → 必须问 user (root §13.1 例外)

**禁** (root §13):
- scp 直接编辑 ECS `liuye_service/*.py` (回档源)
- 改完不验 (改完跑 `cd credit_report_agent_work && py -m pytest liuye_service/tests/ -v`)
- 跳 `scripts/deploy_to_ecs.sh` 直接 `git push` + `systemctl restart` (脚本封装 stash + pull + healthcheck · 跳了易出错)

## 11. W1 file 交付清单 (v3 §8 backend worker 18 文件)

```
liuye_service/__init__.py
liuye_service/api.py                    # FastAPI router · mount 3-6 行
liuye_service/schemas.py                # Pydantic 5 协议 SSOT + LedgerReviewEvent + Permission + Validation
liuye_service/orchestrator.py           # Cowork SSE 编排 + range messages endpoint
liuye_service/audit.py                  # in-process 包 audit_service + decision_ledger
liuye_service/permissions.py            # PermissionRequest 流 + 3 风险分级
liuye_service/trace.py                  # liuye_session_id / trace_id 关联
liuye_service/config.py                 # env LIUYE_ENABLED / LIUYE_DEMO_MODE / LIUYE_LEDGER_JURISDICTION
liuye_service/adapters/base.py          # adapter 协议接口
liuye_service/adapters/channel.py       # HTTP 调 agent_channel (Cowork SSE)
liuye_service/adapters/credit.py        # Cowork SSE (R4 修, 非 Managed)
liuye_service/adapters/report.py        # Cowork SSE
liuye_service/adapters/sse_v1_to_liuye.py  # P0-2 唯一 wire 兼容层
liuye_service/workers/outbox_retry.py   # 60s · 5 retry · backoff 60-960s
liuye_service/ledger_review.py          # append-only LedgerReviewEvent
liuye_service/tests/test_contracts.py   # 5 协议 schema validate
liuye_service/tests/test_sse_adapter.py # 11 event mapping (含 permission.request 不经 adapter)
liuye_service/tests/test_outbox.py      # outbox worker retry + dead-letter
```

详细交付 DoD 见 `docs/onboarding/W1-backend-worker.md`.

## 12. Commit trailer 模板 (接老仓 §13.5)

改 `liuye_service/*.py` 必带 trailer:
```
PRESERVES: BE7-ledger, A4-llm-caller    ← 列保留的老仓 inventory 能力
NEW-ENDPOINT: POST /api/liuye/...       ← 新增 BFF endpoint
TESTS-PASS: liuye_service/tests/...     ← 跑通的 pytest 文件
```

缺 trailer = review 阻断 + merge 阻断 (与老仓 §13.5 同等严肃).

## 13. 引用 SSOT

| Tier | 文件 | 适用 |
|---|---|---|
| Meta | `docs/arch/instruction-source-of-truth.md` | 老仓 SSOT 排序规则 |
| 1 | `docs/contracts/liuye-architecture.md` | Liuye 10KB 摘要 |
| 1 | `D:\claude code\_temp\liuye-final-spec-v3.md` | v3 spec 51KB 完整实施 |
| 1 | `docs/contracts/sse-envelope.md` v1.0 | 老 SSE 协议 (adapter 兼容源) |
| 1 | `docs/contracts/llm-prompt-contract.md` v1.0 | LLM prompt 8 段 SSOT (`shared/prompts/contract.py`) |
| 1 | `docs/contracts/decision-ledger.md` v1.0 | BE7 决策账本 |
| 2 | root `CLAUDE.md` | 老仓全局工程行为 |
| 3 | **本文件** | `liuye_service/` BFF scoped |
| 4 | `docs/onboarding/W1-backend-worker.md` | W1 backend worker brief |

冲突时数字小者赢. 本 scoped 不允许反向放宽 Tier 1-2 的硬线.
