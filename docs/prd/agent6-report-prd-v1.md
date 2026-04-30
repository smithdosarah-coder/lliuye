# Agent6 信贷报告助手 (report) · sub-PRD v1

**agent_id**: `report` (per `docs/contracts/agent-naming-ssot.md` v1.0)
**Status**: 🟡 v1 draft · pending PM ratification (per master PRD §3.1 G-10)
**Owner**: 主 CLI · 修改走 RFC · worker A4-report 实施
**Phase**: Phase A end (G-10 工具栏 3 端点真接) + Phase B-3 (handoff 真消费 · per G-05/G-06)
**作者**: worker-A7 · 2026-04-29

---

## 1. Original Intent (verbatim · 飞书 wiki + 本地 PRD)

**飞书源** (主):
- https://fcntbrvzmfph.feishu.cn/wiki/E9z8wJnDRiaI4ckmeH1cYcQknXc (node: `E9z8wJnDRiaI4ckmeH1cYcQknXc` · "04 · 报告生成助手")
- https://fcntbrvzmfph.feishu.cn/wiki/JY93w1r0aibCeXkSEoLcs8F7nTw (node: `JY93w1r0aibCeXkSEoLcs8F7nTw` · "PRD 报告生成助手 规划版 v2.3")

**本地 fallback**: `docs/PRD_报告生成助手.md` (v1.0)

客户经理上传企业原始材料 (PDF / Word / Excel / 扫描件) + 模板 · 自动生成一份**可直接提交审批的 15000 字授信调查报告 (Word)**。

**Evidence-First 三层信息框架** (per CLAUDE.md §3.3):
1. **材料事实** (Python 精确计算 · `financial_analyzer.py`)
2. **行业上下文** (`industry_benchmark.py` 行业基准卡)
3. **分析推断** (LLM grounded · `section_generator.py` 三阶段 Evidence Protocol)

**输出**:
- ReportJSON (供 Agent3 下游消费 · per master PRD G-05)
- Word 报告 (15000 字 · 8 标准章节)

**核心隐喻**: **Evidence-First 报告引擎 + QC blocker** · 财务确定性计算 + LLM 消费 · **不让 LLM 现场算财务比率**。

---

## 2. Current Repo State (2026-04-29)

### 2.1 主管线 v16 (CLAUDE.md §11)

`v16_pipeline.py` 为 CLI 入口 + 7 个 `v16_*.py` 模块 (classifier → generator → QC gate):
- `v16_classifier.py` (材料分类)
- `v16_generator.py` (段落生成)
- `v16_op_handlers.py` (REWRITE / KEEP / SKIP / DELETE 操作)
- `v16_step1_extract.py` + `v16_step1_make_guide.py` + 3 `to_review_*.py` (review 工件)
- `v16_pipeline.py` (CLI 入口 · 跨步骤编排)

### 2.2 后端 API

`agent_report/api.py:1-23` 暴露完整 8 端点:
- v16 主管线 SSE: `/api/report/v16/fill` (classifier → generator → QC gate)
- 材料上传 / 解析
- 章节重写
- docx 导出
- 下载等

### 2.3 前端

`web/src/app/archive/report/_components/ReportWorkspace.tsx` (F-009~F-014):
- ScanCTA 5 步流程 / 模板面板 / 材料上传 grid / 时间流 / A4 预览 + FieldChip 3 态 / 工具栏 5 操作
- F-014 工具栏 5 操作:
  - ✅ Word 导出 (通)
  - ✅ 打印 (通 · 走浏览器 print)
  - ❌ PDF 导出 (mock hook · 不调后端)
  - ❌ 分享链接 (mock hook · 不调后端)
  - ❌ 版本时光机 (mock hook · 不调后端)
- F-014 smoke test pending

### 2.4 关键文件 (CLAUDE.md §10)

- `financial_analyzer.py` (确定性财务指标 · 43k 行规模 · 大段)
- `quality_scorer.py` (9 维度评分 · QC gate 49k 行)
- `section_generator.py` (Evidence-First 三阶段 · 101k 行)
- `truth_fill.py` (结构化预填 · 47k 行)
- `material_kb.py` (材料解析与 KB 构建 · 54k 行)

### 2.5 旧版归档

`legacy_gradio/` (v15 form_filler + narrative_pipeline + Gradio v7.5 + v9 单机版) **2026-04-29 全栈隔离** (per CLAUDE.md §16 · Block B `739ed7d`):
- import guard 默认 ImportError
- pytest / ruff / coverage / mypy 全排除
- 主线代码不允许 import legacy_gradio

### 2.6 评估

- `evaluation/agent6_report.yaml` baseline yaml 已建
- `unfilled_marker` 0.625 (Phase 2 绿区锚定基线 · per memory `project_runner_phase_a_validated.md`)

---

## 3. Drift Gap (本 sub-PRD · G-10)

### 3.1 G-10 · 工具栏 3 功能接真后端 (KRR: 🟢 Rewrite)

| 维度 | 内容 |
|------|------|
| Original | F-014 工具栏 5 操作 (Word / PDF / 分享 / 版本 / 打印) 全接真后端 |
| Current | Word + 打印通 · **PDF / 分享链接 / 版本时光机 3 功能 mock hook · 不调后端** · F-014 smoke pending |
| KRR | 🟢 **Rewrite** · 工具栏 mock = dead button · 违 bank delivery DoD 体验红线 (用户触碰每一层必须丝滑) · F-014 smoke pending |
| Phase | Phase A end |
| Owner | A4-report |
| Acceptance | `/api/report/export_pdf` + `/api/report/share` + `/api/report/version` 三端点通 + 前端调 + F-014 smoke pass |

### 3.2 衍生 (Phase B-3 · per G-05/G-06 · master PRD §3.1)

- `report_to_credit_handoff.md` schema doc 落 (Phase A · Agent3 sub-PRD §5.1 owner)
- Agent6 → Agent3 真 ReportJSON 串联 (Phase B-3 e2e)
- Agent3 → Agent6 writeback "审批意见" 章节注入 (Phase B-3 双向)

---

## 4. 产品形态详细 (Phase A end MVP)

### 4.1 用户旅程 (客户经理在 RM workbench 调 report tile)

1. 客户经理跳 `/archive/report` workspace
2. 选模板 (面板 · 多版本 docx 模板)
3. 上传企业材料 grid (拖拽 · pdf / docx / xlsx / scanned img · per CLAUDE.md §3.5 row Agent6 · 文件夹异构形态)
4. 一键 `/api/report/v16/fill` (SSE · 阶段事件):
   - **Phase 1 · classifier**: 材料分类 (财报 / 合同 / 资料 / 流水)
   - **Phase 2 · generator**: 段落生成 (Evidence-First 三阶段)
     - 阶段 1: 证据汇集 (`material_kb` 抽事实)
     - 阶段 2: Grounded 写作 (`section_generator` LLM 消费)
     - 阶段 3: 自审 (LLM self-check + citation 校验)
   - **Phase 3 · QC gate**: `quality_scorer` 9 维度评分 (gate · 不进 prompt · 阻断或放行)
5. A4 预览 + FieldChip 3 态 (✅ 已填 · 🟡 部分 · ❌ 未能自动填写)
6. 工具栏 5 操作:
   - **Word 导出**: `/api/report/export_docx` (通)
   - **PDF 导出** (G-10 必接): `/api/report/export_pdf`
   - **分享链接** (G-10 必接): `/api/report/share` 生成只读分享 URL
   - **版本时光机** (G-10 必接): `/api/report/version` 列报告历史版本 + 切换
   - **打印**: 浏览器 print (通)
7. **Phase B-3**: 一键 "送 Agent3 决策" → ReportJSON 真传 → Agent3 90 秒 dashboard

### 4.2 Evidence-First 三阶段细节 (CLAUDE.md §3.3 + 项目核心 IP)

```python
# section_generator.py 三阶段
def evidence_first_generate(section_id, material_kb, industry_card):
    # Phase 1: 证据汇集
    evidence = collect_grounded_evidence(material_kb, section_id)
    # Phase 2: Grounded 生成
    draft = llm_grounded_write(evidence, industry_card, section_template)
    # Phase 3: 自审 (citation + factual check)
    audit = llm_self_audit(draft, evidence)
    if audit.failed_claims:
        return mark_unfilled(audit.failed_claims)  # "未能自动填写"
    return draft
```

**3 层确定性 vs 概率性边界** (per CLAUDE.md §3.1):
- **确定性 (truth_fill 预填)**: 财务比率 / 行业基准 / 字段抽取 → Python
- **概率性 (LLM 消费 prompt)**: 行业意见 / 风险分析 / 话术 → LLM (走 `shared/llm_caller`)
- **QC gate (quality_scorer)**: 9 维度评分 (结果不进 prompt · 只判通过 / 阻断)

### 4.3 LLM caller 迁移 (per CLAUDE.md §3.6)

`agent_report/api.py:_build_llm_caller` 裸 `OpenAI(base_url=...)` → 迁 `LLMCaller(agent_id="report", endpoint="/api/report/v16/fill").chat()` · A4-report 子任务实施 (caller 4)。

### 4.4 QC Blocker (per CLAUDE.md §8)

所有 AI 生成内容输出前终审:
- 企业名占位符 / 数字占位符残留检查
- 证据链完整性 (每条 claim 必须回指证据 ID)
- 财务数字与 `financial_analyzer` 计算结果一致性校验
- 不通过 → 阻断输出 + 显式标 "未能自动填写"

---

## 5. Phase 拆分

### 5.1 Phase A end 必出

- G-10 三端点真接:
  - `/api/report/export_pdf` (PDF 导出 · 走 wkhtmltopdf 或 docx2pdf)
  - `/api/report/share` (生成 read-only share URL · 含 token + 过期)
  - `/api/report/version` (列版本 + 切换 · 后端 store report version history)
- F-014 Playwright smoke pass (5 操作全验)
- LLM caller 迁 `LLMCaller(agent_id="report")` (caller 4 deprecation)
- `report_to_credit_handoff.md` schema doc (G-05 · A6 worker 主轨)

### 5.2 Phase B-3 推延

- G-05 e2e: Agent6 → Agent3 真 SSE handoff (双 worker A4-report + A4-credit 联调)
- G-06 双向: Agent3 → Agent6 writeback 章节注入
- 多模板支持: 不同审批层级 / 不同行业自动模板
- v16 prompt 优化: feedback-driven few-shot (per CLAUDE.md §6 数据飞轮)

---

## 6. 不做 (per CLAUDE.md §4 + master PRD)

- ❌ 决策意见 (是 Agent3 职责 · 报告仅出 ReportJSON + Word)
- ❌ 拓客 / 候选搜索 (Agent1 职责)
- ❌ LLM 现场算财务比率 (CLAUDE.md §3.1 红线 · `financial_analyzer.py` 是确定性层)
- ❌ 不让 LLM 直接判定红线触发 (Agent3 / 客户经理人审职责)
- ❌ 不在前端 inline 大坨 mock (CLAUDE.md 反 §3.5)
- ❌ 不写关键词 / 正则黑名单兜底幻觉 (走 QC blocker + Evidence-First 三阶段 + 自审)
- ❌ 不允许 import legacy_gradio (CLAUDE.md §16 全栈隔离)

---

## 7. 评估锚定 (per master PRD §5.2)

- **Baseline yaml**: `evaluation/agent6_report.yaml`
- **API 版本对齐**: Agent6 **v16** (classifier → generator → QC gate · v16_pipeline.py)
- **通用指标**: `field_completeness` ≥ 95% · `evidence_rate` (每条 claim 必带证据) ≥ 95% · `hallucination_rate` ≤ 3% · `task_completion_rate` ≥ 90%
- **信贷专业**: 财务比率计算正确率 (vs Python ≥ 99%) · `unfilled_marker` 0.625 (Phase 2 绿区基线)

---

## 8. 与 legacy_gradio 关系 (per CLAUDE.md §16)

- **v15 (legacy_gradio/)**: 物理保留 · 全栈隔离 · 仅 emergency demo `ALLOW_LEGACY_GRADIO=1` 解锁
- **v16 (主管线 · 本 sub-PRD)**: 主线 · 持续迭代 · 任何主线代码不允许 import legacy_gradio
- **真删条件**: PM 拍板"v16 真稳了" → 任何 worker 写 PR + Authorized-By trailer → `git rm -rf legacy_gradio/`

---

## 9. 引用

- Tier 1: `docs/contracts/agent-naming-ssot.md` v1.0 + `sse-envelope.md` v1.0 + `llm-prompt-contract.md` v1.0 + `report_to_credit_handoff.md` (G-05 schema 待立 · A6 worker 主轨)
- Tier 1 (RFC): `docs/contracts/rfc/20260418-v16-llm-abstraction-upgrade.md` + `20260418-evaluation-runner.md`
- Tier 2: CLAUDE.md §3.1 (确定性边界) + §3.3 (Evidence-First) + §3.6 (LLM caller 迁) + §3.7 (active rules) + §4 (Agent6 边界) + §6 (数据飞轮) + §8 (QC Blocker) + §16 (legacy_gradio 隔离) + master-2026-04-29.md §3.1 G-10
- Tier 4: `docs/onboarding/A7-prd.md` §1.2 (legacy_gradio 隔离 · 本 sub-PRD §8 衔接)
- 飞书: https://fcntbrvzmfph.feishu.cn/wiki/E9z8wJnDRiaI4ckmeH1cYcQknXc + JY93w1r0aibCeXkSEoLcs8F7nTw (规划版 v2.3)

---

**作者**: worker-A7 · Phase A Week 2-3 · 2026-04-29
**状态**: v1 draft · pending master PRD ratification
