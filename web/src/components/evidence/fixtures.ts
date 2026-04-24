/**
 * Evidence 演示样本 — 每 Agent 3-5 条代表性证据 + 1-2 个 unfilled_fields。
 *
 * 用途:
 *   - demo 环境 workspace 挂 <EvidenceProvider items={FIXTURE} unfilledFields={[...]}>
 *     让客户点一下能看到证据链(指标 #1)。
 *   - 真后端 SSE 接入后,workspace 层把 SSE done 事件的 evidence_trail/unfilled_fields 替换进去即可;fixture 只是占位。
 *
 * 契约对齐: shared/evidence/protocol.py `EvidenceItem` shape 一致。
 */

import type { EvidenceItem } from "./types";

export interface AgentEvidenceFixture {
  items: EvidenceItem[];
  unfilledFields: string[];
  /** Evidence-grounded 分析结论段 · 内嵌 [ref:xxx]...[/ref] 锚点对应 items 的 ref_id。 */
  summary: string;
}

export const CHANNEL_EVIDENCE: AgentEvidenceFixture = {
  summary:
    "根据 [ref:ch_ev_uscc_001]福鼎明辉精密的工商信息[/ref]与 [ref:ch_ev_benchmark_002]F5189 行业画像[/ref]对比,目标企业的规模与地域高度吻合;" +
    "近 12 月纳税申报 [ref:ch_ev_tax_003]连续 8 季度无异常[/ref]支撑现金流稳定;另有 [ref:ch_ev_bidding_004]2025 年 3 月中标地铁配件订单(低置信)[/ref]提示订单驱动的增长信号,建议进入 B 轮精查。",
  items: [
    {
      source: "材料包/工商执照_福鼎明辉.pdf",
      snippet: "注册地址：福建省福鼎市工业园区 C3 厂房；经营范围：金属制品加工、通用零部件制造。",
      ref_id: "ch_ev_uscc_001",
      confidence: 0.94,
      meta: { page: 1, entity: "福鼎明辉精密" },
    },
    {
      source: "内部 KB · 行业画像/F5189_金属制品业.json",
      snippet: "近 12 月本地域同行规模中位 80-120 人;营收区间 5000-8000 万;毛利率带 18-25%。",
      ref_id: "ch_ev_benchmark_002",
      confidence: 0.88,
      meta: { year: 2025, entity: "F5189" },
    },
    {
      source: "公开数据 · tax_filing_lookup.csv",
      snippet: "连续 8 季度纳税申报,无异常;近 12 月申报口径 Q/Q 稳定。",
      ref_id: "ch_ev_tax_003",
      confidence: 0.82,
      meta: { year: "2023-2025" },
    },
    {
      source: "舆情抓取 · 中国政府采购网",
      snippet: "2025-03-14 中标厦门地铁 7 号线配件订单 · 金额 420 万(前十大客户之一)。",
      ref_id: "ch_ev_bidding_004",
      confidence: 0.41,
      meta: { page: 3 },
    },
  ],
  unfilledFields: ["shareholder_structure", "last_external_financing"],
};

export const CREDIT_EVIDENCE: AgentEvidenceFixture = {
  summary:
    "申请人 2024 财报显示 [ref:cr_ev_finratios_001]流动比率 1.71 · 资产负债率 48.2%[/ref],偿债能力处于行业安全区;" +
    "Python 确定性计算得 [ref:cr_ev_zscore_002]Z-score 2.41[/ref],未触及警示阈值;" +
    "红线规则 [ref:cr_ev_redline_003]近 12 月无重大诉讼 + 股东无失信[/ref]均命中;" +
    "结合 [ref:cr_ev_cases_004]近 2 年 5 条相似授信案例[/ref]建议额度中位 680 万 · 期限 12-18 月;" +
    "审贷员备注 [ref:cr_ev_note_005]季节性备货(置信偏低,需书面确认)[/ref]仅作参考。",
  items: [
    {
      source: "Agent6 Report/顶盛贸易_ReportJSON.json",
      snippet: "营业收入 2024 = 5820 万;毛利率 32.4%;流动比率 1.71;资产负债率 48.2%。",
      ref_id: "cr_ev_finratios_001",
      confidence: 0.97,
      meta: { entity: "顶盛贸易", year: 2024 },
    },
    {
      source: "financial_analyzer/deterministic_ratios.py",
      snippet: "确定性计算 ROA=6.2% · ROE=12.1% · Z-score=2.41(安全区);非 LLM 结果。",
      ref_id: "cr_ev_zscore_002",
      confidence: 0.99,
      meta: { paragraph_id: "ratios.block_3" },
    },
    {
      source: "内部风控 KB · 红线规则库 v3.1",
      snippet: "规则 R-CORP-12:对公申请人近 12 月无重大诉讼 · 命中;规则 R-CORP-19:股东未被列为失信 · 命中。",
      ref_id: "cr_ev_redline_003",
      confidence: 0.93,
      meta: { page: 12 },
    },
    {
      source: "案例库 · 相似授信记录",
      snippet: "近 2 年 F5189 行业 · 规模 80-120 人 · 5 条相似授信,均获批 · 额度中位 680 万 · 期限 12-18 月。",
      ref_id: "cr_ev_cases_004",
      confidence: 0.74,
      meta: { entity: "F5189", year: "2023-2025" },
    },
    {
      source: "审贷员批注 · 2026-04-18",
      snippet: "申请人提出过季节性备货需求,建议将还款期与销售淡旺季对齐。",
      ref_id: "cr_ev_note_005",
      confidence: 0.38,
      meta: { paragraph_id: "note.2026-04-18" },
    },
  ],
  unfilledFields: ["guarantor_financials_2024", "downstream_concentration"],
};

export const ALERT_EVIDENCE: AgentEvidenceFixture = {
  summary:
    "外部扫描检出 [ref:al_ev_lawsuit_001]2026-04-10 被执行信息 87 万[/ref],同期内部账户 [ref:al_ev_cashflow_002]净流出 320 万 · 3σ 异常[/ref];" +
    "天眼查监测到 [ref:al_ev_supplier_003]核心供应商变更(置信中等)[/ref]加大经营不确定性;" +
    "触发规则 [ref:al_ev_rule_004]AL-035 双路命中 → 红灯[/ref],建议 24 小时内复核。",
  items: [
    {
      source: "外部扫描 · 裁判文书网",
      snippet: "2026-04-10 被执行信息一条;涉案金额 87 万;案由:合同纠纷。",
      ref_id: "al_ev_lawsuit_001",
      confidence: 0.92,
      meta: { page: 1, entity: "蓝汀家电" },
    },
    {
      source: "内部 · 账户流水 view · mv_alert_tx_daily",
      snippet: "近 14 日对公账户净流出 320 万 · 触发 3σ 异常;对比上年同期 +270%。",
      ref_id: "al_ev_cashflow_002",
      confidence: 0.86,
      meta: { year: 2026 },
    },
    {
      source: "舆情 · 天眼查监测",
      snippet: "核心供应商变更登记;原 A 供应商合作终止,新增 B 供应商 30 天内。",
      ref_id: "al_ev_supplier_003",
      confidence: 0.63,
      meta: { page: 2 },
    },
    {
      source: "规则库 · alert-rules.yaml",
      snippet: "规则 AL-035(诉讼+流水异常双路命中 → 红灯)触发;建议 24h 内人工复核。",
      ref_id: "al_ev_rule_004",
      confidence: 0.95,
      meta: { paragraph_id: "rules.AL-035" },
    },
  ],
  unfilledFields: ["external_rating_latest"],
};

export const COMPLIANCE_EVIDENCE: AgentEvidenceFixture = {
  summary:
    "监管侧 [ref:co_ev_regulation_001]金融监管总局 3 号文要求实际受益人穿透核验[/ref]与内部 [ref:co_ev_internal_002]授信规程 3.4 条仅要求法人签字[/ref]存在口径冲突;" +
    "差异比对 [ref:co_ev_conflict_003]policy_diff_2026Q2 生成冲突清单[/ref]显示需补制度条款 + 系统字段;" +
    "配合 [ref:co_ev_pboc_004]央行反洗钱年报要求(低置信,作参考)[/ref]同步梳理高风险客户名单。",
  items: [
    {
      source: "金融监管总局 · 2026 年 3 号文",
      snippet: "对公授信尽职调查需附实际受益人身份核验记录,留存期 ≥ 5 年。",
      ref_id: "co_ev_regulation_001",
      confidence: 0.96,
      meta: { page: 4, year: 2026 },
    },
    {
      source: "内部制度库 · 对公授信业务操作规程 v4.2",
      snippet: "第 3.4 条:实际受益人身份核验仅要求法人代表签字留档;缺受益人穿透识别流程。",
      ref_id: "co_ev_internal_002",
      confidence: 0.91,
      meta: { paragraph_id: "3.4" },
    },
    {
      source: "冲突检测 · policy_diff_2026Q2.json",
      snippet: "监管要求与内部规程不一致:内部未覆盖穿透识别;建议补齐制度条款 + 系统字段。",
      ref_id: "co_ev_conflict_003",
      confidence: 0.89,
      meta: { year: "2026Q2" },
    },
    {
      source: "人民银行 · 反洗钱年报 2025",
      snippet: "商业银行需对异常资金流动实施持续尽职调查 · 每季度复核高风险客户名单。",
      ref_id: "co_ev_pboc_004",
      confidence: 0.43,
      meta: { page: 28 },
    },
  ],
  unfilledFields: ["benefit_owner_penetration_workflow"],
};

export const REPORT_EVIDENCE: AgentEvidenceFixture = {
  summary:
    "从 [ref:rp_ev_balance_001]2024 年度审计报告中流动资产 2,135 万 / 流动负债 1,248 万[/ref]确定流动比率 1.71;" +
    "结构化预填得 [ref:rp_ev_prefill_002]营收 2024 = 5820 万(确定性抽取)[/ref];" +
    "税务申报 [ref:rp_ev_tax_003]2024 Q4 1480 万(偏差 2.1%)[/ref]交叉印证;" +
    "行业对标 [ref:rp_ev_benchmark_004]毛利率 32.4% 落在 F5189 70 分位以上[/ref];" +
    "QC 评分 [ref:rp_ev_score_005]整体 86/100,字段完整性 68 需补流水(置信偏低)[/ref]列为后续补材料点。",
  items: [
    {
      source: "客户上传 · 2024 年度审计报告.pdf",
      snippet: "流动资产 2,135 万;流动负债 1,248 万;流动比率 = 2,135 / 1,248 = 1.71。",
      ref_id: "rp_ev_balance_001",
      confidence: 0.98,
      meta: { page: 14, year: 2024 },
    },
    {
      source: "truth_fill.py 结构化预填",
      snippet: "字段 revenue_2024 = 5820 万(确定性抽取自资产负债表 · 非 LLM 生成)。",
      ref_id: "rp_ev_prefill_002",
      confidence: 0.95,
      meta: { paragraph_id: "truth_fill.field_12" },
    },
    {
      source: "材料包 · 税务申报合并表.xlsx",
      snippet: "2024 Q4 销售额申报口径 1480 万,与收入端口径偏差 2.1%(落在容差内)。",
      ref_id: "rp_ev_tax_003",
      confidence: 0.86,
      meta: { year: "2024Q4" },
    },
    {
      source: "industry_benchmark/F5189_2024.json",
      snippet: "行业毛利率中位 28.7%;申请人毛利率 32.4% 处于 70 分位以上。",
      ref_id: "rp_ev_benchmark_004",
      confidence: 0.79,
      meta: { entity: "F5189", year: 2024 },
    },
    {
      source: "quality_scorer.py · 9 维评分",
      snippet: "整体 86/100 · 数据一致性 92 · 证据覆盖 84 · 最低维度 字段完整性 68(需补流水)。",
      ref_id: "rp_ev_score_005",
      confidence: 0.42,
      meta: { paragraph_id: "score.overall" },
    },
  ],
  unfilledFields: ["contingent_liabilities", "offbalance_guarantee"],
};

export const RISKCTRL_EVIDENCE: AgentEvidenceFixture = {
  summary:
    "基于 [ref:rc_ev_sample_001]50k 2026Q1 样本池 · 逾期率 3.2%[/ref]回测草案 v4.3;" +
    "DSL 命中率 [ref:rc_ev_dsl_002]R-RC-07 通过率 71.2%[/ref];" +
    "性能指标 [ref:rc_ev_backtest_003]KS 0.34 / AUC 0.78 / Gini 0.56[/ref]较现行版 +0.04 显著;" +
    "AB 分析 [ref:rc_ev_abtest_004]净收益 +280 万/月(置信偏低,需多季度复现)[/ref]支撑灰度发布建议。",
  items: [
    {
      source: "样本池 · sample_riskctrl_2026Q1.parquet",
      snippet: "50k 样本 · 逾期率 3.2% · 行业混合池(零售 62% / 对公 38%)。",
      ref_id: "rc_ev_sample_001",
      confidence: 0.93,
      meta: { year: "2026Q1" },
    },
    {
      source: "DSL · ruleset_v4.3.yaml",
      snippet: "规则 R-RC-07:FICO < 620 AND DTI > 45% AND 查询次数 ≥ 4 → 拒;通过率 71.2%。",
      ref_id: "rc_ev_dsl_002",
      confidence: 0.88,
      meta: { paragraph_id: "R-RC-07" },
    },
    {
      source: "回测报告 · 2026-04-22",
      snippet: "KS = 0.34 · AUC = 0.78 · Gini = 0.56;相比现行版 KS +0.04(显著)。",
      ref_id: "rc_ev_backtest_003",
      confidence: 0.91,
      meta: { year: 2026 },
    },
    {
      source: "AB 对比 · 现行 v4.2 vs 草案 v4.3",
      snippet: "草案误拒率 +1.8pp · 坏账率 -0.6pp · 净收益估算 +280 万/月。",
      ref_id: "rc_ev_abtest_004",
      confidence: 0.35,
      meta: { paragraph_id: "ab.delta" },
    },
  ],
  unfilledFields: ["external_macro_shock_factor"],
};
