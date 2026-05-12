# SLO 4 · Task D · 6 Agent Template Path Before/After (LLM-free verify)

> **Scope**: 仅 template / fallback path · LLM 不可用时的 deterministic 路径
> **Blocker**: admin 真号 E2E (含 LLM 路径) 需 SLO 1 (DEEPSEEK key) + SLO 2 (admin auth)
> **Rubric**: docs/contracts/agent-output-rubric-2026-05-11.md

## Summary · 6/6 agent template path pass rubric anchors

| Agent | Passed | Forbidden hit | Require hits / min |
|---|---|---|---|
| channel | ✅ | ✅ none | 3/3 |
| credit | ✅ | ✅ none | 4/3 |
| alert | ✅ | ✅ none | 3/2 |
| compliance | ✅ | ✅ none | 3/2 |
| report | ✅ | ✅ none | 3/1 |
| riskctrl | ✅ | ✅ none | 3/2 |

## channel

### Sample output (template path)

```
杭州精密电子有限公司您好，贵司电子元件、中型，营收 15000 万，配 专精特新 资质，匹配我们行『保理 / 应收质押融资』最高 2000万，按同类客户经验放款周期 5-10 个工作日。方便本周内安排 10 分钟通话沟通融资节奏吗？
```

- Passed: ✅
- ✅ Forbidden phrases: none
- Required anchors hit: ['专精特新|高新|小巨人', '\\d+\\s*万', '工作日|本周内'] (3/3)

## credit

### Sample output (template path)

```
企业 杭州精密电子有限公司 综合评分 75 分（B 级）。
四维评分: 
  - 财务 72 分 (良好) · 参考确定性指标 (流动比 / 资产负债率 / 净利率 / 现金流) 见 features_snapshot
  - 行业 78 分 (良好) · 参考行业增长 / 地位 / 政策导向 见 industry_card
  - 经营 76 分 (良好) · 参考成立年限 / 员工 / 主营稳定性 / 客户集中度 见 features_snapshot
  - 担保 74 分 (良好) · 参考押品类型 / 覆盖率 / 担保人资信 见 profile.guarantee_info
触发 1 条黄灯软告警 (需审贷会讨论): 资产负债率红线 (实际 0.82 vs 阈值 0.8)。
结论: 通过 · 建议额度 3000 万元 · 期限 36 个月 · 放款条件见 conditions[] · 三法测算见 amount_methods · 完整证据链见 decision_graph。
```

- Passed: ✅
- ✅ Forbidden phrases: none
- Required anchors hit: ['财务\\s+\\d+\\s+分\\s*\\(', '(优秀|良好|合格|薄弱|不达标)', '红灯|黄灯|绿灯', '实际\\s+\\d'] (4/3)

## alert

### Sample output (template path)

```
资产负债率72.0%，接近 80% 警戒线 · 客户经理 7d 内电话确认偿债来源 + 评估追加担保 / 压缩额度必要性
```

- Passed: ✅
- ✅ Forbidden phrases: none
- Required anchors hit: ['客户经理.*\\d+\\s*[d天]\\s*内', '现场|电话|核查|核档', '24h|3d|7d|30d|本周'] (3/2)

## compliance

### Sample output (template path)

```
[
  {
    "category": "改",
    "title": "修订条款以匹配 银保监〔2025〕12 号第 3 条 · disposition: 暂停 / 法律部 review",
    "text": "业务事件 EVT-X1（loan）冲突字段「kyc_completed」触发 POL-001 银保监〔2025〕12 号第 3 条 · 严重程度 critical · 建议: 立即暂停本笔业务 · 法律部 7d 内 review 该政策条款 · 业务条款责任部门同步修订对应字段定义、阈值与触发规则 · 修订稿提交合规专家终审."
  }
]
```

- Passed: ✅
- ✅ Forbidden phrases: none
- Required anchors hit: ['暂停|强制整改|监测|法律部 review', '\\d+d\\s*内|立即', '责任部门|业务部门|合规官'] (3/2)

## report

### Sample output (template path)

```
营收 12000 万 · 同比增长 14.9%

【企业事实(来自 KB 解析)】
  - company_name: xx 制造

【行业参考卡片 · LLM 行业章节引用 · 禁编造】
  - 电子元件行业: 2025 国产替代加速 · 中长期景气 · 政策支持 70 亿减税

【政策参考卡片 · LLM 政策章节引用 · 必带 evidence_date / 出处】
  - 工信部 [2025] 36 号 半导体支持 (2025-08-15 · 工信部官网): 对国产替代企业最高补贴 30%
```

- Passed: ✅
- ✅ Forbidden phrases: none
- Required anchors hit: ['行业参考卡片', '政策参考卡片', 'evidence_date|出处'] (3/1)

## riskctrl

### Sample output (template path)

```
### 策略效果指标

- **KS统计量**: 0.4200

> KS = 0.420 处于同业基准 0.35-0.50 健康区间 · 策略区分能力中等 · 可上线 · 建议双周复核低分样本

```

- Passed: ✅
- ✅ Forbidden phrases: none
- Required anchors hit: ['同业基准\\s+0\\.35-0\\.50', '(优秀档|健康区间|不建议直接上线|不可上线)', '可上线|定期回测|检查阈值|加新特征|重抽样|样本量'] (3/2)
