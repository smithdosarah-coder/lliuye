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

> ⚠️ `agent_id` 列对 `compliance/compli` 留 PM 占位 (§3) · 其余 5 行已锁。

| agent_id | 中文 | 业务名 | UI brand | route (canon) | 色彩 token | RBAC role | eval baseline |
|---|---|---|---|---|---|---|---|
| `channel` | 全渠道获客 | look-alike 获客 (基于已成交客户外网搜相似企业) | 全渠道获客 | `/archive/channel` | `--t-channel` (#3C7B7B 青绿) | `rm` / `admin` | `evaluation/agent1_channel.yaml` |
| `report` | 信贷报告助手 | Agent6 报告 (Evidence-First 三阶段 + QC blocker) | 信贷报告助手 | `/archive/report` | `--t-report` (#B08640 棕赭) | `rm` / `credit_officer` / `compliance_officer` / `risk_manager` / `admin` | `evaluation/agent6_report.yaml` |
| `credit` | 授信决策辅助 | Agent3 授信 (Agent6 下游 · 对公+对私+普惠 三板块四维评分) | 授信决策辅助 | `/archive/credit` | `--t-credit` (#3E6292 青蓝) | `rm` / `credit_officer` / `risk_manager` / `admin` | `evaluation/agent3_credit.yaml` |
| `alert` | 贷中风险预警 | Agent4 预警 (客户行为变化驱动 · 红/黄/绿榜单) | 贷中风险预警 | `/archive/alert` | `--t-alert` (#C85A3C 赭红) | `rm` / `credit_officer` / `compliance_officer` / `risk_manager` / `admin` | `evaluation/agent4_alert.yaml` |
| **🟡 compli\|compliance** (PM TBD §3) | 合规巡检 | Agent5 合规 (政策事件驱动 · 业务矩阵冲突点) | 合规巡检 | `/archive/<TBD>` | `--t-compli` (#5B7A48 墨绿) | `compliance_officer` / `admin` | `evaluation/agent5_compliance.yaml` (PM TBD 后改) |
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

**红线**: consumer 一律 read-only 引用本 SSOT · 不允许在 consumer 文件**重复定义**或**镜像**字段值。`web/src/lib/auth/agent-id.ts` 补丁映射在 PM 拍板 §3 后由 worker-A4 删除。

---

## 3. 🟡 PM 拍板待裁: `compli` vs `compliance` 单 id 选一

**背景**: 当前全栈双 id 分裂 · 补丁文件 `web/src/lib/auth/agent-id.ts:1-18` 是症状不是治本 (audit Cat 8 + 10)。

### 选项 A: 全栈统一 `compliance` (语义 · 与 eval baseline 一致)

**优点**:
- 与 `evaluation/agent5_compliance.yaml:3 agent: compliance` 一致 · eval baseline 不动
- 与 `web/src/lib/agents.ts:20 AgentKey="compliance"` 一致 · 前端 6 import 不动
- 语义完整 · "合规" → "compliance" 自然映射
- 与 `auth_service/users.py` `compliance_officer` role 命名一致

**改动量**: ~5 处 (backend 偏小)
- `auth_service/rbac.py:42` VALID_AGENTS 改 `compli` → `compliance`
- `web/src/lib/store/auth-store.ts:36-40` ACCESS key 改
- `web/src/lib/store/types.ts:12` AgentId enum 改
- `auth_service/tests/test_users_jwt_rbac.py` fixture 改
- decisions-log 历史 Q-NNN 提及 `compli` 处加注 · 不实改
- 删 `web/src/lib/auth/agent-id.ts` 补丁文件

### 选项 B: 全栈统一 `compli` (短 · backend 已用)

**优点**:
- backend `auth_service/rbac.py` + `users.py` 已用 `compli` · backend 不动
- `compli` 比 `compliance` 短 4 char · URL / token / log 节省
- 与 `--t-compli` 色彩 token 一致

**改动量**: ~12 处 (frontend + eval 偏大)
- `web/src/lib/agents.ts:20` AgentKey 改 `compliance` → `compli` · 6 处 import 跟着改
- `evaluation/agent5_compliance.yaml:3` agent: compli + 文件改名 `agent5_compli.yaml`
- `evaluation/runner/adapters/agent5_compliance.py` 跟改
- `docs/contracts/agent-compli-spec.md` 已是 compli (不用动)
- `web/src/components/shell/AuthGate.tsx:21` regex 不动
- 删 `web/src/lib/auth/agent-id.ts` 补丁文件

### Tradeoff matrix

| 维度 | 选项 A `compliance` | 选项 B `compli` |
|---|---|---|
| 语义清晰度 | ✅ 完整词 | ⚠️ 缩写 (但与 `riskctrl` 风格一致) |
| 改动量 | ⭐⭐ 5 处 | ⭐ 12 处 |
| URL/RBAC 长度 | ⚠️ 偏长 | ✅ 短 (与 `riskctrl` 一致) |
| 与现有 evaluation yaml 兼容 | ✅ 不动 | ❌ rename 1 文件 + adapter 改 |
| 与 backend 风格一致 | ❌ 反向改 backend | ✅ backend 不动 |
| `compliance_officer` role 命名 | ✅ 一致 | ⚠️ role `compliance_officer` 但 agent_id `compli` (轻微割裂) |

**主 CLI 不预决** · 留 PM 拍板 (per worker-A1 onboarding §3 #4)。一旦 PM 选定:
- Worker-A1 同 commit 改本 SSOT §1 表 + §3 标 RESOLVED
- 主 CLI fire 后续 worker (主线 worker-A4 或 fix-forward batch) 执行 §3 列出的具体 file 改动
- `web/src/lib/auth/agent-id.ts` 补丁文件由 worker-A4 删除 + commit `Signal: COMPLI-AGENTID-PATCH-REMOVED`

---

## 4. CI Lint Enforcement (Phase A 验收硬线 #8)

### 4.1 Hardline rule

> 任何 `agent_*/api.py` mount 路径 (FastAPI `prefix=...`) 必须在本 SSOT §1 `route` 列里。

**实现**: `scripts/lint/check_agent_naming_ssot.py` (Phase A worker-A2 或 主 CLI fix-forward 落地)

```python
# Pseudocode
SSOT_ROUTES = parse_ssot_md("docs/contracts/agent-naming-ssot.md")
# {"channel": "/archive/channel", "report": "/archive/report", ...}

for f in glob("agent_*/api.py"):
    mount = grep_mount_prefix(f)  # e.g. "/api/channel"
    agent_id = parse_agent_id_from_filename(f)  # "channel"
    expected_api_prefix = f"/api/{agent_id}"
    expected_archive_route = SSOT_ROUTES[agent_id]
    assert mount == expected_api_prefix, f"{f} mount {mount} != SSOT {expected_api_prefix}"
    # 同时 check web/src/app/archive/<id>/ 目录 exists
    assert exists(f"web/src/app/archive/{agent_id}/"), f"route {expected_archive_route} 目录不存在"
```

### 4.2 后端 mount prefix 共形

| agent_id | api mount (api_server.py) | archive route |
|---|---|---|
| `channel` | `/api/channel` | `/archive/channel` |
| `report` | `/api/report` | `/archive/report` |
| `credit` | `/api/credit` | `/archive/credit` |
| `alert` | `/api/alert` | `/archive/alert` |
| `compli\|compliance` (TBD) | `/api/<id>` | `/archive/<id>` |
| `riskctrl` | `/api/riskctrl` | `/archive/riskctrl` |

### 4.3 前端 AgentDef.path 字段 deprecation

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
- ✅ §4 CI lint 规则定义 (实现待 worker-A2)
- ✅ §5 audit Cat 16 dangling fix 同 commit 回写 CLAUDE.md §4
- ⏳ §3 PM 拍板 → bump v1.1 (后续 commit)
- ⏳ §4 CI lint 真落地 → Phase A 硬线 #8 met (worker-A2 / 主 CLI fix-forward)
