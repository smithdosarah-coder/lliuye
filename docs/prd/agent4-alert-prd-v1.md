# Agent4 贷中风险预警 (alert) · sub-PRD v1

**agent_id**: `alert` (per `docs/contracts/agent-naming-ssot.md` v1.0)
**Status**: 🟡 v1 draft · pending PM ratification (per master PRD §3.1 G-07)
**Owner**: 主 CLI · 修改走 RFC · worker A4-alert + data-foundation 协作实施
**Phase**: Phase A end (流水 upload + 解析) + Phase B-3 (双路 cross e2e)
**作者**: worker-A7 · 2026-04-29

---

## 1. Original Intent (verbatim · 飞书 wiki + 本地 PRD v2.0)

**飞书源**: https://fcntbrvzmfph.feishu.cn/wiki/YrjDwayKIi6BqJkpfgncb1Qvn5c (node: `YrjDwayKIi6BqJkpfgncb1Qvn5c` · "06 · 贷中风险预警助手")
**本地 fallback**: `docs/PRD_贷中风险预警助手_v2.0.md`

客户经理 / 风险经理上传"在贷客户池 + 预警规则库 + 内部制度"三类知识库 · Agent **批量遍历全量客户** · **双路交叉命中** (外部扫描域 + 内部交易域) · 吐出**分级榜单**:

```
红 (高危 · 立即处置)
黄 (观察 · 7 天内复检)
绿 (正常)
```

**核心隐喻**: **知识库驱动的批量贷中预警雷达** · 不是单企业查询工具。

**双路交叉**:
- **外部扫描域**: 工商变更 / 司法 / 舆情 / 行业 (走 `shared/sources/` SearchProvider)
- **内部交易域**: 客户在本行的流水 / 还款行为 / 关联账户 (走客户上传的内部数据)

任一路命中 + 双路命中 → 不同等级。

---

## 2. Current Repo State (2026-04-29)

### 2.1 后端

`agent_alert/api.py:1-20` 暴露 5 端点 (CLAUDE.md §11 v3.1):
- `POST /api/alert/scan` (SSE · 批量扫描 · 阶段事件)
- `POST /api/alert/export_docx`
- `GET /api/alert/hitlist` (红/黄/绿榜单持久化)
- `GET /api/alert/drill/{cid}` (单客户 drill + LLM 处置建议)
- `GET /api/alert/health`

### 2.2 前端

`web/src/app/archive/alert/_components/AlertWorkspace.tsx` (F-020~F-023 + F-049/F-055):
- features-inventory.md:227-260, 589-651 三灯墙 + 队列 + drill 已实装
- 4 gate state 模型缺 (conflict-register Cat 2-1 · 跟 channel pilot 模板对齐)

### 2.3 数据源

- 外部扫描: Tavily 实搜路径有 401 fallback (W-C3-A3) · 实际外部信号源 (企查查 / 企信宝) **未接**
- 内部交易域: **仅 KB_DEMO 解锁模式** · 流水 upload + 解析 endpoint **未接**

### 2.4 评估

- `evaluation/agent4_alert.yaml` baseline yaml 已建
- 信贷专业 "信号多样性 (每客户 ≥ 2 种信号类型)" 适用

---

## 3. Drift Gap (本 sub-PRD · G-07)

### 3.1 G-07 · 内部交易域真实数据接入 (KRR: 🟢 Rewrite)

| 维度 | 内容 |
|------|------|
| Original | 客户上传"在贷客户池 + 内部流水 + 预警规则库"三类 KB → 双路交叉命中 → 红/黄/绿榜单 |
| Current | 三灯墙 + drill 已实装 · 但内部交易域**仅 KB_DEMO 解锁** · 流水 upload + 解析 endpoint 未接 |
| KRR | 🟢 **Rewrite** · 内部交易域是 PRD 核心能力 (双路交叉非单路) · 不接流水 = 半 Agent · 违 §3.5 形态硬线 (mock 不替 Agent 做"本该外搜的工作") |
| Phase | Phase A (流水 upload + 解析) + Phase B-3 (双路 cross e2e) |
| Owner | A4-alert + data-foundation worker (per Q-028 5 原则 · 多表 csv 形态) |
| Acceptance | 流水 upload endpoint + 解析 + 跨域 hit list smoke pass |

---

## 4. 产品形态详细 (Phase A end MVP)

### 4.1 用户旅程 (客户经理在 RM workbench 调 alert tile)

1. RM 上传 3 类 KB:
   - **在贷客户池** (csv · 含 cid / 企业名 / 在贷余额 / 到期日 等基础字段 · ≥ 100 行 · per §3.5 反 5 原则)
   - **预警规则库** (yaml/json · 触发条件 + 等级映射)
   - **内部流水** (多表 csv · 流水 / 还款行为 / 关联账户 · per CLAUDE.md §3.5 row Agent4)
2. 一键 `/api/alert/scan` (SSE · 阶段事件 `loading_kb / external_scan / internal_cross / ranking`)
3. 双路交叉:
   - 外部扫描域: 走 SearchProvider 实搜每客户 (工商变更 / 司法 / 舆情 / 行业)
   - 内部交易域: 解析流水 → 异常行为 (大额提现 / 集中划转 / 关联账户) → 与外部信号交叉
4. 三灯墙渲染:
   - 🔴 红 (双路命中 OR 严重单路) · 立即处置
   - 🟡 黄 (单路命中) · 7 天内复检
   - 🟢 绿 (无命中)
5. 客户级 drill: `/api/alert/drill/{cid}` → LLM grounded 处置建议 (引用具体信号 + 规则)
6. 一键 `/api/alert/export_docx` 导出榜单报告

### 4.2 双路交叉算法 (确定性 vs 概率性)

- **确定性**: 流水统计 (大额阈值 / 集中度) / 工商变更命中规则 → Python
- **概率性**: 舆情情感分析 / 处置建议自然语言 → LLM (走 `shared/llm_caller`)
- **禁止**: LLM 直接判定红黄绿等级 (走规则引擎 confirm)

### 4.3 LLM caller 迁移 (per CLAUDE.md §3.6)

`agent_alert/api.py` 直 `LLMClient(provider=...)` → 迁 `LLMCaller(agent_id="alert", endpoint="/api/alert/drill").chat()` · A4-alert 子任务实施。

### 4.4 4 gate state 模型 (per channel pilot 模板)

- `started`: 用户点扫描按钮
- `selectedSession`: 选定一个扫描 session
- `liveData`: SSE 流入中 · 三灯墙渐进式渲染
- `selectedCandidate`: 用户选定一个 cid drill into

依赖 A3 channel pilot 4 gate 模板 (Phase A 中段) · A4-alert 用模板复制。

---

## 5. Phase 拆分

### 5.1 Phase A end 必出

- 流水 upload endpoint: `/api/alert/upload_internal` (csv/xlsx · 多表)
- 流水解析模块: `agent_alert/internal_parser.py` (异常行为提取)
- 4 gate state 实装 (channel pilot 模板复制)
- LLM caller 迁 `LLMCaller(agent_id="alert")`

### 5.2 Phase B-3 推延

- G-07 双路 cross e2e: 真实外部 + 内部命中关联 (跨域信号 join)
- 真实外部源接入: 企查查 / 企信宝 (Tavily 之外)
- 处置建议模型迭代: prompt + few-shot 优化 · 提升 actionable 质量
- 历史扫描 session 管理 (复检追踪)

---

## 6. 不做 (per CLAUDE.md §4 + master PRD)

- ❌ 单企业手动查询 (是 Agent1 / Agent6 职责 · alert 仅批量)
- ❌ 授信决策 (Agent3 职责)
- ❌ 财务审计 (Agent5 职责)
- ❌ LLM 直接判定红黄绿等级 (规则引擎 confirm)
- ❌ 不替客户做"本该外搜的工作" (per §3.5 row Agent4 · 外部信号必走 SearchProvider 真搜)

---

## 7. 评估锚定 (per master PRD §5.2)

- **Baseline yaml**: `evaluation/agent4_alert.yaml`
- **API 版本对齐**: Agent4 v3.1 (知识库驱动批量扫描)
- **通用指标**: `tool_success_rate` (双路命中率 ≥ 80%) · `task_completion_rate` (批量扫描完成率 ≥ 95%)
- **信贷专业**: 信号多样性 (每客户 ≥ 2 种信号类型) · 红线判定准确率 (双路命中 → 红 准确率 ≥ 90%)

---

## 8. 引用

- Tier 1: `docs/contracts/agent-naming-ssot.md` v1.0 + `sse-envelope.md` v1.0 + `live-fallback-banner-spec.md` (Tavily key 缺时 banner)
- Tier 2: CLAUDE.md §3.1 (确定性边界) + §3.5 row Agent4 (mock 形态硬线 · 多表 csv) + §3.6 (LLM caller 迁) + §4 (Agent4 边界) + master-2026-04-29.md §3.1 G-07
- Tier 5: decisions-log Q-028 (反 5 原则 · 2026-04-24)
- 飞书: https://fcntbrvzmfph.feishu.cn/wiki/YrjDwayKIi6BqJkpfgncb1Qvn5c

---

**作者**: worker-A7 · Phase A Week 2-3 · 2026-04-29
**状态**: v1 draft · pending master PRD ratification
