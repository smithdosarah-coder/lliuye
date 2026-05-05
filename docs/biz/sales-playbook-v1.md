# 销售剧本 v1.0 · 信贷 6 Agent 矩阵

> **版本**: v1.0 · 2026-05-04 · worker-B2-biz (Phase B Sprint 2 · BE11 doc-only)
> **性质**: 销售内训 doc · 客户对接话术参考 · **不是** 直接发客户的对外材料
> **审稿对象**: 销售 lead / 主 CLI / PM
> **下游**: 配合 `pricing-assumptions.md` 报价 + `trial-flow-assumptions.md` 阶段动作 + `multi-tenant-assumptions.md` 数据隔离答疑

---

## 0. 痛点根本 (per `BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` §1 · Codex R2 verbatim)

> **银行用户不敢信 · 不敢签 · 不敢追责**

后端真痛不是"缺 ML / embedding / batch analytics" — 这些都是手段。真痛是 4 角色对 AI 输出的**信任 + 可复核 + 可追责**。

销售对外**禁止**说:
- ❌ "我们 AI 准确率 90%+" (没真实生产 baseline)
- ❌ "替代审贷员 / 替代客户经理" (per 金管总局 2025 "AI 现阶段只能辅助, 不能替代" · DoD §0 证据 3)
- ❌ "比 XX 友商便宜 50%" (低价签下来后维护吃亏 · 友商也会跟降)
- ❌ "30 天部署上线" (Pilot 1.5-2 月 · Pro 私有化 ≥ 3 月)
- ❌ "全自动化" (copilot-only · 监管硬规)

销售对外**主打**:
- ✅ "每条 AI 结论可追到原始材料 · 30 秒内回查" (per DoD L2-1 evidence_rate ≥ 0.95 · BE7 decision ledger)
- ✅ "出错谁负责 · 我们提供完整 audit chain" (per `shared/decision_ledger/` jurisdiction + retention)
- ✅ "审贷员可改 · 改的内容回流优化模型 · 客户数据不离场" (per CLAUDE.md §6 数据飞轮 + §3.5 mock 边界)
- ✅ "财务比率 / 红线判定走 Python 确定性计算 · LLM 不现场算" (per CLAUDE.md §3.1 治本路径)

---

## 1. 4 角色 × 6 Agent 价值话术矩阵

per `auth_service/rbac.py:9-15` ACCESS · 4 + 1 角色对应 6 Agent。

### 1.1 客户经理 (RM · `role=rm`) → Agent1 + Agent6 + Agent3 + Agent4 + Agent5 + Agent2

**痛点**:
1. 找客户难: 名单总是同事剩下的 · 没有 look-alike (per BE1 痛 1.1.2)
2. 报告写得久: 4 小时 / 件 · 200 RM × 30 件 / 月 = 巨量人时浪费 (per `pricing-assumptions.md` §3.3 ROI 模型)
3. 推荐产品不准: 凭经验匹配 · 漏推率高
4. 客户事件感知慢: 出事看新闻才知道

**话术** (按场景):

> "您 RM 团队最大的瓶颈是不是**找客户 + 写报告**两件事吃掉一半工时? 我们 Agent1 用您行已成交客户库做 look-alike · 每个候选都给您 4 维度证据 (行业 / 区域 / 规模 / 相似度) · RM 决策完后我们追踪转化 · 6 个月内您能看到 RM 找客户命中率提升的曲线。"

> "Agent6 是按章节生成 · 每条数字都挂证据链 (出处 / 段落 / URL) · 您 RM 写一份报告 4 小时 · Agent6 帮您填 70% · 您审核 30% · 单件耗时降到 1 小时多。我们做过 ROI 模型 (`pricing-assumptions.md` §3.3): 200 RM 一年节省 ~1800 万人力成本。"

**异议**:
- "AI 写出来的报告我看不懂能不能改?" → 可以改 · audit modify 端点回流 · 您改的会变成 few-shot 优化我们 Agent (per CLAUDE.md §6) · 您 RM 是模型的训练师之一
- "如果 AI 找的候选不准怎么办?" → 我们的"准"是基于您行已成交客户的内源 KB · 不是外面的通用模型 · 不准就是您 KB 数据问题 · 我们一起补

### 1.2 审贷员 (credit_officer · `role=credit_officer`) → Agent3 + Agent6 + Agent4

**痛点**:
1. AI 评分黑盒: 不敢签 · 出错追不到 (per BE2 痛 1.2.1)
2. 缺同业对标: 单个客户的指标好不好不知道 (per BE2 peer_gap)
3. 报告章节不一致: 章 A 说企业增长 · 章 B 说有风险 · 没人发现 (per BE3 cross-section coherence)
4. 缺材料没人提: 等审贷会发现才知道缺材料 (per BE3 material gap graph)

**话术**:

> "您审贷最怕什么? 是 AI 给的分数没法解释 · 您签了字出问题谁担? Agent3 的每个分数都挂决策图: feature snapshot / rule hit / 阈值 / 来源段落 / 版本号 (per BE2 decision_graph) · 您能 30 秒内看到为什么是这个分。我们还有同业对标 (peer_gap): 这家企业的资产负债率 65% · 同行业中位 58% · 高出 7 个百分点 · 您一眼判别不正常。"

> "Agent6 已经把材料缺口 + 章节一致性都查过了 · 您拿到的报告右上角会显示 '本案缺 2024 年审计报告 · 影响 6.1 财务分析章节 · 影响评分 -8 分' (per BE3 material gap graph) · 您不用等审贷会才发现。"

**异议**:
- "AI 评分跟我经验冲突时听谁的?" → **听您的** · per 金管总局 "AI 现阶段只能辅助" · 我们的输出标"建议" · 您 final 签字 · 您改的进 audit log · 给您行的合规部留底
- "出问题怎么追?" → BE7 decision ledger (per CLAUDE.md §3.7.5) · 每个决策含 input_hash / output_hash / evidence_chain / reviewer_id · jurisdiction = '银' · retention = 5 年 (银保监 archive)

### 1.3 合规官 (compliance_officer · `role=compliance_officer`) → Agent5 + Agent6 + Agent4

**痛点**:
1. 政策版本管理乱: 新政策出 · 谁知道哪条业务规则受影响 (per BE4 痛 1.3.1)
2. 冲突解释不敢签: AI 判某条业务规则违规 · 但不给业务原文 + 条款原文 + 置信度 (per BE4 痛 1.3.2)
3. 处罚案例分析停在表面: 没结构化 reason (per Agent5 现状)

**话术**:

> "您合规部最痛的是新政策出来后没人能快速排查业务制度库哪些规则受影响。Agent5 是政策事件驱动 (per CLAUDE.md §4): 监管发布新政策 → Agent 自动对您行业务制度库扫一遍 → 出违规冲突点明细清单 · 每条含 `冲突字段 / 业务原文 / 条款原文 / 置信度 / 复核原因` (per BE4 violation reason schema) · 您直接派给业务部整改。"

> "我们对 Agent5 的输出有硬约束: 没证据的判断标'未能自动判定' · 不让 LLM 现场编 (per CLAUDE.md §3.1 + §12) · 您拿到的清单不会有'可能 / 大概'兜底 · 全是签字级证据。"

**异议**:
- "你们用的 LLM 数据出境合规吗?" → 全境内 · DeepSeek (杭州深度求索) 主路由 + 阿里 DashScope 备 (per CLAUDE.md §3.7.3 PIPL fallback chain) · 跨境 Moonshot 仅显式 opt-in · audit log 含 region 字段可追溯
- "Agent5 漏判了某条违规怎么办?" → Agent5 是 copilot · 不替您背锅 · 您合规部审核后签字 · 漏判风险您行内审一直都有 · Agent5 是把您从 100 条降到 5 条要审核的 · 复盘漏判进我们 baseline 评估 (per CLAUDE.md §6)

### 1.4 风险经理 (risk_manager · `role=risk_manager`) → Agent2 + Agent4 + Agent3

**痛点**:
1. DSL 写完不知道好不好: KS / AUC 业务方看不懂 (per BE6 痛 1.4.1)
2. KS 0.4 这个数字客户经理看不懂 → 转通过率 / 坏账率
3. 跨客户模式发现难: 100 个客户一起出问题没人能发现 (per BE9)
4. Agent4 缺 key 回 mock: 信号不可信 (per BE5 痛)

**话术**:

> "您写 DSL 规则上线前最大的不确定是: KS 0.42 这个数字到底好还是不好? Agent2 给您双轨指标: KS / AUC 给统计口径 + **通过率 / 坏账率 / 利润影响** 给业务口径 (per BE6 业务指标双轨) · 您给行长汇报时说 '这条规则上线后通过率从 65% 降到 58% · 坏账率从 3.2% 降到 1.8% · 月利润影响 +120 万' · 业务方一听就懂。"

> "Agent4 我们已经把 freshness / source confidence / fallback banner / scan replay 都接好了 (per BE5) · 您能看到每条信号的'多新 / 哪来 / 多置信' · 缺 key 回 mock 的告警会显式 banner 提示 · 不会让您拿一份'看上去很真但是 mock'的预警去签字。"

**异议**:
- "我们已经有同盾 / 百融 / 拓尔思" → 并行不冲突 · 友商擅长信用模型 / 反欺诈底层 · 我们擅长**可解释 + 可追责** · 您审贷会签字时的"为什么 + 凭什么"是我们 fill 的空白
- "KS 提升不到 5 个点不值得部署" → Pilot 6 月不评 KS · 评 ROI 模型 (per `pricing-assumptions.md` §3.3) + 节省人时 + 减少误判损失 · 这些组合起来年化 6-9x ROI

### 1.5 admin (`role=admin`) → 全 6 Agent

仅平台管理员 · 客户侧不演示 (我方运维 + 客户 IT 部技术对接人用)。

---

## 2. ROI 模型详细 (per `pricing-assumptions.md` §3.3 + DoD §0 证据 1)

### 2.1 Agent6 报告 ROI (主打 RM / 业务部)

| 假设变量 (客户填) | 默认锚 (壹账通) | 我方保守值 |
|---|---|---|
| RM 人数 | 200 | 200 |
| 单 RM 月报告产出 | 30 | 30 |
| 单报告平均人工耗时 (小时) | 4 | 4 |
| 自动化率 | 80% (壹账通公布) | 70% (我方保守) |
| 单 RM 月成本 (含五险一金) | 1.5 万 | 1.5 万 |

**计算**:
- 释放人时 / 月 = 200 × 30 × 4 × 70% = **16800 小时**
- 等价 RM 人数 = 16800 ÷ (22 工作日 × 8h) = **95 RM 月产能**
- 月节省人力成本 = 95 × 1.5 = **142 万 / 月**
- 年化节省 = **1700 万 / 年**

→ Pro 档 200-300 万 / 年 vs 1700 万节省 → **ROI 5.6-8.5x**

### 2.2 Agent3 授信 ROI (主打 credit_officer / 风控部)

| 假设变量 | 默认锚 (同盾诸葛) | 我方保守值 |
|---|---|---|
| 年放贷件量 | 10000 | 10000 |
| 单件人工审贷耗时 (小时) | 2 | 2 |
| 误判率 (无 AI) | 5% | 5% |
| 单笔误判平均损失 (万) | 50 | 50 |
| 误判降幅 | 45% (同盾) / 72% (同盾内审) | 30% (保守) |

**计算**:
- 误判减少件数 = 10000 × 5% × 30% = **150 件 / 年**
- 年节省坏账 = 150 × 50 = **7500 万 / 年**
- 审贷耗时不计 (人工耗时减少另算)

→ Enterprise 档 500-800 万 / 年 vs 7500 万节省 → **ROI 9-15x**

### 2.3 Agent5 合规 ROI (主打 compliance_officer)

| 假设变量 | 锚 | 备注 |
|---|---|---|
| 监管处罚单笔均值 (百万) | 200-1000 | 数据安全法 / 个保法 上年度营业额 5% |
| 年遭遇罚款概率 (无 AI) | 1% | 行业平均 |
| Agent5 减少违规检出率 | 80% | 我方保守值 |

**计算**:
- 期望罚款 (无 AI) = 200 万 × 1% = **2 万 / 年** (单事件) → 但 1 起罚款 = 200 万直接 + 暂停业务资质 (per DoD §0 证据 3)
- Agent5 价值 ≠ 期望罚款节省 · 价值在**避险确定性** · 一次罚款抵 5 年 Agent5 投入

→ 不算精确 ROI · 改打 "**1 次罚款 = 5 年 Agent5 投入**" 的避险话术

### 2.4 Agent2 风控 ROI (主打 risk_manager)

| 假设变量 | 锚 | 我方保守值 |
|---|---|---|
| 年放贷规模 (亿) | 100 | 100 |
| 当前坏账率 | 3% | 3% |
| Agent2 + Agent4 联动后坏账率 | 2.2% | 2.5% (保守) |

**计算**:
- 坏账减少 = 100 × (3% - 2.5%) = **5000 万 / 年**

→ 此模型客户更敏感 · 因为坏账直接进损益表

### 2.5 ROI 话术模板 (拼装)

> "您行规模 (RM 数 / 放贷量 / 审贷件量) 我们填进 ROI 模型 (`docs/biz/pricing-assumptions.md` §3.3) · 出年化节省 X 万 / 年。我们 Pro 档 Y 万 / 年 · ROI Z 倍。Pilot 期 6 月跑出真实数据 · ROI 从模型变成实际 · 续 Pro 续 Enterprise 都看实际。"

> "我们不打"准确率提升 X%"这种空话 · 业务方听不懂。我们打**节省人时 + 减少坏账 + 避免罚款**三件事 · 都有具体数字 + 评估 baseline 月报追踪 (per `evaluation/README.md`)。"

---

## 3. 客户异议 FAQ

### 3.1 关于价格

**Q: Pilot 30-80 万贵了**
A: Pilot 是 6 月期 · 单分行 · 单业务线 · 折合月 5-13 万 · 我们工程师 + 答疑 + 月度 baseline + ROI 模型 + Slack 群 全包。低于 30 万我们不做 · 维护成本不够 · 您也得不到响应。

**Q: Pro 200 万 vs 友商 100 万**
A: 友商 100 万通常是单 Agent (e.g. 仅信用评分) + 共享 SaaS + 5×8 SLA。我们 200 万是 3-6 Agent 自选 + 物理隔离 + 7×24/4h SLA + decision ledger 全审计 + few-shot 客户私有 (per `multi-tenant-assumptions.md` §3 Pro 档)。您比的不是同档位。

**Q: 能不能买断**
A: Enterprise 档 500-1500 万一次性 license + 18-22% 年维护 (per `pricing-assumptions.md` §3.2 业内常规) · 等同拓尔思 / 壹账通模式。Pro 档不卖买断 · 因为我们要持续优化 prompt + few-shot · 买断 = 您拿到代码不优化 = 6 月后过期。

### 3.2 关于数据安全

**Q: 我们的数据会不会被你们拿去训其他客户?**
A: **不会**。Pilot 期共享 baseline (per `multi-tenant-assumptions.md` §2.8 Phase B 现状) · Pro 起客户 few-shot 完全私有 · `data/tenants/<您行 slug>/few_shots/` 隔离 · prompts.py 不嵌入您的数据 · runtime lookup。Enterprise 档训练数据完全本地不离场。

**Q: LLM 调用会不会泄漏到境外?**
A: 全境内。`shared/llm_caller/retry.py:DEFAULT_FALLBACK_CHAIN = ("deepseek", "dashscope")` (per CLAUDE.md §3.7.3) · 都是境内 provider · 海外 Moonshot 仅 opt-in · audit log 含 `region` 字段可追溯 · PIPL 跨境合规底线。

**Q: 我们解约后数据怎么处理?**
A: 30 日内您可申请数据导出 (Excel + jsonl 包) · 解约后按 retention class 倒计时 (per `multi-tenant-assumptions.md` §5.2): 候选 / 预警 (short) 90 日 · 授信 / 合规 (standard) 5 年 · 报告 (long) 10 年 (银保监 archive 强制 · 不能随意删)。

### 3.3 关于合规

**Q: AI 给的决策出错谁负责?**
A: 您。我们是 copilot · 您 final 签字 (per 金管总局 2025 "AI 现阶段只能辅助")。但我们提供完整 audit chain: BE7 decision ledger 含 `decision_id / input_hash / output_hash / evidence_chain / reviewer_id / reviewer_ts` (per CLAUDE.md §3.7.5) · 您出问题能 30 秒内回到原始材料 · 内审 / 监管来查您拿得出。

**Q: 算法可解释性合规吗?**
A: 合规。CAC 《AI 安全治理框架 2.0》强制可解释 · 我们 BE2 decision_graph (per `agent_credit/decision_graph.py`) 每个分数挂 feature/rule/threshold/source · BE4 violation reason schema 每条违规给冲突字段 + 原文 + 置信度。reason_codes 字典固定可枚举 (per DoD L2-7) · 对标 Zest / Upstart AAN。

**Q: 等保 / 信创?**
A: Enterprise 档支持私有化 + 信创兼容 (per DoD L4-2) · 鲲鹏 / 麒麟 / 曙光路径有规划文档 · 实跑要看您行环境一案一议。Pilot / Pro 不强制信创。

### 3.4 关于功能

**Q: 你们有同盾 / 百融的功能吗?**
A: **没有**。我们不做信用模型 / 反欺诈底层 / 970+ 区域银行覆盖 · 这些是友商的 sweet spot。我们做**审贷员 / 合规官 / RM 的工作流 + 决策可追责** · 与友商互补不冲突。Agent2 风控 DSL 是上层规则配置 + 业务指标双轨 · 不是替代您的信用评分模型。

**Q: 没有大模型微调 (SFT) 怎么做行业适配?**
A: 提示词 + few-shot 注入 (per CLAUDE.md §6 数据飞轮)。SFT 适合大厂训通用模型 · 我们做单银行 SaaS · 客户 feedback → 提取 few-shot → 注入 prompt · 同样适配。Phase C 真客户量上来后可考虑 LoRA · 现在不做。

**Q: 模型卡片?**
A: 每 Agent 有 model card (per DoD L3-11) `docs/model_cards/<agent>.md` · 含算法 / 输入 / 输出 / 准确率 / 局限。Pilot 期月度跑 baseline 落 `evaluation/baselines/pilot/<您行>_YYYY-MM.json` · 您能看到每月趋势。

### 3.5 关于交付节奏

**Q: 多久能上线?**
A: Pilot SaaS: 1-2 周 onboarding (创 tenant + import 数据 + 跑 baseline · per `trial-flow-assumptions.md` §3.4 M1)。Pro 私有化: 6-8 周 (含信创适配)。Enterprise: 12-16 周 (含信创 + 私有 LLM 部署 + 培训)。

**Q: 我们 IT 部要投入多少人?**
A: Pilot: 1 个技术对接人 ≤ 0.2 人月 (just for 数据 import / 网络白名单)。Pro: 1-2 个 + 我方驻场 1 周 (onboarding) · 之后 0.3 人月 / 月。Enterprise: 客户 PMO + IT 团队 ≥ 3 人 driver-side · 我方驻场 2 周。

---

## 4. 竞品对标 (per `pricing-assumptions.md` §1)

### 4.1 金融壹账通 Smart Lender / Gamma

**他们强**:
- Smart Lender 报告自动化率 80% (业内最高)
- Gamma 国有大行 100% 渗透
- 平安系背景 · 银行采购信任度高

**我们差异**:
- 我们打**可解释 + 可追责** · 他们打**端到端自动化**
- 我们 Pro 档 200-500 万 vs 他们 Smart Lender 通常 ≥ 1000 万 (头部银行打包)
- 我们城商 / 农商 sweet spot · 他们国有大行 sweet spot

**对位话术**: "壹账通做的是大体量自动化 · 我们做的是您审贷员能签字的可追责。如果您是城商 / 农商 / 区域行 · 您要的不是 100% 自动化 · 是 70% 自动化 + 30% 您能签字的解释。"

### 4.2 同盾科技 (诸葛金融大模型)

**他们强**:
- 风险识别 78%→94% / 误报 -45% / 人工误判 -72% (公开数据)
- 反欺诈 / 信用模型业内 top
- 950+ 客户 (含中大型行)

**我们差异**:
- 同盾做底层模型 · 我们做工作流
- 我们 Agent2 + Agent4 是规则上层 + 信号融合 · 不替代同盾的信用评分

**对位话术**: "同盾擅长信用 + 反欺诈底层模型 · 我们 Agent2 是您行 risk_manager 写 DSL 规则的工具 · 我们 Agent4 把同盾 / 内部多源信号融合给您。我们与同盾互补 · 不竞争。"

### 4.3 百融云创 (CybotStar)

**他们强**:
- 950+ 区域银行覆盖 · 农商 / 城商 sweet spot
- per-call 模式成熟 · 单价低
- 成立 13 年 · 客户基础厚

**我们差异**:
- 百融以信号 / 信用查询为主 · 我们以 RM / 审贷工作流为主
- 我们 Agent1 look-alike 是基于客户内源 KB · 百融是基于全市场信号

**对位话术**: "百融适合您查询客户征信 / 黑名单 · 我们 Agent1 是基于您行已成交客户库做 look-alike · 您 RM 用得更顺手。"

### 4.4 拓尔思 (拓天大模型)

**他们强**:
- 单笔成交 ~2000 万 (顶价锚)
- 国资背景 · 信创第一梯队
- 已签多家国有大行

**我们差异**:
- 拓尔思是大模型 + 知识图谱通用 · 我们是信贷垂直
- 我们 Pro 档 200-500 万 · 拓尔思 800-2000 万

**对位话术**: "拓尔思一笔 2000 万是国有大行通用平台 · 您城商 / 农商 / 单业务线不需要那么大体量。我们 Pro 档 200-500 万是您单业务线就能起的 ROI 5-9x。"

### 4.5 国外锚 (FICO / Moody's CreditLens)

不主打。客户问到时:
> "FICO / Moody's 在国内主要做评分模型 license · 不做工作流。我们做审贷员 / RM / 合规官的工作流 · 是不同的 layer。"

---

## 5. 演示 demo 流程 (per `trial-flow-assumptions.md` §2 POC)

### 5.1 90 分钟现场演示节奏

| 时间 | 内容 | 目的 |
|---|---|---|
| 0-10' | 客户介绍 + 我方介绍 + 议程对齐 | 暖场 + 设期望 |
| 10-25' | 痛点对齐 (per §0 4 角色) · 不演示 · 让客户讲 | 找客户业务真痛 |
| 25-45' | Agent1 + Agent6 演示 (RM 视角) | 主打 ROI 高 |
| 45-65' | Agent3 + Agent5 演示 (审贷 / 合规视角) | 主打 evidence-first + 可追责 |
| 65-75' | Agent4 + Agent2 演示 (风险经理视角) | 选讲 · 看客户 risk_manager 是否在场 |
| 75-85' | 答 5 方异议 (per §3 FAQ) | 业务 + 科技 + 合规 同时在场 |
| 85-90' | 议程总结 + Pilot 邀约 | 不报价 · 仅邀进 POC |

### 5.2 现场必带 (per `trial-flow-assumptions.md` §2.4 D4)

- 笔记本预热 demo.liuye.me 5 个场景 (per DoD L1-1 ≥ 2 场景 / Agent · 我方备 5)
- 备用 mock 模式 (断网可演示 · per L1-10)
- ROI 模型 Excel (现场填客户参数算节省)
- 4 个 ppt 视图: 痛点对齐 / 6 Agent 一图 / 可追责架构 (BE7) / 数据飞轮
- 不带: 报价单 / 合同 / 法务条款

### 5.3 现场禁动作

- ❌ 报价 (引导到 Pilot 邀约 · 报价书走法务 + 销售 lead 后发)
- ❌ 承诺 SLA / 准确率
- ❌ 拿客户业务部 / 风控部之间的矛盾点开玩笑
- ❌ 跟友商比价格 (维度不同 · 转可追责)

---

## 6. 销售漏斗预测 (per `trial-flow-assumptions.md` §1)

| 阶段 | 转化率 (假设) | 周期 |
|---|---|---|
| Lead → POC | 30% | 1-2 周 |
| POC → Pilot | 30% (per `trial-flow-assumptions.md` §7 T9 假设 · 待销售验证) | 1-2 周决策 |
| Pilot → Pro | 70% (per `trial-flow-assumptions.md` §7 T6 假设) | 6 月 Pilot 期 |
| Pro → Enterprise | 20% | 1-3 年 |

**100 lead 漏斗**:
- 100 → 30 POC → 9 Pilot → 6 Pro → 1 Enterprise
- 9 Pilot × 50 万 + 6 Pro × 300 万 + 1 Enterprise × 1000 万 = **3250 万 / 年化**
- 假设 lead 获取成本 5 万 / 100 = 5 万 / 年 → 净利率 > 90%

> ⚠️ 漏斗数字全部是**假设**。Phase B 销售实战 5 家 lead 后回写真实数据 (per `trial-flow-assumptions.md` §7 假设 T9)。

---

## 7. 准入清单 (销售收 lead 时硬过)

**接入条件 (3 项 AND)**:
- 客户业务部主任 + 科技部分管 leader 同时表态意向
- 客户提供 1 业务线 sample 数据 (脱敏)
- 客户预算 ≥ 30 万 (Pilot 底价线)

**不接入 (任一)**:
- 客户仅采购部接洽 (业务方不在场 = 决策不闭环)
- 客户预算 < 30 万 (打不进 Pilot 档 · 不如不做)
- 客户已签拓尔思 / 壹账通的全 6 Agent 等价竞品 (我方差异化打不过)
- 客户要求 30 天上线 (期望管理失败 · 不如不接)
- 客户对 LLM 数据出境零容忍但要 Claude / OpenAI (我们境内强制 · 客户技术口径不一致)

---

## 8. 销售内训速记卡 (1 页)

**6 Agent 一句话**:
- Agent1 获客: 您内源 KB look-alike + 4 维度证据 · 给 RM 用
- Agent2 风控: DSL 上线 + KS / 通过率双轨 + 利润影响 · 给 risk_manager 用
- Agent3 授信: decision_graph + peer_gap · 给 credit_officer 用
- Agent4 预警: 客户行为变化触发 + freshness / source / replay · 给 risk_manager + RM 用
- Agent5 合规: 政策事件触发 + violation reason schema · 给 compliance_officer 用
- Agent6 报告: classifier→generator→QC + Evidence-First + cross-section coherence · 给 RM 用 (Agent3 下游)

**4 角色一句话痛点**:
- RM: 找客户难 + 报告写得久
- credit_officer: AI 评分黑盒 + 缺同业对标 + 缺材料没人提
- compliance_officer: 政策版本管理乱 + 冲突解释不敢签
- risk_manager: DSL 写完不知道好不好 + KS 业务方看不懂

**5 方决策**:
业务 (要 ROI) · 科技 (要部署) · 合规 (要可解释) · 数据 (要不出境) · 采购 (要砍价)

**3 档定价**:
Pilot 30-80 万 / 6 月 · Pro 150-500 万 / 年 · Enterprise 500-2000 万 / 年

**1 个根本痛**:
银行用户不敢信 · 不敢签 · 不敢追责。我们卖**可信 + 可签 + 可追责** · 不是卖准确率。

---

## 9. 假设清单

| # | 假设 | 验证方式 | 风险 |
|---|---|---|---|
| S1 | 4 角色话术匹配真实客户决策结构 | 销售实战 + 客户访谈 5 家 | 中 |
| S2 | ROI 模型保守值客户认可 | 真实 Pilot 客户回测 | 中 |
| S3 | "可追责"卖点击中 5 方中 ≥ 3 方 | 客户走访 · 5 方异议 FAQ 命中率 | 中 |
| S4 | 城商 / 农商是 sweet spot · 不打国有大行 | 销售漏斗 6 月真实数据 | 中 |
| S5 | 现场 90 分钟 demo 节奏可成 | 实战 3 家以上 | 中 |
| S6 | 100 lead → 1 Enterprise 转化 (per §6) | 销售实战 100 lead | **高** · 无基线 |
| S7 | 客户接受境内 LLM (DeepSeek / DashScope) | 法务 + 数据管理部访谈 | 低 |
| S8 | 异议 FAQ 命中率 ≥ 70% | 5 家客户访谈复盘 | 中 |
| S9 | Pilot → Pro 续签率 70% | 6 月后真实数据 | 中 |
| S10 | 友商对位话术 (§4) 不被销售当场打脸 | 内训演练 + 销售 sandbag | 中 |

---

## 10. 与其他 doc 的对接

- `pricing-assumptions.md` §1: 市场锚点 → 本 doc §4 竞品对标
- `pricing-assumptions.md` §3.3: ROI 模型 → 本 doc §2 ROI 详细
- `pricing-assumptions.md` §4: 5 方采购 → 本 doc §0 + §1 4 角色 + §3 异议 FAQ
- `multi-tenant-assumptions.md` §3 + §5: 数据隔离 + PIPL → 本 doc §3.2 异议 FAQ
- `trial-flow-assumptions.md` §2 + §3: POC + Pilot 阶段 → 本 doc §5 演示 + §7 准入
- `docs/scorecard/definition-of-done.md` L1-L4: → 本 doc §5 演示 + §3 异议
- `BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` §1: 痛点根本 verbatim → 本 doc §0 + §1
- `CLAUDE.md` §3.1 + §3.7.5: 治本路径 + decision ledger → 本 doc §0 + §3.3

---

## 11. 修订日志

- v1.0 · 2026-05-04 · worker-B2-biz · 初稿 · 4 doc 系列收官

**下一次修订触发**:
- 第 1 个真实 Lead → POC 走完 → §6 漏斗数字 + §3 异议 FAQ 命中率回写
- 第 1 个 Pilot 客户走完 6 月 → §2 ROI 模型保守值 vs 实际值修正
- 销售内训演练 3 轮后 → §1.5 速记卡补漏
- 友商出新版本 → §4 对位话术更新
