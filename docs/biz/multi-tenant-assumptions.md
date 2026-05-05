# 多租户架构假设 v1.0 · spec only · NOT 实装

> ⚠️ **OBSOLETE / REFERENCE-ONLY (Q-052 · 2026-05-04 · PM ratify)**: **永不实装 multi-tenant** · 客户全本地化部署 (一家一套 ECS · 物理天生隔离) · 不存在 SaaS multi-tenant 场景 · 本 doc 仅作为商务团队参考 (if 客户问 "你们怎么部署") · PM 不审 · 不再是 Phase B 验收硬线 (charter v2 #2 OBSOLETE) · 详 Q-052

> **版本**: v1.0 · 2026-05-04 · worker-B2-biz (Phase B Sprint 2 · BE11 doc-only)
> **性质**: **架构 spec / 数据模型 spec · 不实装**, 推 Phase C (per Codex R2 反对实装 · `BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` line 52)
> **审稿对象**: 主 CLI / 后端 worker / Phase C charter 起草者
> **下游**: Phase C 真实装时本 doc 进 RFC `docs/contracts/multi-tenant.md` v1.0 (走 §15 SSOT Tier 1)

---

## 0. 红线 (per phase-b-charter.md line 100-108 + Codex R2 line 52)

❌ **绝不实装**:
- 不动 `auth_service/users.py:46-50` 5 fixed user
- 不动 `audit_service/recorder.py:46-65` schema (不加 `tenant_id` 列)
- 不动 `shared/decision_ledger/schema.py:56-74` `LedgerEntry` (不加 `tenant_id`)
- 不动 `data/feedback/YYYY-MM-DD.jsonl` 路径 (不分 tenant 子目录)
- 不写 RBAC role · 复用现有 `auth_service/rbac.py` 4 + 1 角色
- 不动前端 `web/src/lib/store/auth-store.ts` user model
- 不创新 sqlite schema · 不写 alembic migration · 不写 backfill 脚本

✅ **仅做 doc**:
- 数据模型 spec (字段 / 关系 / 约束 / index 建议)
- 实装路径 (Step 1-6 序列 · 工程量 estimate)
- 与现有 SSOT 的对齐路径 (CLAUDE.md / decision-ledger.md / auth-protocol.md)
- 假设清单 (哪些假设需 Phase C 验证)

**触发实装条件** (per Codex R2): 至少 2 个 Pilot 客户签字 · OR 1 个 Pro 客户在谈 · OR PM 显式拍板 + `Authorized-By: PM` trailer。

---

## 1. 现状盘点 (single-tenant · 2026-05-04)

### 1.1 用户层 (per `auth_service/`)

```
USERS = {
  u_wangzhe   → role=rm                 / team=华东·上海第一支行
  u_lihua     → role=credit_officer     / team=华东·授信审查部
  u_zhoumin   → role=compliance_officer / team=总部·合规管理部
  u_chenkai   → role=risk_manager       / team=总部·风险管理部
  u_liuye     → role=admin              / team=AI 中台
}
```

5 fixed user · bcrypt hash · 单租户 (隐含 `tenant=zhongan_demo`)。`team` 字段是文本 · 没有 `org_id` 强约束。

### 1.2 audit log (per `audit_service/recorder.py:46-65`)

```sql
CREATE TABLE llm_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  user_id TEXT,                  -- nullable · 无 tenant 关联
  agent_id TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt TEXT,
  response TEXT,
  input_tokens INTEGER,
  output_tokens INTEGER,
  cost_cny REAL,
  latency_ms INTEGER,
  error TEXT,
  encryption_marker TEXT         -- Stage E.3 PIPL · null=plain · "aes-gcm-256"=encrypted
);
CREATE INDEX idx_user_ts ON llm_calls(user_id, ts);
CREATE INDEX idx_agent_ts ON llm_calls(agent_id, ts);
```

**问题**: 没 `tenant_id` · 全租户混在一张表 · 无法做 tenant 维度计费 / quota / 隔离。

### 1.3 decision ledger (per `shared/decision_ledger/schema.py:56-74` + CLAUDE.md §3.7.5)

```python
@dataclass
class LedgerEntry:
    decision_id: str
    agent_id: str
    endpoint: str
    ts: str
    input_hash: str
    output_hash: str
    evidence_chain: dict
    jurisdiction: str = DEFAULT_JURISDICTION   # "HQ" / "BRANCH" / "银" / "保" / "证"
    retention_class: str = RETENTION_STANDARD
    subject_name: str | None = None
    subject_id: str | None = None              # SHA-256 16-hex prefix · PII never plain
    reviewer_id: str | None = None
    ...
```

**问题**: 有 `jurisdiction` (近似 org_id) 但**无 `tenant_id`**。jurisdiction 是法律辖区 (银 / 保 / 证) · 不是商业租户。一个银行客户 = 一个 tenant · 但其内部决策可能跨 jurisdiction (e.g. 总行 + 分行)。

### 1.4 feedback / few-shot (per CLAUDE.md §6 + worker-B1 BE10)

```
data/feedback/YYYY-MM-DD.jsonl   ← 全租户混写
agent_*/prompts.py               ← 共享 prompt · few-shot 注入后所有租户共用
```

**问题**: feedback 没 tenant 维度 · 客户 A 的修正会污染客户 B 的 few-shot。这是 **Pro / Enterprise 档客户的硬退出条件** (训练数据不能离场)。

### 1.5 数据存储 (per `data/`)

```
data/
├── alert/                       ← Agent4 客户池 / 信号 · 单租户
├── audit/llm_calls.db           ← 全 tenant 混
├── channel_kb/                  ← Agent1 KB · 单租户
├── compliance/                  ← Agent5 政策库 · 单租户
├── feedback/YYYY-MM-DD.jsonl    ← 全 tenant 混
├── im/                          ← Slack 风对话 · 单租户
├── ledger/decisions.sqlite      ← 全 tenant 混
└── mock/                        ← demo fixture
```

**问题**: 没目录分租户 · 没 storage quota · 没 tenant 删除路径 (客户解约后数据保留 / 销毁政策不清)。

---

## 2. 多租户数据模型 spec (Phase C 实装目标)

### 2.1 三层实体关系

```
tenant (商业租户 · 一个银行 = 一个 tenant)
  │
  └── org (机构 · 一个 tenant 下 N 个 org · 总行 + 分行 + 子公司)
        │
        └── user (per `auth_service/users.py` 现 5 user · Phase C 扩到 N user 含 org_id)
```

| 实体 | 主键 | 外键 | 业务含义 | 例子 |
|---|---|---|---|---|
| `tenant` | `tenant_id` (string · slug 命名 · 如 `icbc` / `zhongan-demo` / `nbcb` ) | — | 商业合同主体 · 一份合同 = 一个 tenant | 工商银行 / 宁波银行 / 中安信科 |
| `org` | `org_id` (string · slug · 如 `icbc-hq` / `icbc-shanghai` ) | `tenant_id` (FK) | 机构层级 · 含 `parent_org_id` 自引用做树 | 工行总行 / 工行上海分行 / 工行普惠子公司 |
| `user` | `user_id` (string · 现 `u_wangzhe` 等) | `tenant_id` + `org_id` (FK 双键) | 自然人账号 | 王哲@工行上海分行 |

### 2.2 tenant 字段 spec

```python
@dataclass
class Tenant:
    tenant_id: str                # PK · slug · 不可改 · 与合同绑死
    name: str                     # 显示名 (中文 · "中国工商银行")
    name_en: str                  # 英文名 ("ICBC")
    pricing_tier: str             # "pilot" / "pro" / "enterprise" (per pricing-assumptions.md §3.1)
    contract_start: str           # ISO date · 合同起始
    contract_end: str             # ISO date · 合同到期 · 退出窗口前 30 天 alert
    deployment_mode: str          # "saas_shared" / "saas_dedicated" / "private" / "private_xinchuang"
    jurisdiction_default: str     # 默认 jurisdiction (per decision_ledger §3.7.5) · "银" / "HQ" 等
    data_residency: str           # "cn" (境内) / "cn-coastal" (境内沿海) / "cn-mainland" 等 · 法务签字
    encryption_required: bool     # 是否强制 audit log AES-GCM (per Stage E.3 PIPL)
    quota_pack: dict              # {agent_id: {monthly_limit: int, current: int}} · 计费用
    sla_tier: str                 # "5x8" / "7x24_4h" / "7x24_1h"
    status: str                   # "active" / "suspended" (欠费) / "exit_pending" / "deleted"
    created_at: str
    updated_at: str
```

### 2.3 org 字段 spec

```python
@dataclass
class Org:
    org_id: str                   # PK · slug
    tenant_id: str                # FK
    parent_org_id: str | None     # 自引用 · 总行 → 分行 → 支行
    name: str                     # "工行上海分行"
    org_type: str                 # "headquarter" / "branch" / "sub_branch" / "subsidiary"
    business_lines: list[str]     # ["对公", "普惠", "对私"] · per Agent3 三板块
    region: str                   # "华东" / "华南" / "西南" 等
    jurisdiction: str             # 覆盖 tenant default · "银" / "HQ" / "BRANCH"
    created_at: str
```

### 2.4 user 字段扩展 (兼容现 `auth_service/users.py`)

```python
@dataclass
class User:
    user_id: str                  # PK · 复用现 "u_wangzhe" 格式
    tenant_id: str                # FK · 新增
    org_id: str                   # FK · 新增 (替代现 `team` 文本字段)
    name: str                     # 现有
    role: str                     # 现有 · per `auth_service/rbac.py` 4 + 1 角色不变
    avatar: str                   # 现有
    password_hash: str            # 现有 · bcrypt
    status: str                   # "active" / "disabled" / "left"
    created_at: str
    last_login_at: str | None
```

**复用现 RBAC** (per phase-b-charter.md 红线 "复用现有 auth_service"): `auth_service/rbac.py:9-15` ACCESS matrix 不动 · 角色名不变 · 仅增 `tenant_id` + `org_id` 双字段做 row-level 隔离。

### 2.5 audit log 扩展

```sql
ALTER TABLE llm_calls ADD COLUMN tenant_id TEXT;
ALTER TABLE llm_calls ADD COLUMN org_id TEXT;
CREATE INDEX idx_tenant_ts ON llm_calls(tenant_id, ts);
CREATE INDEX idx_tenant_agent ON llm_calls(tenant_id, agent_id, ts);
```

**约束**: 现 `user_id` 字段 nullable 保留 · `tenant_id` 加 NOT NULL backfill 默认 `zhongan_demo` · 历史数据 backfill 一次性脚本。

### 2.6 decision_ledger 扩展

`shared/decision_ledger/schema.py` 增字段:

```python
@dataclass
class LedgerEntry:
    # ... 现 14 字段 ...
    tenant_id: str = "zhongan_demo"   # 新增 · 默认 demo
    org_id: str | None = None         # 新增 · nullable (跨 org 决策时 None)
```

`jurisdiction` 字段保留 (法律辖区 · 与商业租户解耦 · 一个 tenant 可跨 jurisdiction)。

### 2.7 数据目录 spec

```
data/
├── tenants/
│   └── <tenant_id>/                  ← 物理隔离 (Pro / Enterprise) OR 共享目录 (Pilot)
│       ├── alert/                    ← Agent4 客户池
│       ├── channel_kb/               ← Agent1 KB
│       ├── compliance/               ← Agent5 政策库
│       ├── feedback/YYYY-MM-DD.jsonl ← 租户私有 few-shot 来源
│       ├── im/                       ← 对话
│       ├── audit/llm_calls.db        ← Enterprise 档独立 audit (private)
│       └── ledger/decisions.sqlite   ← Enterprise 档独立 ledger (private)
├── audit/llm_calls.db                ← Pilot / Pro shared SaaS 共用
├── ledger/decisions.sqlite           ← Pilot / Pro shared
└── mock/                             ← demo fixture · 全租户共享只读
```

**Pilot 档**: 逻辑隔离 · `tenant_id` 列筛 · 共享 audit/ledger DB
**Pro 档 SaaS dedicated**: 独立 ECS instance · 数据目录 `tenants/<tenant_id>/` 隔离
**Enterprise 档 私有化**: 客户机房 · 数据完全本地 · `tenants/` 路径仅一个

### 2.8 few-shot 注入 spec (per CLAUDE.md §6 数据飞轮)

**Phase B 现状** (worker-B1 BE10 PoC):
```
data/feedback/YYYY-MM-DD.jsonl  ← 全租户共享
↓ scripts/extract_feedback_fewshots.py
agent_*/prompts.py              ← 共享 few-shot
```

**Phase C 多租户路径**:
```
data/tenants/<tenant_id>/feedback/YYYY-MM-DD.jsonl
↓ scripts/extract_feedback_fewshots.py --tenant <tenant_id>
data/tenants/<tenant_id>/few_shots/agent_*.json
↓ runtime: agent_*/prompts.py 读 tenant_id 加载对应 few-shot
```

**关键**: prompts.py 不嵌入 tenant few-shot · 而是 **runtime lookup** (`load_fewshot(agent_id, tenant_id)`) · 防止租户 A 数据污染租户 B prompt。

---

## 3. 隔离层级矩阵 (per pricing-assumptions.md §5)

| 维度 | Pilot (逻辑隔离) | Pro (物理隔离) | Enterprise (物理 + 网络隔离) |
|---|---|---|---|
| 计算实例 | 共享 ECS / Web 服务 | 独立 ECS instance OR 共享 + 强 quota | 客户机房 |
| 数据库 | 共享 sqlite · `tenant_id` 筛 | 独立 sqlite (Pro SaaS dedicated) OR 客户 PostgreSQL (私有化) | 客户 DB · 完全本地 |
| 文件系统 | 共享磁盘 · `tenants/<tenant_id>/` 目录 | 独立卷 | 客户磁盘 |
| 网络 | 公网 + Cloudflare tunnel | VPC + 客户白名单 IP | 客户内网 + VPN / 专线 |
| LLM endpoint | 我方 DeepSeek key (per CLAUDE.md §3.7.3 PIPL) | 我方 key OR 客户自带 key (BYOK) | 客户私有部署 LLM (DeepSeek-R1 / Qwen 本地) |
| Audit log | 共享 sqlite | 独立 sqlite | 客户托管 · 我方无访问 |
| Decision ledger jurisdiction | `HQ` 默认 | `HQ` / `BRANCH` 二选 | 5 enum 全开 + 客户自定义扩展 |
| Few-shot prompt | 共享 (Pilot 期不污染 · 因数据少) | 租户私有 (Pro 起强约束) | 客户私有 + 训练数据不离场 |
| 数据销毁 | 解约后 30 日 logical delete | 解约后 30 日物理 delete + 备份覆盖 | 客户自托管 · 我方仅留我方代码版本 |

---

## 4. 实装路径 (Phase C · ~8-10 周 wall-clock · per pricing-assumptions.md §6)

### Step 1 · schema migration (1.5 周)

**Backend**:
- `audit_service/recorder.py`: ALTER TABLE 加 `tenant_id` + `org_id` · backfill 默认 `zhongan_demo` / `zhongan_demo_hq` · 加 index
- `shared/decision_ledger/schema.py`: `LedgerEntry` 增 `tenant_id` + `org_id` 字段 · sqlite migration 同上
- `auth_service/users.py`: 5 user 加 `tenant_id="zhongan_demo"` + `org_id="zhongan_demo_ai_platform"` 等 · 兼容现 `team` 字段保留作 display name
- 新建 `shared/tenant/` 模块: `Tenant` / `Org` dataclass + `tenant_store.py` (sqlite-backed)

**Test**:
- `tests/shared/test_tenant_schema.py` · backfill 一致性 · index 命中
- 现有 `tests/audit_service/` + `tests/shared/test_decision_ledger.py` 全绿 (向下兼容)

**Verification**: 现 5 user 全 backfill `tenant_id=zhongan_demo` · `audit_service.recorder.list_calls(tenant_id="zhongan_demo")` 返全部历史

### Step 2 · row-level filter (1 周)

**Backend**:
- `auth_service/dependencies.py`: `require_user` 返 `current_user` 含 `tenant_id` + `org_id` · 注入 FastAPI context
- 6 Agent api.py: SSE event payload + ledger record + audit record 全部带 `tenant_id` (从 `current_user`)
- `audit_service.recorder.list_calls()` / `decision_ledger.query_*()` 加 `tenant_id` 必填参数
- Cross-tenant query 仅 `admin` 角色可走

**Test**:
- 跨租户尝试 → 403 Forbidden
- 同租户跨 org 访问 → role-based 判 (e.g. compliance_officer 跨 org 看 audit 通过 · rm 不通过)

### Step 3 · metering aggregation (1 周)

**Script**: `scripts/metering/daily_aggregate.py`

```python
# 读 audit_service.llm_calls + decision_ledger 上日数据
# 按 (tenant_id, org_id, agent_id, endpoint) 聚合
# 计算: total_calls / total_cost_cny / total_decisions / unique_users
# 落 data/metering/YYYY-MM-DD.jsonl
```

**Cron**: 每日 02:00 跑 (per worker-B1 BE10 weekly cron 模式)

### Step 4 · quota enforcement (1 周)

**Backend**:
- `auth_service/dependencies.py` 加 `check_quota(agent_id)` decorator
- 调用前查 `tenant.quota_pack[agent_id]` · `current >= monthly_limit` 时 fail-fast 返 402 Payment Required
- 错误 payload 含升级 link `/admin/upgrade` (Pro / Enterprise 引导)
- 每月 1 日 reset `current` (cron job)

**前端**:
- `web/src/lib/api/*.ts` 补 402 fallback handler · 引导用户看 quota dashboard

**Test**:
- Pilot tenant 超 quota → 402
- Pro / Enterprise unlimited → 不阻

### Step 5 · admin billing dashboard (1.5 周)

**前端**:
- 新页 `/admin/billing` (仅 admin 角色可见)
- 复用 shell v2 `_components/` 组件
- 展示: tenant × agent × endpoint × 月用量 + cost + ROI 折线 (per pricing-assumptions.md §3.3)

**Backend**:
- `/api/admin/billing/summary?tenant_id=xxx&month=YYYY-MM` 端点
- 数据源: `data/metering/*.jsonl` + sqlite

### Step 6 · billing reconciliation (2 周 · 视支付方式)

国内银行多 PO + 银行转账 · 不必 Stripe:
- 月底跑 reconcile 脚本 · 出 `tenant_id × 服务项 × 用量` Excel
- 走线下对账 + 财务出账单 + 客户付款 + 入账登记

海外客户 (如有): 接 Stripe · 但 Phase B / Phase C 早期不优先

**总 Phase C metering ~8 周 (Step 1-5 必做 · Step 6 可推 Phase D)**

---

## 5. 安全 + 合规约束 (per CLAUDE.md §3.7.3 PIPL + DoD §4.3)

### 5.1 PIPL / 数据出境

**Phase C 实装时硬约束**:
- `tenant.data_residency = "cn"` 时 LLM fallback chain 强制 `("deepseek", "dashscope")` (per `shared/llm_caller/retry.py:DEFAULT_FALLBACK_CHAIN`) · 不允许走 `moonshot` (海外路由)
- `audit_service.LLMCall.encryption_marker` 必须 `"aes-gcm-256"` (Stage E.3 PIPL)
- Enterprise 档 `data_residency = "cn-mainland"` 时跨 region 数据传输禁止 · 只能客户机房本地

### 5.2 数据销毁 (per `decision_ledger` retention class)

| Retention | 触发 delete | Pilot | Pro | Enterprise |
|---|---|---|---|---|
| `short` (90d) | 解约 + 90 日 | logical delete | physical delete | 客户托管 |
| `standard` (5y) | 5y 后 OR 解约 + 5y | logical | physical (5y 后) | 客户托管 |
| `long` (10y) | 10y 后 OR 解约 + 10y | logical | physical (10y 后) | 客户托管 |

**关键**: 解约触发 retention 倒计时 · 不立即删 (银保监 archive 强制)。

### 5.3 BYOK (Bring Your Own Key · Pro / Enterprise)

`tenant.deployment_mode in ("saas_dedicated", "private", "private_xinchuang")` 时:
- 客户提供自己的 LLM key (DeepSeek / DashScope / Moonshot)
- 客户提供自己的 AES-GCM master key (audit log 加密)
- 客户提供自己的 sqlite encryption key (SQLCipher · Phase C 加)

---

## 6. 前端改造 spec (Phase C · 不动现壳 v2)

per CLAUDE.md §7 platform shell v2 · 不动 4 view (`/today` / `/dispatch` / `/archive` / `/warroom`):

**Masthead 加 tenant switcher** (admin 跨租户运维用):
- 仅 admin 角色显示 · 默认 hidden
- 切租户后所有 API call 带 `X-Tenant-Id` header
- 普通 user 不显示 · 单租户写死

**`/admin/billing` 新页** (Step 5):
- shell v2 风格 · 复用 Masthead + Desk + Float-badge
- 4 卡片: tenant overview / agent usage breakdown / cost trend / ROI estimation
- 不在顶栏 · 仅 admin 角色 Desk 抽屉看到

**LoginForm / auth-store** (per `web/src/lib/store/auth-store.ts`):
- 加 `tenant_id` + `org_id` 字段 · 登录 response 返
- 不显式问用户租户 · 由 user_id → tenant 路由
- BYO domain (Enterprise 档): 客户专属 domain `<tenant>.liuye.me` 或 客户自有域名

---

## 7. 与 SSOT 的对齐路径 (per CLAUDE.md §15)

Phase C 实装时本 doc 升级路径:

| 时点 | 文档 | Tier | 操作 |
|---|---|---|---|
| Phase B 当前 | `docs/biz/multi-tenant-assumptions.md` | (非 SSOT · 仅 doc) | 写 |
| Phase C Step 1 启动前 | `docs/contracts/multi-tenant.md` v1.0 | Tier 1 (接口契约) | 走 RFC `shared-change-protocol.md` 立 |
| Phase C Step 1 完成 | `CLAUDE.md` §3.7.5 | Tier 2 | 加 active rule (per §3.7 回写硬规) |
| Phase C Step 5 完成 | `docs/contracts/decision-ledger.md` v1.x | Tier 1 | 加 `tenant_id` + `org_id` 字段更新 |
| Phase C 全完 | `docs/contracts/auth-protocol.md` v1.x | Tier 1 | 5 fixed user → multi-tenant user 模型 |

**回写时机**: Step 1 PR merge 同 commit 加 `ACTIVE-DECISIONS-BACK-WRITTEN: 1` trailer (per CLAUDE.md §15 active rule 回写硬规)。

---

## 8. 假设清单

| # | 假设 | 验证方式 | 风险 |
|---|---|---|---|
| M1 | tenant ↔ 银行 1:1 | 销售访谈 · 是否有客户要 1 tenant 多银行 (e.g. 跨行联营) | 中 |
| M2 | org 树 ≤ 4 层 (集团 → 总行 → 分行 → 支行) | 国有大行机构图调研 · 工行 5 层多 | 中 |
| M3 | RBAC 4 + 1 角色 + tenant_id 行级隔离够用 | Phase C 真客户 POC 验证 | 中 · 客户可能要自定义角色 (e.g. 风控部经理 vs 风控部员工) |
| M4 | Pilot 共享 sqlite 性能够 · 100 tenant × 100 RM | benchmark · sqlite 单文件读写并发 | **高** · 推荐 Pro 起换 PostgreSQL |
| M5 | data_residency `"cn"` 满足所有国内客户 | 法务 + 客户合规部签字 | 低 |
| M6 | BYOK 实装可推 Pro 起 (Pilot 不做) | 客户访谈 · Pilot 客户是否真要 BYOK | 中 |
| M7 | tenant 切换 (admin) 不破坏现 session | Phase C frontend test | 低 |
| M8 | retention class 解约触发 delete 不冲突银保监 archive 强制 | 法务签字 + 监管部访谈 | **高** · 银保监可能要 archive 不允许删 |
| M9 | audit log AES-GCM 加密对查询性能影响 ≤ 30% | benchmark | 中 |
| M10 | few-shot 租户私有不污染 prompts.py | 单测验 · per-tenant `load_fewshot()` | 低 |

> **M4 + M8 critical**: Phase C 启动前必须 spike 验证 · 否则架构白做。

---

## 9. 真实装条件 (per Codex R2 + PM 拍板)

**触发条件 (任一满足)**:
1. **2 个 Pilot 客户签字** · `tenant.contract_start IS NOT NULL` × 2
2. **1 个 Pro 客户在谈** · 走访 ≥ 3 次 · 出技术方案书
3. **1 个 Enterprise 客户表态意向** · 出 RFP 应答

**未触发 = 不实装**:
- Phase B 全程保持单租户
- 不 backfill `tenant_id`
- 不引入 multi-tenant 复杂度
- 不写 admin billing dashboard

**触发后 PM 走流程**:
1. PM 拍板 + decisions-log Q-NNN 立条目 + `Authorized-By: PM` trailer
2. 写 `docs/contracts/multi-tenant.md` v1.0 RFC
3. 起 Phase C Sprint 1 worker (`worker-C1-multi-tenant`) · 1 worktree
4. 8 周内交 Step 1-5 · Step 6 视客户付款方式推 Phase D

---

## 10. 风险登记

| # | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R1 | Phase C 启动时 schema 已积大量历史数据 · backfill 慢 | 中 | 中 (downtime) | Step 1 跑前 freeze write 1h · 用 `WAL` 模式跑 backfill |
| R2 | 共享 sqlite 性能瓶颈 (M4) | 高 | 高 | Pro 起强制 PostgreSQL · 代码层抽 ORM (现 raw sqlite3) |
| R3 | 客户要求 self-hosted 但 LLM key 我方持有 | 中 | 中 | BYOK 路径文档化 · Phase C Step 1 落 |
| R4 | 监管要求 audit log archive 与 retention delete 冲突 (M8) | 中 | 高 | 法务前置 · 解约触发"冷归档"而非 delete · 保留 5 / 10 年后真删 |
| R5 | tenant_id slug 重命名 (e.g. 客户改名) | 低 | 中 | tenant_id 不可改 · `display_name` 字段单独维护 |
| R6 | RBAC 4 + 1 角色不够 (M3) | 中 | 中 | 加 `custom_roles` 表 · `tenant.role_extensions: list[Role]` |
| R7 | Few-shot 跨租户泄漏 (M10 反证) | 低 | **极高** (合规事故) | 单测覆盖 · prompts.py 不嵌入 tenant 数据 · runtime lookup |
| R8 | Cloudflare tunnel 单租户 demo 域名不够 (Pro 起多 domain) | 低 | 低 | Pro 起客户专属 subdomain · `<tenant>.liuye.me` |

---

## 11. 与其他 doc 的对接

- `pricing-assumptions.md` §3.1 / §5: 三档定价 → 本 doc §3 隔离矩阵对应
- `pricing-assumptions.md` §6: metering 实装路径 → 本 doc §4 Step 1-6 详细
- `trial-flow-assumptions.md`: Pilot 期 tenant 创建路径 → 本 doc §2.2 `Tenant.status="active"` 触发
- `sales-playbook-v1.md`: 客户问"数据在哪 / 谁能看" → 本 doc §3 + §5 引用
- `docs/contracts/decision-ledger.md` v1.0: 现 jurisdiction → 本 doc §2.6 兼容
- `docs/contracts/auth-protocol.md`: 现 5 user → 本 doc §2.4 扩展
- `CLAUDE.md` §3.7.3 PIPL: → 本 doc §5.1 + §2.2 `data_residency`
- `CLAUDE.md` §3.7.5 decision ledger: → 本 doc §2.6

---

## 12. 修订日志

- v1.0 · 2026-05-04 · worker-B2-biz · 初稿 · doc-only · NOT 实装

**下一次修订触发**:
- §9 真实装条件之一满足 → 升 RFC `docs/contracts/multi-tenant.md` v1.0
- 销售访谈反证 M1-M10 任一假设 → 修对应 §
- Phase C 启动前 spike M4 / M8 验证完 → 修 §10 R2 / R4 缓解策略
