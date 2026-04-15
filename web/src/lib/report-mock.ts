/**
 * Mock data for Agent6 report pipeline — used when V14-A backend isn't up.
 * Profiles align with agent_credit/mock_data/corporate_profiles/*.json so
 * the downstream handoff carries a real schema, not synthetic fluff.
 */
import type {
  EnterpriseProfile,
  Question,
  ReportSection,
} from "./credit-types";

export const MOCK_PROFILES: Record<string, EnterpriseProfile> = {
  dingsheng_trade: {
    profile_id: "corp_dingsheng_001",
    company_name: "鼎盛商贸有限公司",
    unified_credit_code: "91440000MAZZEXAMPLE",
    industry: "F51-批发业",
    establishment_date: "2018-03-15",
    registered_capital: "1000",
    employee_count: 42,
    region: "广东省佛山市",
    main_business: "建材批发与代理",
    controller_name: "王某",
    controller_share_pct: "80%",
    financial_anchors: {
      revenue_latest: 18000,
      revenue_prev: 22000,
      net_profit_latest: -420,
      net_profit_prev: 350,
      total_assets: 9600,
      total_liabilities: 7680,
      net_assets: 1920,
      accounts_receivable: 4500,
      inventory: 2200,
      operating_cash_flow: -680,
      short_term_borrowing: 4200,
      ebitda: -180,
      period: "2025年度",
    },
    request: { amount: 500, purpose: "补充流动资金", term_months: 12 },
  },
  zhangsan_restaurant: {
    profile_id: "sme_zhangsan_001",
    company_name: "张某个体餐饮",
    industry: "I62-餐饮业",
    establishment_date: "2022-06-01",
    region: "浙江省杭州市",
    main_business: "社区快餐店",
    controller_name: "张某",
    financial_anchors: {
      monthly_revenue: 18,
      months_in_business: 36,
      period: "2025H1",
    },
    request: { amount: 50, purpose: "门店装修与周转", term_months: 24 },
  },
};

export const MOCK_SECTIONS: Record<string, ReportSection[]> = {
  dingsheng_trade: [
    {
      id: "basic",
      title: "一、基本情况",
      content:
        "鼎盛商贸有限公司成立于 2018 年 3 月,注册资本 1000 万元,位于广东省佛山市,主营建材批发与代理。现有员工 42 人,实际控制人王某持股 80%,经营权与所有权高度集中。",
    },
    {
      id: "operation",
      title: "二、经营与行业",
      content:
        "受下游地产行业深度调整影响,2025 年度营收同比下滑 18% 至 1.80 亿元。主要客户为关联公司鼎盛地产,关联方销售占比约 45%,客户集中度偏高,回款周期由 90 天拉长至 150 天以上。",
    },
    {
      id: "finance",
      title: "三、财务状况",
      content:
        "2025 年度资产负债率 80.0%,净利润亏损 420 万元(上年盈利 350 万元),经营性现金流为 -680 万元,短期借款 4200 万元,速动比率约 0.6,短期偿债压力突出。",
    },
    {
      id: "request",
      title: "四、本次申请",
      content:
        "申请流动资金贷款 500 万元,期限 12 个月,用途为补充流动资金。建议关注点:关联交易真实性、客户集中度、存货周转率、还款来源。",
    },
    {
      id: "conclusion",
      title: "五、初步结论",
      content:
        "(待 Agent3 下游授信决策模块回填审批意见)",
    },
  ],
  zhangsan_restaurant: [
    {
      id: "basic",
      title: "一、基本情况",
      content:
        "申请人张某,个体餐饮经营者,于 2022 年 6 月在杭州市开设社区快餐店,经营 3 年,店面自有装修。",
    },
    {
      id: "operation",
      title: "二、经营情况",
      content:
        "月均营业收入约 18 万元,主要客群为周边居民与写字楼白领,晚高峰翻台稳定,疫情后流水呈上升趋势。",
    },
    {
      id: "request",
      title: "三、申请用途",
      content:
        "申请普惠经营贷 50 万元,期限 24 个月,用途为门店二次装修与日常周转。",
    },
    {
      id: "conclusion",
      title: "四、初步结论",
      content: "(待 Agent3 下游普惠评分与额度建议回填)",
    },
  ],
};

export const MOCK_QUESTIONS: Question[] = [
  {
    id: "q_collateral",
    section_id: "request",
    question: "本次贷款是否提供抵押或第三方担保?",
    hint: "示例:房产抵押(评估值 / 所在地)、法人连带保证、股权质押等;若无请填「无」。",
    input_type: "textarea",
  },
  {
    id: "q_related_party",
    section_id: "operation",
    question: "关联方交易的真实性依据是什么?",
    hint: "建议提供合同、银行回单、物流签收单等其中至少 1 项交叉验证。",
    input_type: "textarea",
  },
  {
    id: "q_repay_source",
    section_id: "request",
    question: "除经营回款外,是否存在其他还款来源?",
    hint: "如股东个人资产、关联方资金支持、已有储蓄等。",
    input_type: "textarea",
  },
];
