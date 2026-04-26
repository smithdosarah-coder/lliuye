# Agent3 · 授信决策助手演示脚本（10-15 min Sales Playbook）

**版本**：v1.0
**更新日期**：2026-04-26
**对应 DoD**：L3-12
**目标受众**：审贷员 / 审贷会成员 / 风险经理 / 科技部采购
**演示时长**：10-15 min

---

## 0. 演示前准备（演示者 5 min 自检）

```bash
py /tmp/start_uvicorn.py
curl -s http://127.0.0.1:8000/api/credit/health
cd web && npm run dev    # http://localhost:3000/archive/credit
ls demo_data/agent_credit/    # corp / retail handoff fixture
```

如 LLM 失联 → Mock 模式（preset 决策 fixture）。

---

## 1. 开场（1 min）：业务痛点

> "审贷员一份对公授信决策书 · 平均 2.5 小时手工读材料 + 算财务比率 + 写决策意见。
>
> Agent3 接 Agent6 ReportJSON · 5 分钟出：
> - 四维评分（财务 / 行业 / 经营 / 担保）
> - Top-5 标准拒贷原因码（对标 FCRA AAN）
> - 红线判定（硬红线 / 软告警）
> - 决策意见书 docx（含雷达图 + reason_codes + 红线明细）
>
> 审贷员只做'改 + 签' · 不再'读 + 算 + 写'。"

## 2. Demo 一步一步（8 min）

### Step 1：接 Agent6 handoff（1 min）

打开 `http://localhost:3000/archive/credit`。
- 选业务线：对公 corporate / 普惠 inclusive / 对私 retail
- 点"接 Agent6 handoff" → 自动从 `demo_data/agent_credit/` 拉 EnterpriseProfile fixture
- 一键预填整个表单（来自 Agent6 ReportJSON）

> 💬 讲稿："Agent6 → Agent3 是 X-Nexus 闭环关键点 · EnterpriseProfile schema 双向兼容 · 不复制 PDF · 仅传摘要字段。"

### Step 2：触发四维评分（2 min）

点"开始评分"· SSE 5 阶段：
1. `load_profile` 画像加载
2. `score_financial` 财务维度（确定性走 `financial_analyzer.py`）
3. `score_industry` 行业维度（行业卡片 + 景气度）
4. `score_operational` 经营维度（材料锚定）
5. `score_guarantee` 担保维度（抵质押 + 担保人）

实时进度条 · 真模式 ~2-3 min · Mock 模式 ~3 秒。

> 💬 讲稿："财务维度 100% 走 Python · 不让 LLM 现场算财务比率 · 这是合规红线（CLAUDE.md §3.1）。"

### Step 3：看四维雷达图 + 综合评分（2 min）

右侧产出区：
- **四维雷达图**（RiskRadar · L1-3 Agent3 可视化 · Stage 4 frontend-integration 完成后展示）：
  - 财务（25% 权重）/ 行业（25%）/ 经营（25%）/ 担保（25%）
  - 0-100 分制 · 80+ 优秀 · 60-80 中 · < 60 弱
- **综合评分**：四维加权 + 风险等级（A / B / C / D）
- **决策建议**：批准 / 有条件批准 / 拒绝
- **额度建议**：基于综合评分 + 业务线参数

> 💬 讲稿："四维评分透明化——审贷员看雷达图能 5 秒判断短板。"

### Step 4：Top-5 reason_codes + 红线（2 min）

下方面板：
- **Top-5 决策理由码**（对标 FCRA AAN · 见 `docs/reason_codes/agent3-corporate.yaml` 15 条 + retail 16 条）：
  - 红 / 黄 / 绿 三 severity
  - 每条含 evidence_path（点跳转原材料）+ threshold 阈值 + description 描述
- **红线明细**：硬红线触发清单（如资产负债率 > 70% / 连续亏损 / 黑名单）+ 软告警

> 💬 讲稿："Top-5 reason_codes 是合规底线——客户被拒贷必须给标准化理由 · 这是金管总局 + 监管硬要求。"

### Step 5：导出决策意见书 docx（1 min）

点"导出 docx" → `agent_credit/decision_letter_docx.py` 本地渲染：
- 决策书结构：审批结论 / 额度建议 / 综合评分 / 决策说明 / 批准条件 / Top-5 reason_codes / 红线命中明细 / 额度三估算 / 同业案例参考
- 文件名：`{客户名}_授信决策意见书_{decision_id}.docx`
- 监管底线：本地渲染 · 不走境外 API

> 💬 讲稿："决策书 docx 生成 100% 本地 · python-docx + 中文字体 · 不走境外 LLM 渲染。"

### Step 6：反馈飞轮 + 跨域协同（1 min）

- 审贷员改一条字段（如调低额度）→ `/api/feedback` 写 jsonl
- 触发 Agent5：决策完成后 → 自动合规检查（如新政策对比）
- 触发 Agent4：高风险客户 → 自动加入贷中预警客户池

> 💬 讲稿："Agent3 → Agent5 / Agent4 是贷后管理的起点 · 不是终点。"

## 3. 合规与监管锚点（1 min）

| 监管 | Agent3 实现 |
|---|---|
| 商业银行互联网贷款管理暂行办法 2025 | 自主风控 + 核心模型不外包 + 决策辅助非替代 |
| CAC AI 治理 2.0 | reason_codes 字典 + Evidence-First Protocol + 模型卡 |
| 助贷新规 2025-10 | 合作机构清单 + Agent3 不替代银行实质审批 |
| 金管总局 2025 表态 | copilot 边界 · UI 显式标"建议" |

## 4. 典型 Q&A（2 min）

- **Q**：四维评分透明吗？
  **A**：100% 透明。每维度公式 + 权重 + 输入字段在模型卡 `docs/model_cards/agent3.md` 公开。雷达图 5 秒看短板。

- **Q**：reason_codes 跟 FCRA AAN 怎么对标？
  **A**：FCRA AAN 是国际拒贷理由码标准（美国 1970 年立法）· Agent3 对标其"原因 + 描述 + 改进建议"三段式 · 中文场景适配 · 字典 docs/reason_codes/agent3-{corporate,retail}.yaml 共 31 条。

- **Q**：决策书是否能客户化定制？
  **A**：模板可定制。客户提供 .docx 模板 + 字段映射 → `agent_credit/decision_letter_docx.py` 适配（实施期 1 周内）。

- **Q**：上线工期？
  **A**：Demo 1 周 · POC 2 周（含 EnterpriseProfile 接入）· 生产 4-6 周。

## 5. 收尾话术（0.5 min）

> "Agent3 是 X-Nexus 决策侧。
>
> Agent6 给'材料解读' · Agent3 给'要不要批 + 多少' · Agent5 给'合不合规' · Agent4 给'后续怎么管'。
>
> 一份信用决策从材料到台账 · AI 全周期辅助。
>
> 下一步：四维评分算法 / FCRA AAN 对标细节 / POC / 报价？"

---

## 附录 A · Mock 模式

```bash
curl -N "http://127.0.0.1:8000/api/credit/decision?mock=1&segment=corporate&preset=preset_corp_a"
```

## 附录 B · 决策书 docx 验证

```bash
py -c "
from agent_credit.decision_letter_docx import export
data = export({'subject_name':'测试','decision':'批准',...})
print('docx size:', len(data))
"
```

## 附录 C · 演示失败兜底

- LLM 失联 → Mock 模式 + UI 提示 "fixture 决策 · 真实流程一致"
- 财务字段缺失 → "未能自动评估" + 标注缺什么材料
- 红线触发 → 显式阻断 + 列出具体红线
