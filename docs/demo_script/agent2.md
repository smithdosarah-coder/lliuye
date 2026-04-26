# Agent2 · 风控规则助手演示脚本（10-15 min Sales Playbook）

**版本**：v1.0
**更新日期**：2026-04-26
**对应 DoD**：L3-12
**目标受众**：策略经理 / 风险经理 / 科技部采购
**演示时长**：10-15 min

---

## 0. 演示前准备（演示者 5 min 自检）

```bash
py /tmp/start_uvicorn.py
curl -s http://127.0.0.1:8000/api/riskctrl/health
cd web && npm run dev    # http://localhost:3000/archive/riskctrl
ls data/mock/agent2-samples/loans.csv    # 7500 行 / 29 列
```

如 LLM 失联 → 切 Mock 模式（fixture KS 0.32 + 通过率 68%）。

---

## 1. 开场（1 min）：业务痛点

> "策略经理建一条新风控规则 · 传统 SAS 流程：诉求 → 数据准备 → 建模 → 回测 → 上线 · 平均 4 周。
>
> Agent2 把这个压到 1 天：
> - 策略经理输入诉求文本 + 上传样本 csv
> - Agent2 生成 DSL 规则 + 回测 KS / PSI / 通过率 · 5 分钟
> - 冠军挑战者 A/B 对比 · 输出推荐方案
>
> 这不替代策略经理 · 是把'手工建模'压到'AI 起手 + 人工审'。"

## 2. Demo 一步一步（8 min）

### Step 1：输入策略诉求（1 min）

打开 `http://localhost:3000/archive/riskctrl`。
- 诉求文本：自然语言 · 例 "识别多头借贷高风险客户 · 目标坏账 ≤ 2% · 通过率 ≥ 65%"
- 上传样本：`loans.csv` 7500 行 + 标签字段（坏账定义 / 业务线）
- 业务线选择：对公 / 普惠 / 对私

> 💬 讲稿："诉求要明确——目标 + 约束 + 边界。Agent2 解析诉求生成 DSL · 不是 chatbot 自由对话。"

### Step 2：触发 DSL 生成（2 min）

点"生成规则"· SSE 5 阶段：
1. `parse_intent` 诉求解析
2. `dsl_synthesize` DSL 规则生成
3. `dsl_validate` 语法 + 字段引用校验
4. `backtest` 跑回测（KS / PSI / 通过率 / 误拒率）
5. `report` 报告聚合

实时进度条 · 真模式 ~3-5 min · Mock 模式 ~3 秒。

> 💬 讲稿："DSL 是给策略经理看的——不是黑盒模型。每条规则都是 IF-THEN-ELSE 可读语句 · 上线前可手工调。"

### Step 3：看 DSL 规则 + 回测指标（2 min）

右侧产出区：
- **DSL 规则集**：树状展示 · 每条规则 IF-THEN-ELSE + 命中率 + 业务含义
- **回测指标**：
  - KS（Kolmogorov-Smirnov）= 0.32（≥ 0.30 良好）
  - PSI（Population Stability Index）= 0.18（< 0.25 稳定）
  - 通过率 = 68% / 误拒率 = 12%
  - 与 scikit-learn 一致率 ≥ 99%
- **混淆矩阵**：TP / FP / TN / FN 可视化

> 💬 讲稿："KS 0.32 是行业及格线 · 0.40+ 优秀。PSI 跑分稳定 · 这套规则上线后 3 个月内不会漂。"

### Step 4：冠军 vs 挑战者 A/B（1.5 min）

- 选当前生产规则集（冠军）vs Agent2 新生成（挑战者）
- 对比 KS / PSI / 通过率 / 误拒率 4 维度
- 推荐方案：保留 / 替换 / 加权融合
- 灰度建议：10% → 30% → 50% → 100% 4 阶段

> 💬 讲稿："不直接替换 · 灰度 30 天再决策。这是金融产品的硬约束。"

### Step 5：导出 + 上线（0.5 min）

- "导出回测报告 PDF" → 含全部指标 + 图表 + 业务解读
- "导出 DSL JSON" → 直接给生产规则引擎部署
- "灰度计划 docx" → 含 4 阶段时间表 + 监控指标

### Step 6：反馈飞轮（1 min）

策略经理灰度后标"误拒高 + 是否调整阈值"→ `/api/feedback` 写 jsonl
- 误拒标注 → 后续 DSL 生成时调整阈值倾向
- 上线决策 → 追加冠军库 · 后续作 baseline

## 3. 合规与监管锚点（1 min）

| 监管 | Agent2 实现 |
|---|---|
| 商业银行互联网贷款管理暂行办法 2025 | 自主风控（核心模型不外包）· Agent2 仅辅助 |
| CAC AI 治理 2.0 | 偏见测试（pending Wave 3+）+ 模型卡 |
| 数据安全法 | 历史样本本地处理 · 不出境 |
| 个保法 | 样本字段脱敏（身份证 hash · 不进 LLM 明文） |

## 4. 典型 Q&A（2 min）

- **Q**：DSL 会不会比 SAS 弱？
  **A**：DSL 表达力覆盖 IF-THEN-ELSE + 算术 / 逻辑 / 时间窗 + 嵌套规则 · 90% 风控场景够用。复杂关联（图谱 / 多跳）当前不支持 · 需走人工补。

- **Q**：KS 跟 sklearn 一致吗？
  **A**：≥ 99% 一致率（数学公式一致 · 浮点误差容忍）· 可现场 import sklearn 跑对比。

- **Q**：上线灰度怎么管？
  **A**：4 阶段 10/30/50/100% · 每阶段 ≥ 7 天 · 监控 KS / 通过率 / 误拒率。Agent2 给灰度计划 · 监控走客户内部系统。

- **Q**：上线工期？
  **A**：Demo 1 周 · POC 2 周（含历史样本接入）· 生产 6-8 周（含灰度）。

## 5. 收尾话术（0.5 min）

> "Agent2 是 X-Nexus 6 Agent 中的'策略侧'。
>
> Agent1 给'谁' · Agent3 给'要不要' · Agent2 给'怎么定标准' · Agent4 给'有没有出问题' · Agent5 给'合不合规' · Agent6 给'报告怎么写'。
>
> 6 个 Agent 闭环 · 信用风险全周期 AI 化。
>
> 下一步：DSL 算法 / Phase 8b 硬化 / POC / 报价？"

---

## 附录 A · Mock 模式

```bash
curl -N "http://127.0.0.1:8000/api/riskctrl/dsl?mock=1&intent=multi_loan_risk"
```

## 附录 B · KS 校验

```bash
py -c "
import pandas as pd
from sklearn.metrics import roc_auc_score
df = pd.read_csv('data/mock/agent2-samples/loans.csv')
print('KS:', ...)
"
```

## 附录 C · 演示失败兜底

- 样本质量差 → 提示数据预处理建议
- DSL 校验失败 → 显示具体错误行 + 建议
- KS < 0.20 → 提示样本特征不足 · 建议补字段
