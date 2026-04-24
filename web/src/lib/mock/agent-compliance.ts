/**
 * Agent Compliance (合规 · A05) — Policy event-driven matrix mock fixtures.
 * Feeds the /archive/compliance workspace (policy stream + conflict list + tiering).
 */

export type PolicyEvent = {
  id: string;
  publishedAt: string; // narrow
  issuer: string;
  title: string;
  digest: string;
  scope: string[];
  link?: string;
  status: "scanning" | "scanned" | "needs-review";
};

export type ComplianceFinding = {
  id: string;
  eventId: string;
  policy: string; // 指向 PolicyEvent.title
  policyClause: string; // e.g. "§3.2"
  internalDoc: string;
  internalClause: string;
  severity: "critical" | "major" | "minor";
  kind: "conflict" | "gap" | "outdated";
  summary: string;
  suggestion: string;
  reviewedBy: string | null;
};

export type ComplianceDeptFilter = {
  id: string;
  label: string;
  count: number;
};

export const COMPLIANCE_STATS = {
  weeklyProcessed: "17",
  successRate: "88%",
  avgDuration: "4.2 分钟",
} as const;

export const COMPLIANCE_DEPTS: ComplianceDeptFilter[] = [
  { id: "all", label: "全部制度文档", count: 248 },
  { id: "credit-policy", label: "授信政策", count: 44 },
  { id: "risk-ops", label: "风险操作", count: 61 },
  { id: "compliance-gov", label: "合规治理", count: 28 },
  { id: "kyc-aml", label: "反洗钱 / KYC", count: 35 },
  { id: "post-loan", label: "贷后管理", count: 22 },
  { id: "data-privacy", label: "数据与隐私", count: 18 },
  { id: "branch-ops", label: "分支行操作", count: 40 },
];

export const COMPLIANCE_EVENTS: PolicyEvent[] = [
  {
    id: "pol-2026-014",
    publishedAt: "04-19",
    issuer: "国家金融监管总局",
    title: "《普惠小微信用贷款额度与利率定价审慎管理通知》",
    digest:
      "明确年度增量利率不得超过同期 LPR+250bps,信用额度采用客户净资产 2.5 倍上限,豁免清单收窄。",
    scope: ["授信政策", "分支行操作"],
    link: "https://www.nfra.gov.cn/n47/n48/c2026-04-19/doc.html",
    status: "scanned",
  },
  {
    id: "pol-2026-013",
    publishedAt: "04-18",
    issuer: "人民银行反洗钱局",
    title: "《关于规范客户身份识别和高风险客户尽调的补充规定》",
    digest:
      "对高风险客户身份再识别周期由 3 年缩短至 2 年;新增 7 类跨境交易场景作为增强尽调触发项。",
    scope: ["反洗钱 / KYC", "合规治理"],
    status: "scanned",
  },
  {
    id: "pol-2026-012",
    publishedAt: "04-16",
    issuer: "地方金融监管局",
    title: "《关于强化商贸批发类客户贷后资金用途监控的指导意见》",
    digest:
      "要求单笔受托支付 ≥50 万的商贸批发客户,贷后留痕需覆盖发票、运单、付款凭证三联证据链。",
    scope: ["贷后管理", "风险操作"],
    status: "needs-review",
  },
  {
    id: "pol-2026-011",
    publishedAt: "04-14",
    issuer: "国家数据局",
    title: "《金融行业数据跨机构共享与安全管控指引(2026 版)》",
    digest: "明确征信级字段与经营类字段的共享分级,新增「可撤回授权」接口能力要求。",
    scope: ["数据与隐私", "合规治理"],
    status: "scanned",
  },
  {
    id: "pol-2026-010",
    publishedAt: "04-11",
    issuer: "国家金融监管总局",
    title: "《银行理财产品信息披露规范》修订版",
    digest: "销售页面 3 日冷静期 · 产品说明书需独立披露底层资产穿透视图。",
    scope: ["合规治理"],
    status: "scanned",
  },
];

export const COMPLIANCE_FINDINGS: ComplianceFinding[] = [
  {
    id: "f-001",
    eventId: "pol-2026-014",
    policy: "普惠小微信用贷款额度与利率定价审慎管理通知",
    policyClause: "§3.2 利率上限",
    internalDoc: "《XX 银行普惠金融授信操作细则 2025》",
    internalClause: "§4.1 利率定价",
    severity: "critical",
    kind: "conflict",
    summary:
      "内部细则上限为 LPR+320bps,政策要求 LPR+250bps,冲突差 70bps · 涉及在贷合同 1,284 份。",
    suggestion: "在 2026-05-01 前发修订版,存量合同采用就高不就低转挂接。",
    reviewedBy: null,
  },
  {
    id: "f-002",
    eventId: "pol-2026-014",
    policy: "普惠小微信用贷款额度与利率定价审慎管理通知",
    policyClause: "§2.4 信用额度上限",
    internalDoc: "《小微客户授信审查要点 2024 版》",
    internalClause: "§6.3 授信额度",
    severity: "major",
    kind: "outdated",
    summary: "内部要点用净资产 3 倍,政策收窄为 2.5 倍;15% 在审卷宗需重新测算。",
    suggestion: "打补丁说明 + 授信额度重测清单下发各分行。",
    reviewedBy: "王合规",
  },
  {
    id: "f-003",
    eventId: "pol-2026-013",
    policy: "客户身份识别和高风险客户尽调补充规定",
    policyClause: "§5 高风险再识别周期",
    internalDoc: "《反洗钱客户尽职调查管理办法 2024 修订》",
    internalClause: "§9 再识别",
    severity: "major",
    kind: "gap",
    summary: "现办法为 3 年周期,需缩短至 2 年;涉及高风险客户标签 218 户。",
    suggestion: "修订办法 + 排期 6 月底前完成全量客户再识别。",
    reviewedBy: null,
  },
  {
    id: "f-004",
    eventId: "pol-2026-013",
    policy: "客户身份识别和高风险客户尽调补充规定",
    policyClause: "附表 7 类跨境场景",
    internalDoc: "《对公跨境交易反洗钱操作手册》",
    internalClause: "§3 触发条件",
    severity: "minor",
    kind: "gap",
    summary: "新增 7 类跨境场景中,有 3 类为内部手册未覆盖(跨境电商分账、RCEP 关税退补、离岸人民币).",
    suggestion: "出台补充附件 · 分支行限时 30 天内知悉并演练。",
    reviewedBy: null,
  },
  {
    id: "f-005",
    eventId: "pol-2026-012",
    policy: "商贸批发类客户贷后资金用途监控指导意见",
    policyClause: "§2.1 三联证据链",
    internalDoc: "《贷后检查工作指引 2023 版》",
    internalClause: "§7.2 资金流向核查",
    severity: "major",
    kind: "conflict",
    summary: "现指引仅要求发票 + 付款凭证,未要求运单;涉及商贸批发存量客户 402 户。",
    suggestion: "更新指引 + 上线系统强校验 · 以受托支付金额 ≥50 万为触发点。",
    reviewedBy: null,
  },
  {
    id: "f-006",
    eventId: "pol-2026-011",
    policy: "金融行业数据跨机构共享与安全管控指引",
    policyClause: "§6 可撤回授权",
    internalDoc: "《客户数据授权管理办法》",
    internalClause: "§4 授权撤销",
    severity: "critical",
    kind: "gap",
    summary: "现办法不支持客户单通道撤回,需新增接口与操作流程 · T+15 技术就绪。",
    suggestion: "数据中台 + 合规 + 法务三方会签,6 月 1 日前上线可撤回授权能力。",
    reviewedBy: null,
  },
];
