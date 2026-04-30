# Agent5 合规巡检 (compliance) · sub-PRD v1

**agent_id**: `compliance` (V2 · PM 已拍 per Q-042 decisions-log · SSOT §3 stale marker 待 worker-A1 fix-forward)
**Status**: 🟡 v1 draft · pending PM ratification (per master PRD §3.1 G-08/G-09 · §7 open question 2 · `compli/compliance` 已 V2 删)
**Owner**: 主 CLI · 修改走 RFC · worker A4-compli 实施 (+ 主 CLI 跑 G-09 真路径验)
**Phase**: Phase A end (G-08 doc + G-09 验) + Phase B-3 (事件源真接 + G-09 Rewrite if 验后决)
**作者**: worker-A7 · 2026-04-29

---

## 1. Original Intent (verbatim · 飞书 wiki + 本地 PRD v2.0)

**飞书源**: https://fcntbrvzmfph.feishu.cn/wiki/ZMeywAaEJi7ALEkwb9uc4cFnnqc (node: `ZMeywAaEJi7ALEkwb9uc4cFnnqc` · "02 · 合规巡检智能体")
**本地 fallback**: `docs/PRD_合规巡检智能体_v2.0.md`

合规官上传"监管政策库 + 内部制度 + 业务数据"三类知识库 · Agent **把政策拆成规则集 / 业务拆成事件集** · 做 **N×M 矩阵比对** · 吐出**违规榜单** (严重 / 一般 / 观察) **精确到放款业务单号级**。

**触发源 (核心边界 · per CLAUDE.md §4)**: **政策发布事件驱动** · 不是定期巡检 · 不是手动巡检。

```
新政策发布
   ↓
事件订阅触发 → 拆解新规则
   ↓
N×M 矩阵 (新规则 × 业务事件)
   ↓
违规榜单 (业务单号 + 引用规则 + 等级)
```

---

## 2. Current Repo State (2026-04-29)

### 2.1 后端

`agent_compliance/api.py:1-22` 暴露 5 端点 (CLAUDE.md §11 v3.1):
- `POST /api/compliance/policy_scan` (SSE 4 阶段: 抽规则 → 抽事件 → N×M 矩阵 → 改/补/强修订书)
- `POST /api/compliance/matrix_check` (同步矩阵比对)
- `POST /api/compliance/export_docx`
- `GET /api/compliance/scan`
- `GET /api/compliance/health`

合规修订书 3 类型 (改 / 补 / 强) 已实现。

### 2.2 触发源现状 (核心 gap)

- `policy_scan` 端点为**手动上传触发**
- ❌ 无事件订阅 / webhook / cron
- ❌ 无银保监 / 央行公告 RSS feed 接入

### 2.3 前端

`web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx` (F-024~F-027):
- features-inventory.md:271-310 实装
- F-026 冲突矩阵 (doc × clause) · 业务单号粒度**待验** (G-09 KRR)

### 2.4 数据源

- `shared/sources/impls/{gov_cn, pbc_gov, flk_npc}.py` 已建 (政府公文 source)
- 但 `agent_compliance/scan_engine.py` 尚未消费这些 source 做事件订阅

### 2.5 评估

- `evaluation/agent5_compliance.yaml` baseline yaml 已建
- 信贷专业 "合规术语规范率" + "红线判定准确率" 适用

---

## 3. Drift Gap (本 sub-PRD · G-08 + G-09 · 双 🟡)

### 3.1 G-08 · 政策事件订阅驱动 (KRR: 🟡 PM 拍板 · 选 b 路 default)

| 维度 | 内容 |
|------|------|
| Original | 触发源 = 政策发布事件驱动 (新政策发布自动 push 触发巡检) |
| Current | policy_scan 端点为手动上传触发 · 无事件订阅 / webhook / cron |
| KRR | 🟡 **PM 拍板** · 事件驱动 vs 手动上传是 Agent5 与 Agent4 边界本质 (CLAUDE.md §4 触发列) · 但事件订阅工程量大 |
| MVP 路径 (b 路 default) | Phase A 保留手动 + 飞书 PRD 标 deferred · Phase B 接事件源 (银保监 RSS / 央行公告 webhook 模拟) |
| Phase | Phase A (doc acceptance "手动允许") + Phase B-3 (事件实装) |
| Owner | A4-compli (Phase A doc) + B-3 (事件实装 · Phase B-3 立项) |
| Acceptance | (b 路): Phase A 飞书 PRD 标 deferred + 文档 acceptance "手动允许 · 事件待 B" · Phase B end (银保监 RSS / 央行 webhook cron 真触) |

**PM open question 2** (per master PRD §7):
- (a) Phase A 真接事件 → A4-compli + 主 CLI fix-forward (工程量大 · 阻 Phase A end)
- (b) Phase A 仅文档 acceptance "手动允许 · 事件待 B" (本 PRD default · A7 建议)

### 3.2 G-09 · 违规榜单 UI 精度 (KRR: 🟡 验后决 · 选 a 路 优先)

| 维度 | 内容 |
|------|------|
| Original | 违规榜单 UI 精度 = 精确到**放款业务单号级** (而非合同级 / 客户级粗粒度) |
| Current | F-026 冲突矩阵 (doc × clause) 已实装 · 业务单号粒度**待验** · Drawer 对照纸是否含业务单号 cell click 未审 |
| KRR | 🟡 **验后决** · 主 CLI 跑真路径看 F-026 cell · 若已对接业务单号 = Keep · 若仅 doc/clause 粗粒度 = Rewrite |
| Phase | Phase A end (验) + Phase B-3 (Rewrite 时落地) |
| Owner | A4-compli (验后决 Keep / Rewrite) |
| Acceptance | F-026 cell click 显业务单号 OR PRD 显式 acceptance 落"合同级" (退一步) |

**主 CLI 验路径** (Phase A 内 · 不阻):
1. 启 dev server `cd web && npm run dev`
2. 跳 `/archive/compliance` workspace
3. 上传一组 KB (政策 + 业务) · 触发 matrix_check
4. 点 F-026 cell · 看 Drawer 对照纸是否含**业务单号字段**
5. 如有 → KRR Keep · 若无 → KRR Rewrite (走 Phase B-3)

### 3.3 ~~PM open question 3 · `compli` vs `compliance` 单 id~~ (V2 已删)

V2 (codex 5 issue 修): PM per Q-042 decisions-log 拍 **`compliance`** · SSOT §3 stale marker 待 worker-A1 fix-forward · 本 sub-PRD 全文 verbatim 用 `compliance` (文件名 / agent_id / route `/archive/compliance` / LLM caller endpoint 全统一)。

---

## 4. 产品形态详细 (Phase A end MVP · b 路)

### 4.1 用户旅程 (合规官在 RM workbench 调 compliance tile · Phase A 手动)

1. 合规官手动上传 3 类 KB:
   - **监管政策库** (pdf · 银保监 / 央行通知 / 司法解释 等)
   - **内部业务制度** (SOP · 准入 · KYC · 风偏 · 审查清单)
   - **业务数据** (csv · 含**放款业务单号** · 客户 · 产品 · 风险等级 · 等)
2. 一键 `/api/compliance/policy_scan` (SSE · 4 阶段):
   - 抽规则 (政策 → 规则集 N 条)
   - 抽事件 (业务 → 事件集 M 条)
   - N×M 矩阵比对
   - 改/补/强 修订书生成
3. 违规榜单渲染:
   - 严重 / 一般 / 观察 三档
   - 每条引用规则 ID + 业务单号 (G-09 验后决精度)
4. 修订书 3 类型一键 export_docx

### 4.2 Phase B-3 事件驱动 (G-08 真接)

```python
# Phase B-3 立项 · 模拟监管事件源
@scheduled(cron="0 */6 * * *")  # 每 6 小时
def poll_regulatory_feeds():
    new_policies = []
    for source in [GovCNSource(), PBCGovSource(), FLKNPCSource()]:
        new_policies.extend(source.fetch_since(last_poll_ts))
    for policy in new_policies:
        trigger_policy_scan(policy)  # 自动 push 触发巡检
```

事件源:
- 银保监会公告 RSS (https://www.cbirc.gov.cn/...)
- 央行公告 webhook
- 法律法规库 (`flk_npc` source)

### 4.3 LLM caller 迁移 (per CLAUDE.md §3.6)

`agent_compliance/scan_engine.py` 直 `LLMClient(provider=...)` → 迁 `LLMCaller(agent_id="compli", endpoint="/api/compliance/policy_scan").chat()` (compli 待 SSOT 决) · A4-compli 子任务实施。

---

## 5. Phase 拆分

### 5.1 Phase A end 必出

- G-08 (b 路): 飞书 PRD + 本地 PRD acceptance 显式标 "Phase A 手动上传允许 · 事件源 Phase B 接"
- G-09 验路径: 主 CLI 跑 F-026 真路径 · ratification 决 Keep / Rewrite (verbatim 落本 sub-PRD §3.2 acceptance)
- LLM caller 迁 `LLMCaller(agent_id="compliance")` (V2 · PM 已拍)

### 5.2 Phase B-3 推延

- G-08 真接: 银保监 RSS / 央行 webhook / cron · `poll_regulatory_feeds` 实装
- G-09 (if Rewrite 决): F-026 cell click 显业务单号
- 政策版本 diff (跨期对比 · 新规与旧规差异点高亮)
- 多机构政策矩阵 (跨监管层级 · 总行 / 分行 / 子行)

---

## 6. 不做 (per CLAUDE.md §4 + master PRD)

- ❌ 定期巡检 (Agent5 ≠ 定期巡检 · 触发源是政策事件)
- ❌ 财务审计 (是审计 / 内审职责 · 不是合规)
- ❌ 单企业查询 (Agent1/4/6 职责)
- ❌ LLM 直接判定违规 (规则引擎 confirm)
- ❌ 不写关键词黑名单兜底 (CLAUDE.md §3.1 红线)

---

## 7. 评估锚定 (per master PRD §5.2)

- **Baseline yaml**: `evaluation/agent5_compliance.yaml`
- **API 版本对齐**: Agent5 v3.1 (政策事件驱动)
- **通用指标**: `evidence_rate` (违规必引用规则 ID + 业务单号) · `hallucination_rate` (LLM 抽规则不编 ≤ 5%)
- **信贷专业**: 合规术语规范率 ≥ 90% · 红线判定准确率 ≥ 95%

---

## 8. 引用

- Tier 1: `docs/contracts/agent-naming-ssot.md` v1.0 (compliance ratified V2 · §3 stale marker 待 A1 fix-forward) + `sse-envelope.md` v1.0 + `llm-prompt-contract.md` v1.0
- Tier 2: CLAUDE.md §3.1 (确定性边界) + §3.6 (LLM caller 迁) + §4 (Agent5 边界 · 政策事件触发) + master-2026-04-29.md §3.1 G-08/G-09 + §7 open question 2 + 3
- 飞书: https://fcntbrvzmfph.feishu.cn/wiki/ZMeywAaEJi7ALEkwb9uc4cFnnqc

---

**作者**: worker-A7 · Phase A Week 2-3 · 2026-04-29
**状态**: v1 draft · pending master PRD + PM open question 2 + 3 ratification
