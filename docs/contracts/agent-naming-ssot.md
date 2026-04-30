# Agent Naming Single Source of Truth (SSOT) v1.0

**Status**: 🟢 RATIFIED (with PM-pending decision in §3 · 不阻 ratification)
**Owner**: 主 CLI · 修改走 RFC (`shared-change-protocol.md`) · worker 不直接改本表
**生效**: Phase A · CI lint hardline #8 落地后强制
**Author**: Phase A worker-A1 · 2026-04-29

---

## 0. 为什么有这份 SSOT

走歪诊断 (`docs/reset/north-star.md` §2.3 + `docs/audit/conflict-register-v1.md` Cat 8/9/10/16): 6 Agent 在以下 8 个维度全栈分裂:

- `compliance` (frontend AgentKey) vs `compli` (backend RBAC AgentId) · 双 id 全栈分裂 · 补丁文件 `web/src/lib/auth/agent-id.ts` 临时映射
- `agents.ts:45-115` `path: "/channel"` 字段指向**不存在**的顶层路由 · 应是 `/archive/<id>` (canon)
- `agents.ts` accent 6 处用 legacy `--color-{ink,brass,sage,amber,ember,brass-dim}` · 违 §7 红线 (Letterpress 已下架)
- CLAUDE.md §1 4 角色 vs §4 第 2 行 "策略经理" 文案漂 (audit Cat 16) · runtime 蔓延到 `api_server.py:376` IM prompt
- `evaluation/agent5_compliance.yaml:3` agent: compliance · `auth_service/rbac.py:42` VALID_AGENTS 用 compli · eval baseline 与 RBAC 命名分裂

无 SSOT · 任何 worker 改 agent 相关代码必踩坑。本 doc = 6 Agent × 8 维度的**唯一权威表**。

---

## 1. 8 列 SSOT 表 (核心 · 单源)

> ✅ 6 行全锁 (compliance ratified · per Q-042.B 2026-04-29 PM 拍板 · 详 §3)。

| agent_id | 中文 | 业务名 | UI brand | route (canon) | 色彩 token | RBAC role | eval baseline |
|---|---|---|---|---|---|---|---|
| `channel` | 全渠道获客 | look-alike 获客 (基于已成交客户外网搜相似企业) | 全渠道获客 | `/archive/channel` | `--t-channel` (#3C7B7B 青绿) | `rm` / `admin` | `evaluation/agent1_channel.yaml` |
| `report` | 信贷报告助手 | Agent6 报告 (Evidence-First 三阶段 + QC blocker) | 信贷报告助手 | `/archive/report` | `--t-report` (#B08640 棕赭) | `rm` / `credit_officer` / `compliance_officer` / `risk_manager` / `admin` | `evaluation/agent6_report.yaml` |
| `credit` | 授信决策辅助 | Agent3 授信 (Agent6 下游 · 对公+对私+普惠 三板块四维评分) | 授信决策辅助 | `/archive/credit` | `--t-credit` (#3E6292 青蓝) | `rm` / `credit_officer` / `risk_manager` / `admin` | `evaluation/agent3_credit.yaml` |
| `alert` | 贷中风险预警 | Agent4 预警 (客户行为变化驱动 · 红/黄/绿榜单) | 贷中风险预警 | `/archive/alert` | `--t-alert` (#C85A3C 赭红) | `rm` / `credit_officer` / `compliance_officer` / `risk_manager` / `admin` | `evaluation/agent4_alert.yaml` |
| `compliance` | 合规巡检 | Agent5 合规 (政策事件驱动 · 业务矩阵冲突点) | 合规巡检 | `/archive/compliance` | `--t-compli` (#5B7A48 墨绿) | `compliance_officer` / `admin` | `evaluation/agent5_compliance.yaml` |
| `riskctrl` | 风控策略运营 | Agent2 风控 (DSL 生成 + 回测) | 风控策略运营 | `/archive/riskctrl` | `--t-riskctrl` (#6B4A6D 绛紫) | `risk_manager` / `admin` | `evaluation/agent2_riskctrl.yaml` |

**触发 / 输入 / 产出 / 不做** 见 `CLAUDE.md` §4 (功能边界) · 本 SSOT 不重复 · 仅锁命名维度。

---

## 2. 字段权威性 (consumer ↔ writer)

| 列 | 类型 | 权威 file | consumer file (read-only · 必引用本 SSOT) |
|---|---|---|---|
| `agent_id` | string · kebab-case · ≤ 16 char | 本 SSOT | `web/src/lib/agents.ts` AgentKey + AgentId · `auth_service/rbac.py` VALID_AGENTS · `web/src/lib/store/types.ts` AgentId · `evaluation/agent*_*.yaml` agent 字段 · `agent_*/api.py` mount prefix · `RBAC_GUARD` regex |
| 中文 | string · 4-8 字 · 业务术语锁 (per CLAUDE.md §4) | 本 SSOT | `web/src/lib/agents.ts` AgentDef.label · `web/src/components/shell/Masthead.tsx` nav label |
| 业务名 | string · 句子级描述 | 本 SSOT | docs/contracts/agent-*-spec.md 顶端 + onboarding doc + `docs/prd/master-*.md` |
| UI brand | string · 显示用 | 本 SSOT (= 中文) | 前端组件 title · 不允许新词 |
| route | string · `/archive/<id>` 形 · canon | 本 SSOT | `web/src/app/archive/<id>/_components/<Agent>Workspace.tsx` 子目录 · `web/src/lib/agents.ts` AgentDef.path (旧顶层路径已废 · 见 §4 enforcement) |
| 色彩 token | CSS var · `--t-<id>` | `web/src/app/globals.css` (writer · 主 CLI · per §7 CLAUDE.md) | `web/src/lib/agents.ts` accent · 6 Workspace · Float-badge · Masthead pip |
| RBAC role | role[] · 5 user matrix | `auth_service/rbac.py:VALID_AGENTS` + `auth_service/users.py:46-50` (writer · backend) | `web/src/lib/store/auth-store.ts:36-40` ACCESS · `web/src/app/archive/[agent]/RbacGuard.tsx` · `web/src/components/shell/AuthGate.tsx` |
| eval baseline | path string | 本 SSOT | `evaluation/runner/adapters/agent*_*.py` adapter loader · `docs/contracts/agent-*-spec.md` § "评估基线" |

**红线**: consumer 一律 read-only 引用本 SSOT · 不允许在 consumer 文件**重复定义**或**镜像**字段值。`web/src/lib/auth/agent-id.ts` 现为 identity 映射 (compliance → compliance · per Q-042.B 全栈统一)。

---

## 3. ✅ RESOLVED · agent5 单 id = `compliance` (Q-042.B · 2026-04-29 PM 拍板)

**结论**: agent5 全栈统一 `compliance`。frontend AgentKey + AgentId + backend RBAC + sub-PRD 文件名 + LLM caller `agent_id` + route `/archive/compliance` 全部 verbatim。

**Ratification source**: `docs/handoff/decisions-log.md` Q-042.B (worker-A7 V2 codex 5 issue 第 4 项 fix · effective ratification by 全栈 verbatim 使用)

**真实落地** (Stage 4 cleanup · 主 CLI 2026-04-30 commit):
- `auth_service/rbac.py` ACCESS / HANDOFFS / VALID_AGENTS 9 处 `compli` → `compliance`
- `web/src/lib/store/types.ts` AgentId union + AGENT_IDS 数组
- `web/src/lib/store/auth-store.ts` ACCESS / HANDOFFS 8 处
- `web/src/lib/auth/agent-id.ts` mapping 改为 identity (compliance → compliance · 文件保留以维持 import API 稳定 · consumer code 不动)
- `web/src/lib/api/auth.ts` AuthAgentId union
- `web/src/lib/store/handoff-catalog.ts` recipe id (`alert_to_compli` → `alert_to_compliance` · `compli_to_report` → `compliance_to_report`) + event type (`compli.conflict_found` → `compliance.conflict_found`)
- `web/src/components/shell/AuthGate.tsx` regex agent path
- `web/src/components/shared/ScanCTA.tsx` ScanTone union + remove "compli"→"compliance" cast
- 8 个 frontend consumer 文件 (today/dispatch/customer/audit/components/shell · event type + agent literal 同步)
- `web/src/app/dispatch/_components/{composer-commands.ts, ComposerBar.tsx, MessageBubble.tsx}` AGENT_ALIAS map (legacy `compli` 别名 → `compliance` 输出 · 用户输入 `compli` 仍兼容)
- 3 CSS 文件 `[data-tone="compli"]` / `[data-agent="compli"]` selector 改 `compliance` (色彩 token `--t-compli` 不动 · per CLAUDE.md §7)
- `auth_service/tests/test_users_jwt_rbac.py` 4 assertion 改
- `api_server.py` 3 处 (target_agent comment + _AGENT_SYSTEMS + _AGENT_TO_ID)
- `scripts/lint/check_agent_naming_ssot.py` PM_PENDING 集 → LEGACY_DEPRECATED + 加注 Q-042.B ratify

**例外保留** (Acceptable legacy)：
- `--t-compli` CSS 色彩 token (per CLAUDE.md §7 · CSS token 命名独立于 agent_id)
- `docs/audit/A4-compli-draft.md` (历史文件名 · 不改 git history)
- `agent_compliance/scan_engine.py` 内部 scan_id prefix `compli-{uuid}` (内部 ID 风格 · 不影响 API 契约)
- decisions-log 历史 Q-NNN 提及 `compli` (历史 audit trail · 不动)

**Lint enforcement** (Phase A 验收硬线 #8): `scripts/lint/check_agent_naming_ssot.py` 已 ratify · 后续 worker 引入新 `\bcompli\b` 字面将 ERROR (`compliance` 才合法)。

---

## 4. CI Lint Enforcement (Phase A 验收硬线 #8)

### 4.1 Hardline rule

> 任何 `agent_*/api.py` mount 路径 (FastAPI `@app.METHOD("/api/<id>/...")`) 必须与本 SSOT §1 agent_id 列共形 · 同时 `web/src/app/archive/<id>/` 目录必须存在 · `auth_service/rbac.py` `VALID_AGENTS` 必须共形 · `evaluation/<eval_baseline>.yaml` 必须存在。

**实现** (本 contract V2 commit 落地):

| 文件 | 作用 |
|---|---|
| `scripts/lint/check_agent_naming_ssot.py` | 校验脚本 · stdlib only · 含 5 check (C1-C5) + 1 status report (C6 PM-pending 双 id 分布显式列) |
| `.github/workflows/lint-contracts.yml` | GitHub Actions wiring · push to `main`/`chore/l0-infra`/`feat/**`/`chore/**`/`fix/**` + PR 触发 · 上传 JSON report artifact (14 天) |

**检查项**:

| code | 描述 | level |
|---|---|---|
| C1 | backend `/api/<prefix>/*` 是否在 SSOT agent_ids 内 | ERROR (PM-pending 行降 WARN) |
| C2 | `web/src/app/archive/<id>/` 目录存在 (PM-pending 行任一 alt 命中即 OK) | ERROR (pending 降 WARN) |
| C3 | `auth_service/rbac.py` `VALID_AGENTS` 与 SSOT agent_ids 双向共形 | ERROR (含 SSOT 缺反查 RBAC EXTRA) |
| C4 | `evaluation/<eval_baseline>.yaml` 文件存在 | ERROR (pending 行降 WARN) |
| C5 | `agent_<dir>/api.py` 目录后缀与 mount prefix 一致 (e.g. `agent_compliance/` + `/api/compliance/*`) | ERROR (pending 降 WARN) |
| C6 | PM-pending 双 id 跨栈分布报告 (e.g. `compli@[rbac, eval]` vs `compliance@[backend, frontend, eval]`) | WARN |

**当前现状 (V2 commit smoke run)**: 0 ERROR · 1 WARN (C6 · `compli` vs `compliance` 跨栈分裂 · 阻血 = PM 拍板 §3)。

### 4.2 后端 mount prefix 共形

| agent_id | api mount (api_server.py) | archive route |
|---|---|---|
| `channel` | `/api/channel` | `/archive/channel` |
| `report` | `/api/report` | `/archive/report` |
| `credit` | `/api/credit` | `/archive/credit` |
| `alert` | `/api/alert` | `/archive/alert` |
| `compliance` | `/api/compliance` | `/archive/compliance` |
| `riskctrl` | `/api/riskctrl` | `/archive/riskctrl` |

> ✅ **现状** (Stage 4 cleanup 2026-04-30): 全栈 `compliance` (backend `/api/compliance/*` + frontend `/archive/compliance/` + eval `agent5_compliance.yaml` + RBAC `compliance`) · 跨栈共形完成 · C6 WARN 应自动消失。

### 4.3 PM 拍板后 lint 已收紧 (Q-042.B 2026-04-29 + Stage 4 2026-04-30)

✅ Stage 4 cleanup 完成 · 已:
1. SSOT §1 row 5 锁单 id `compliance` (本 commit)
2. `scripts/lint/check_agent_naming_ssot.py` `PM_PENDING_AGENT_IDS` 改 `LEGACY_DEPRECATED_AGENT_IDS = {"compli"}` (新代码引入 `compli` 字面 ERROR · `compliance` 才合法)
3. `web/src/lib/auth/agent-id.ts` 改 identity 映射 (consumer API 稳定不动 · 解 audit Cat 8/10 · 不删文件以避免连锁 import 改动)
4. 重跑 lint · 0 WARN 0 ERROR · Phase A 硬线 #8 真 met

### 4.4 本地用法

```bash
py scripts/lint/check_agent_naming_ssot.py            # 默认 · WARN 不阻 · ERROR 阻
py scripts/lint/check_agent_naming_ssot.py --strict   # WARN 也判 fail · PM 拍板后 CI 用此模式
py scripts/lint/check_agent_naming_ssot.py --json     # JSON 机器输出 · CI 上传 artifact
```

### 4.5 前端 AgentDef.path 字段 deprecation

`web/src/lib/agents.ts:45-115` 6 处 `path: "/channel"` 等顶层路径 (audit Cat 9) → 顶层目录不存在 · 解决方案 (worker-A4 执行):
- (a) 改为 `path: "/archive/channel"` (canon)
- (b) 删 path 字段 · consumer 用 `route(agent.id)` helper 派生 (推荐 · 减少漂可能)

主 CLI 倾向 (b) · PM 默认追认 unless override。

---

## 5. 角色 SSOT (audit Cat 16 fix)

### 5.1 5 user role × 中文映射 (锚定 `auth_service/users.py:46-50`)

| backend role | 中文 (CLAUDE.md §1 锁) | 用户故事 |
|---|---|---|
| `rm` | 客户经理 | 王哲 (华东 · 主用户) |
| `credit_officer` | 审贷员 (注: 不是"审贷官") | 张敏 (审贷会 · Agent3 主消费者) |
| `compliance_officer` | 合规官 | 李华 (合规审查 · Agent5 主消费者) |
| `risk_manager` | 风险经理 (注: 不是"策略经理") | 陈凯 (Agent2/4 主消费者) |
| `admin` | 管理员 (内部 · 非业务) | (开发 / 配置) |

### 5.2 audit Cat 16 dangling fix (本 SSOT 落地后须执行)

| 处 | 当前 | 应改 | Owner |
|---|---|---|---|
| `CLAUDE.md` §4 表 row 2 (Agent2 风控) | "**策略经理**发起" | "**风险经理**发起" | worker-A1 同 commit (本 SSOT 一并) |
| `web/src/lib/store/types.ts:28` | `Role` 注释 `credit_officer="审贷官"` | `credit_officer="审贷员"` | worker-A4 (frontend cleanup) |
| `api_server.py:376` IM prompt riskctrl | "辅助**策略经理**写 DSL" | "辅助**风险经理**写 DSL" | 主 CLI fix-forward |

---

## 6. Versioning + Migration

### 6.1 Version

| 版本 | 日期 | 变更 | Author |
|---|---|---|---|
| v1.0 | 2026-04-29 | Initial · 6 agent × 8 列 · PM compli/compliance 占位 · §4 CI lint 规则 | worker-A1 |

### 6.2 改本 SSOT 流程

- 任何字段值变更 → 走 `shared-change-protocol.md` RFC
- worker 不允许直改 · 仅 read 引用
- PM 拍板 §3 → 主 CLI 同 commit 更 §1 + §3 标 RESOLVED + bump 到 v1.1

---

## 7. Cross-reference

- `field-naming.md` v1.0 · §3 enum 字典 · 本 SSOT 对齐 (segment / business_line 与 agent_id 正交 · 不冲突)
- `workspace-state-protocol.md` v1.1 · §10 AgentSession 内 agent-specific tail 按本 SSOT agent_id 命名
- `instruction-source-of-truth.md` (本批 contract #5) · 当 SSOT 与 CLAUDE.md 漂时 · SSOT 优先 (合 contract > root CLAUDE.md 优先级)
- `auth-protocol.md` · RBAC matrix 单源 · 本 SSOT 引用而不重复
- `CLAUDE.md` §4 (6 Agent 边界 · 触发 / 输入 / 产出) + §11 (各 Agent 版本) · 本 SSOT 锁命名 · CLAUDE.md 锁业务

---

## 8. 验收 (Phase A 硬线 #8 落地标志)

本 SSOT v1.0 commit 时:
- ✅ 5/6 agent 8 列已锁 (除 compli/compliance 字段值待 PM)
- ✅ §3 PM 拍板项独立 · 标黄 · 不阻 ratification
- ✅ §4 CI lint 规则定义 + V2 已落地 (`scripts/lint/check_agent_naming_ssot.py` 真脚本 + `.github/workflows/lint-contracts.yml` workflow · commit `c994036`)
- ✅ §5 audit Cat 16 dangling fix 同 commit 回写 CLAUDE.md §4
- ✅ §4 CI lint 真落地 → Phase A 硬线 #8 implementation MET (default mode 0 ERROR · 1 WARN intentional · PM 拍板后 `--strict` 升 ERROR 即 0/0 完整 met)
- ⏳ §3 PM 拍板 → bump v1.1 (后续 commit · 阻 `--strict` 模式启用)
