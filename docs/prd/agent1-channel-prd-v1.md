# Agent1 全渠道获客 (channel) · sub-PRD v1

**agent_id**: `channel` (per `docs/contracts/agent-naming-ssot.md` v1.0)
**Status**: 🟡 v1 draft · pending PM ratification (per master PRD §3.1 G-01/G-02)
**Owner**: 主 CLI · 修改走 RFC · worker A4-channel 实施
**Phase**: Phase A end (Rewrite acceptance) + Phase B (深化候选源)
**作者**: worker-A7 · 2026-04-29

---

## 1. Original Intent (verbatim · 飞书 wiki + 本地 PRD v2.0 锚)

**飞书源**: https://fcntbrvzmfph.feishu.cn/wiki/QOzbwMgyciBkfWko5Z3cmIfhnhf (node: `QOzbwMgyciBkfWko5Z3cmIfhnhf` · "01 · 全渠道流量匹配智能体")
**本地 fallback**: `docs/PRD_全渠道流量匹配智能体_v2.0.md`

客户经理上传"已有优质客户名录 + 政策文件"三类知识库 · Agent 抽出**理想客户画像** · 遍历外网企业池 · 找出与画像最相似的 **Top10 新客户线索** · 每条线索附匹配理由 + Top3 产品推荐。

**核心隐喻**: **look-alike 获客引擎** · 不是单查工具或产品推荐表。

> ⚠️ 名称漂: 飞书 / 本地 PRD 称"全渠道流量匹配" · 实际产品形态是 look-alike 引擎 (per `docs/reset/north-star.md` §1.3 PM 早决议)。本 sub-PRD 以 look-alike 为准 · 客户走访前文案统一为 "look-alike 获客"。

---

## 2. Current Repo State (2026-04-29)

### 2.1 后端

`agent_channel/api.py:1-10` 暴露 5 端点:
- `GET /api/channel/scenarios` (3 scenario fixture)
- `POST /api/channel/run` (SSE look-alike 搜索 · 阶段事件)
- `POST /api/channel/export_xlsx`
- `POST /api/channel/export_docx`
- `POST /api/channel/handoff` (移交 Agent3)

### 2.2 前端

`web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (F-005):
- `docs/features-inventory.md:62-68` 标注 **"NEVER CORRECTLY DELIVERED · 产品定位错 · 待重做"**
- QueryBar 实装为"自由搜索标签"输入 · 不是 KB 文件上传 grid
- 无 Top3 产品推荐 panel
- 候选 candidate 缺 `industry / geo / scale / similarity` 4 字段中部分 (per Q-041 active rule · CLAUDE.md §3.7.2)

### 2.3 数据源

- `shared/sources/impls/{tavily, enterprise_info, akshare}.py` 已建 (BaseSource 协议)
- `agent_channel/sources_config.py` 配置 fallback chain
- `realtime_stream.py:339` Tavily key 缺时**silent mock_fallback** (违 banner-spec § 3.5)

### 2.4 评估

- `evaluation/agent1_channel.yaml` baseline yaml 已建
- 5 通用指标 + 5 信贷专业指标中 "信号多样性 (每候选 ≥ 2 种信号类型)" 适用本 agent

---

## 3. Drift Gap (本 sub-PRD · G-01 + G-02)

### 3.1 G-01 · 前端 QueryBar 产品形态错位 (KRR: 🟢 Rewrite)

| 维度 | 内容 |
|------|------|
| Original | KB 文件上传 (已成交客户名录 + 政策 + 产品目录) → 抽画像 → 外网遍历 → Top10 + 匹配理由 + Top3 产品 |
| Current | F-005 QueryBar 自由搜索标签 · 无 KB grid · 无 Top3 产品 panel · features-inventory.md:62-68 "NEVER CORRECTLY DELIVERED" |
| KRR | 🟢 **Rewrite** · 产品形态错位 · 必须改 KB 文件上传驱动 · MVP 路径不可妥协 |
| Phase | Phase A end |
| Owner | A4-channel (依赖 A3 channel pilot 4 gate 模板完) |
| Acceptance | KB 上传 grid + 外网遍历 SSE + Top10 候选 panel + Top3 产品 panel · F-005 inventory 改 RECOVERED · `web/tests/regression/channel-pilot-4gate.spec.ts` Playwright smoke pass |

### 3.2 G-02 · 外网企业池真实遍历 + banner (KRR: 🟢 Rewrite)

| 维度 | 内容 |
|------|------|
| Original | SearchProvider 实搜外网 50+ 家 (Tavily / 企查查 / 企信宝) · 候选含 `industry/geo/scale/similarity` 4 字段 (Q-041 active rule) · 候选不足显式 banner `blocked_by_env` · 不 silent mock |
| Current | KB_DEMO mock 路径仍存 · `agent_channel/realtime_stream.py:339` Tavily key 缺时 silent mock_fallback (conflict-register Cat 11-4) · banner-spec 规则 2 未实装 |
| KRR | 🟢 **Rewrite** · silent fallback 违 banner-spec § 3.5 形态硬线 + bank delivery DoD 体验红线 |
| Phase | Phase A end |
| Owner | A3 (channel pilot · banner-spec 实装) + A4-channel (实搜接通) |
| Acceptance | Tavily key 缺时显 banner + 50+ 候选返 + 4 字段全 (per CLAUDE.md §3.7.2) + smoke `channel-pilot-4gate.spec.ts` 含 banner case |

---

## 4. 产品形态详细 (Phase A end MVP)

### 4.1 用户旅程 (RM workbench 内调用 channel tile)

1. RM 在 `/today` workbench 点 channel tile → 跳 `/archive/channel`
2. 上传 3 类 KB (拖拽 grid · `.xlsx/.csv/.pdf/.docx`):
   - 已成交优质客户名录 (≥ 50 行 · 推荐 100 行 · per drift §3.5 mock 5 原则)
   - 政策 / 准入 / 风偏文档 (定 ideal profile 边界)
   - 银行产品目录 (供 Top3 推荐池)
3. Agent 抽 ideal profile (industry / geo / scale / 财务画像 / 经营年限 等) → 显示给 RM 确认 / 修订
4. SSE `/api/channel/run` 启动 → 阶段事件 `extracting_profile / scanning_external / ranking / matching_products`
5. 候选返 Top10 · 每条:
   - 4 字段必出: `industry` / `geo` / `scale` / `similarity` (0-1)
   - 匹配理由: ≥ 1 句 grounded 在 KB 锚定 (citations 必带)
   - Top3 产品推荐 (从产品目录 score)
6. RM 选定 N 家 → 一键 handoff 到 Agent6 出尽调报告

### 4.2 Banner-spec 触发条件 (per `docs/contracts/live-fallback-banner-spec.md`)

| 触发 | banner 文案 | UX |
|------|------------|-----|
| Tavily key 缺 | "外网搜索 key 未配置 · 当前用 Mock 数据演示" | 黄色 · 顶端 sticky |
| 候选 < 5 家 | "外网池太小 · 仅返 N 家 · 建议拓宽 KB 或检查搜索源" | 橙色 |
| 0 家命中 | "未找到相似企业 · 请检查 KB 是否过窄" | 红色 · 阻断 handoff |

silent fallback 视作 regression · Playwright smoke 必含 3 banner case。

---

## 5. Phase 拆分

### 5.1 Phase A end 必出

- G-01 KB 上传 grid + 外网遍历 SSE + Top10 + Top3 产品 panel · F-005 RECOVERED
- G-02 banner-spec + 4 字段 (Q-041 enforce)
- channel-pilot 4 gate (`started / selectedSession / liveData / selectedCandidate`) 实装 (依赖 A3 pilot 模板)
- Playwright smoke `channel-pilot-4gate.spec.ts` pass

### 5.2 Phase B 深化 (不阻 Phase A)

- 候选源扩充: 企查查 / 企信宝 真实接 (Tavily 之外)
- ideal profile 抽取**模型迭代**: prompt + few-shot 优化 · 提升画像质量
- Top3 产品推荐**评分模型**: 从启发式 → 数据驱动 (基于历史成交数据微调)
- Agent1 → Agent6 handoff 真消费 channel 候选 (跨 Agent 工作流)

---

## 6. 不做 (per CLAUDE.md §4 + master PRD)

- ❌ 授信决策 (是 Agent3 职责 · channel 仅出候选不打分)
- ❌ 财务审计或合规判定 (Agent5 / Agent6 职责)
- ❌ 不写关键词 / 正则黑名单兜底幻觉 (CLAUDE.md §3.1 红线)
- ❌ 不 silent mock fallback (banner-spec 规则 2 硬线)
- ❌ 不在前端 inline mock data (违 CLAUDE.md §3.5)

---

## 7. 评估锚定 (per master PRD §5.2)

- **Baseline yaml**: `evaluation/agent1_channel.yaml`
- **API 版本对齐**: Agent1 v4.0 (信号驱动搜索 · 2026-04-16)
- **通用指标**: `field_completeness` (4 字段必出率 ≥ 99%) · `evidence_rate` (匹配理由必引用 KB) · `tool_success_rate` (实搜 vs mock 占比 · 实搜 ≥ 80% with key)
- **信贷专业**: 信号多样性 (每候选 ≥ 2 种信号类型: 工商 + 财务 / 经营 / 司法 等) · ideal profile 与人工复核一致率 ≥ 75%

---

## 8. 引用

- Tier 1: `docs/contracts/agent-naming-ssot.md` v1.0 + `live-fallback-banner-spec.md` + `sse-envelope.md` v1.0 + `enterprise_profile.md`
- Tier 2: CLAUDE.md §3.5 (mock 5 原则) + §3.7.2 (Q-041 4 字段 active rule) + §4 (Agent1 边界) + 本 sub-PRD ↔ master-2026-04-29.md §3.1
- Tier 5: decisions-log Q-041 (candidate 4 字段) + Stage B.5 (channel SSE 全字段)
- 飞书: https://fcntbrvzmfph.feishu.cn/wiki/QOzbwMgyciBkfWko5Z3cmIfhnhf

---

**作者**: worker-A7 · Phase A Week 2-3 · 2026-04-29
**状态**: v1 draft · pending master PRD ratification
