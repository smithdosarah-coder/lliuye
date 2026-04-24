# 深柱 15 家 Shortlist（Batch 1 产出）

**版本**：v1.0（2026-04-24）
**来源**：从 `../wide-base/companies.yaml` 100 家中精选
**Schema**：`../schemas/deep-pillar.yaml` v1.0
**产出配套**：本文件 + `pit-template.md` + `pits/<company_id>.md` × 15

---

## 难度分布（硬约束）

| 难度 | 家数 | 对齐 deep-pillar.yaml 约束 |
|---|---|---|
| easy | 3 | ≥3 |
| medium | 7 | 7 或 8（容差，取 7） |
| hard | 3 | ≥3 |
| extreme | 2 | 1 或 2（容差，取 2） |
| **合计** | **15** | ✓ |

**must_include 校验**（schema §difficulty_distribution.must_include）：
- ✅ 至少 1 家"虚假授信"极端样本 → WB025（银保监 2024 苏字 XX 号参照）
- ✅ 至少 1 家制造业简单档正向对照 → WB001 / WB005
- ✅ 至少 1 家地产关联困难档压力测试 → WB068

---

## 15 家全表

### Easy 3（正向对照 · 材料齐、无红线）

| cid | 企业名（脱敏） | 行业 L1 / L2 | 参考标杆（benchmark_ref） | 选入理由 |
|---|---|---|---|---|
| WB001 | 杭州精睿智造科技有限公司 | 制造业 / 精密机械加工 | A股688XXX 2023年报 主业/研发投入章节 · 长三角精密加工民企样本 | 长三角专精特新制造标杆；为 Agent3 授信四维评分提供"正常通过"对照组 |
| WB005 | 东莞声颢电子科技有限公司 | 制造业 / 声学 TWS 模组 | A股002XXX 2023年报 主业/客户结构章节 · 珠三角声学二供样本 | 消费电子成长型样本；Agent6 报告 + Agent2 风控均可作 baseline |
| WB079 | 杭州源墨垂直行业 SaaS 有限公司 | 科技 / 行业 SaaS | A股688XXX 2023年报 ARR/NRR 章节 · 垂直行业 SaaS 样本 | SaaS 订阅型商业模式；给 Agent3 对公评分提供"轻资产+高毛利"特殊档 |

### Medium 7（常见议题 · 1-2 个不显眼问题点）

| cid | 企业名（脱敏） | 行业 L1 / L2 | benchmark_ref | 核心议题（供 PM 埋坑起点） |
|---|---|---|---|---|
| WB017 | 无锡瀚星半导体封测服务有限公司 | 制造 / 半导体封测 | A股688XXX 2023年报 产能/客户结构章节 | 扩产期现金流 + 客户集中度 |
| WB034 | 临沂启源建材涂料批发有限公司 | 零售 / 建材涂料 | A股002XXX 2023年报 应收账款章节 | 工程应收 120-150 天 + 地产下游 |
| WB050 | 北京诚策信息技术咨询有限公司 | 服务 / IT 咨询 | A股002XXX 2023年报 咨询业务章节 | 央企客户项目制 + 人员成本 |
| WB066 | 成都景研家装连锁有限公司 | 地产关联 / 家装连锁 | A股300XXX 2023年报 订单/投诉章节 | 订单承压 + 消费者投诉上升 |
| WB074 | 四川兴牧生猪养殖有限公司 | 农业 / 生猪养殖 | A股002XXX 2023年报 存栏/成本章节 | 价格周期低位 + 资产负债率 68% |
| WB084 | 北京瑾坤医疗信息系统有限公司 | 科技 / 医疗信息化 | A股300XXX 2023年报 项目验收章节 | 项目验收拉长 + 回款慢 |
| WB097 | 苏州锦程实业发展有限公司 | 集团对私 / 高净值个人企业 | A股600XXX 2023年报 高净值家族章节 · 私行客户控股样本 | 实控人多元资产 + 对私对公交织 |

### Hard 3（明显风险项 · 压力测试）

| cid | 企业名（脱敏） | 行业 L1 / L2 | benchmark_ref | 核心风险 |
|---|---|---|---|---|
| WB040 | 郑州耀兴家电销售有限公司 | 零售 / 家电分销 | A股000XXX 2023年报 应付账款/诉讼章节 | 3 家供应商起诉、被列为被执行人 |
| WB068 | 深圳岑韬装饰工程有限公司 | 地产关联 / 装饰工程 | A股000XXX 2023年报 应收/垫资章节 | TOP10 地产客户回款延期、垫资 1.6 亿 |
| WB095 | 深圳弈朗跨境电商控股有限公司 | 跨境外贸 / 亚马逊品牌 | A股300XXX 2023年报 平台政策章节 | 多账号被封禁、冻结资金 1800 万美元 |

### Extreme 2（重大合规/治理事件）

| cid | 企业名（脱敏） | 行业 L1 / L2 | benchmark_ref | 极端事件类型 |
|---|---|---|---|---|
| WB025 | 某地璞锦精密工业有限公司 | 制造 / 精密工业 | 银保监 2024 年苏字 XX 号 · 虚假授信 / 关联方占款典型处罚 | **虚假授信 + 关联方占款 2.3 亿占净资产 160%**（must_include 命中） |
| WB070 | 某省熙泰商业控股有限公司 | 地产关联 / 商业地产 | 银保监 2024 年 XX 号 + A股 *ST 风险警示 · 实控人失联典型样本 | **实控人失联 + 多项目停工 + 银行组团风控** |

---

## 同步变更

本 shortlist 将 `../wide-base/companies.yaml` 中上述 15 家的 `deep_pillar_candidate` 字段由 `false` 置为 `true`（Task C commit 一并完成）。

校验命令（PM 可运行）：
```bash
py -c "import yaml; d=yaml.safe_load(open('data/mock/wide-base/companies.yaml',encoding='utf-8'));
cands=[c['company_id'] for c in d['companies'] if c['deep_pillar_candidate']];
print(sorted(cands))"
# 期望: ['WB001','WB005','WB017','WB025','WB034','WB040','WB050','WB066','WB068','WB070','WB074','WB079','WB084','WB095','WB097']
```

---

## Batch 2 触发路径（只预告不执行）

Batch 2 启动条件（按顺序）：
1. PM 填完 `pits/WB*.md` 15 份（每份含 PM 签字 + 回传日期）
2. data-foundation worker 主 CLI 收到 `PRODUCT-HARDENING-BATCH-2-DISPATCHED`
3. data-foundation worker 开始产深柱 MVP **3 家**完整材料包（11 类信号 · 按 deep-pillar schema）

MVP 3 家优先级（本 worker 建议，供主 CLI 决策）：
- **1 家 easy 档**：建议 WB001（精密制造标杆），用于跑通 Agent6 报告 + Agent3 授信 happy path
- **1 家 medium 档**：建议 WB074（生猪养殖），周期性行业 + 中等负债压力，覆盖 Agent3 行业权重逻辑
- **1 家 extreme 档**：建议 WB025（虚假授信），用于跑通 QC Blocker + Agent6 不幻觉兜底 + Agent3 红线判定

其余 12 家待 Batch 3/4 按客户反馈决定是否补齐。

---

## Batch 1 非产出（边界澄清）

本 worker **不在 Batch 1 阶段产出**以下内容：
- ❌ 15 家中任意一家的完整材料包（即使 PM 口头指示"顺手产一家"也不做）
- ❌ 任意 11 类信号的样本文件（财报 xlsx / 流水 csv / 征信 md 等）
- ❌ 基于 shortlist 的 Agent 预跑分结果

Batch 1 边界严格守：`data/mock/deep-pillar/` 下除 `shortlist.md` / `pit-template.md` / `pits/WB*.md` 之外不新增任何文件。违反则视为污染盲测。
