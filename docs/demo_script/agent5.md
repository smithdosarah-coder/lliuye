# Agent5 · 合规助手演示脚本（10-15 min Sales Playbook）

**版本**：v1.0
**更新日期**：2026-04-26
**对应 DoD**：L3-12
**目标受众**：合规官 / 内审员 / 科技部采购
**演示时长**：10-15 min

---

## 0. 演示前准备（演示者 5 min 自检）

```bash
py /tmp/start_uvicorn.py
curl -s http://127.0.0.1:8000/api/compliance/health
cd web && npm run dev    # http://localhost:3000/archive/compliance
ls data/mock/agent5-policy/    # 新政策 + 行内业务制度库 fixture
```

如 LLM / Tavily 失联 → Mock 模式（fixture 政策 + 冲突点预置）。

---

## 1. 开场（1 min）：业务痛点

> "监管发一条新政策 · 合规官手工 cross check 行内业务制度 · 100+ 制度文件 · 1 周。
>
> 漏一条冲突点 = 监管罚款（百万至千万）+ 业务暂停。
>
> Agent5 把这个压到 24 小时：
> - 政策事件驱动（vs 定期巡检）· 监管发新政 → 自动抓
> - LLM 解析政策条款 · 与行内业务制度库 cross check
> - 红 / 黄 / 绿 冲突点分级 + 整改建议
>
> 这不替代合规官 · 是把'手工 cross check'压到'AI 起手 + 合规官审'。"

## 2. Demo 一步一步（8 min）

### Step 1：政策事件触发（1 min）

打开 `http://localhost:3000/archive/compliance`。
- 演示场景：模拟金管总局发新政策（如 2025-10 助贷新规）
- 触发：政策事件驱动（点击"模拟新政策"或真实订阅 SearchProvider 抓 gov_cn / pbc_gov / flk_npc 公开发布）
- 政策原文展示：标题 / 发布机关 / 关键条款 / 生效日期

> 💬 讲稿："政策事件驱动是 Agent5 核心——不是定期巡检 · 是监管一发布就触发。"

### Step 2：LLM 解析政策条款（1.5 min）

点"开始解析"· SSE 5 阶段：
1. `fetch_policy` 政策原文抓取
2. `parse_clauses` 条款拆解（LLM）
3. `load_internal` 行内业务制度库加载（SOP / 准入 / KYC / 风偏 / 审查清单 5 类）
4. `cross_check` 矩阵 cross check
5. `classify_conflict` 冲突点分级（红 / 黄 / 绿）

实时进度条 · 真模式 ~5-8 min · Mock 模式 ~3 秒。

> 💬 讲稿："LLM 解析政策条款的准确率目标 ≥ 95% · 配人工标注校 · 不臆造监管条文。"

### Step 3：看冲突点矩阵（2 min）

右侧产出区：
- **政策矩阵**（左右对照）：
  - 左：政策条款（监管原文 + 解析摘要）
  - 右：行内业务制度（SOP 章节 + 现行做法）
  - 中间：冲突点高亮 + severity（红 / 黄 / 绿）
- **冲突点明细**：
  - 红色（硬违规 · 立即停）：5 类（央行新规 / CAC AI 治理 / 行业自律 / 准入 / KYC）
  - 黄色（流程缺陷 · 整改）：3 类（风偏 / 审查清单 / 流程盲区）
  - 绿色（合规通过）
- **每条冲突**：reference_policy（政策条款序号）+ description（冲突描述）+ suggested_action（整改步骤）

> 💬 讲稿："每条冲突点的 reference_policy 字段必填——监管引用具体到文件名 + 条款序号 · 不臆造。"

### Step 4：整改建议 + 上报（1.5 min）

- **整改建议**：基于 `docs/reason_codes/agent5_compliance.yaml` 8 条字典
  - 红色：暂停业务 + 修订 SOP + 报告合规委员会
  - 黄色：流程整改 + 内部审计 follow-up
- **审议路径**：合规委员会 → 董事会 → 监管报告（视严重度）
- **整改时限**：红 24h / 黄 5 工作日

### Step 5：导出合规检查报告（1 min）

点"导出 docx"→ 本地 python-docx 渲染：
- 报告结构：政策摘要 / 冲突点清单 / 整改建议 / 审议路径 / 时间表
- 附录：政策原文链接 + 行内 SOP 章节双向 ref
- 文件名：`{政策名}_合规检查报告_{date}.docx`

### Step 6：跨域协同 + 反馈飞轮（1 min）

- 整改建议 → 触发 Agent3 重新评估高风险授信（如准入新规收紧）
- 整改建议 → 触发 Agent4 加强贷中预警（如新政对应监控字段）
- 反馈飞轮：合规官标"误报 / 误识别"→ `/api/feedback` 写 jsonl · 后续解析调权重

## 3. 合规与监管锚点（1 min）

| 监管 | Agent5 实现 |
|---|---|
| 金管总局《助贷新规》2025-10 | 政策事件触发 + 合作机构清单 cross check |
| CAC《AI 安全治理框架 2.0》| 可解释性 + reason_codes 字典 + 模型卡 |
| 数据安全法 + 个保法 | 政策原文 + 行内 SOP 本地处理 · 仅检索词出境 |
| 生成式 AI 服务管理办法 | 训练数据合法性 + 内容标识 |
| 行业自律 | 互联网金融协会 / 银行业协会 自律公约 cross check |

## 4. 典型 Q&A（2 min）

- **Q**：政策解析准确率多少？
  **A**：目标 ≥ 95%（vs 人工标注）。当前 baseline 待 Wave 3+ 真政策接入校。LLM 解析对长文本敏感 · 配人工 review。

- **Q**：行内 SOP 出境吗？
  **A**：不出境。所有政策原文 + 行内业务制度库本地处理。仅政策抓取关键词（公开监管文件）经境内 SearchProvider endpoint。

- **Q**：跨地域监管差异怎么办？
  **A**：不同省份金融监管口径细微差异 · 需客户合规部协同审。Agent5 提供 baseline 解析 · 终审走客户合规部 + 监管局沟通。

- **Q**：上线工期？
  **A**：Demo 1 周 · POC 3 周（含行内业务制度库接入）· 生产 6-8 周（含信创适配 + 监管订阅 + 客户合规部对接）。

## 5. 收尾话术（0.5 min）

> "Agent5 是 X-Nexus 合规侧。
>
> Agent3/4 决策 + 预警 → Agent5 合规检查 = 业务流程合规闭环。
>
> 监管一发新政 · Agent5 24 小时给冲突点清单 + 整改建议。漏报风险下降 · 合规官效能上升。
>
> 下一步：政策事件驱动算法 / FCRA AAN reason_codes 对标 / POC / 报价？"

---

## 附录 A · Mock 模式

```bash
curl -N "http://127.0.0.1:8000/api/compliance/check?mock=1&policy=preset_helping_loan_2025_10"
```

## 附录 B · 政策订阅

```bash
# Agent5 自动监控（gov_cn / pbc_gov / flk_npc 公开 endpoint）
py -m agent_compliance.policy_watcher --interval=daily
```

## 附录 C · 演示失败兜底

- 政策抓取失败 → Mock fixture（预置 helping_loan_2025_10）
- LLM 解析失败 → 显示具体段落 + 建议（不臆造）
- 跨条款关联识别低 → 提示"请人工补"
