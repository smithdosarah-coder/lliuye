"use client";

/**
 * CreditV2 — DOM port of design_mockups/stage5/mockup-v2/credit.html.
 * Credit Decision · Agent6 下游 · 四维评分 + 红线 + 黄线.
 */

import {
  V2Shell,
  ChatBlk,
  SseBlk,
  DocWrap,
  AuditStrip,
  type ChatMessage,
  type DocSection,
  type TraceLine,
  type QcMetric,
} from "./V2Shell";

const MESSAGES: ChatMessage[] = [
  {
    side: "agent", sig: "C.", nameZh: "授信决策·辅助评估", nameEn: "Credit",
    ts: "10:11:08", ref: "四维评分", spineColor: "var(--t-credit)",
    body: <>四维评分出来了 — 经营 <b>82</b> / 偿债 <b>76</b> / 成长 <b>81</b> / 合规 <b>73</b>，综合 <b>78</b>（B+）。红线 <b>0</b> 触发，但<em>集中度</em> CR5=67.2% 触黄线，建议额度 <b>8,000 万</b>，期限 12 个月，LPR+85BP。</>,
  },
  {
    side: "user", sig: "王.", nameZh: "王哲", nameEn: "华东客户经理",
    ts: "10:12:34",
    body: <>集中度黄线不能过审贷会，先试算降一档到 <b>6,500 万</b>；另外<b>担保抵押覆盖率</b>要补进评分里。</>,
  },
  {
    side: "agent", sig: "C.", nameZh: "授信决策·辅助评估", nameEn: "Credit",
    ts: "10:13:02", ref: "rerun 评分 / 额度", spineColor: "var(--t-credit)",
    body: <>收到。试算 <b>6,500 万</b>需把流贷从 <b>5,000</b> 降 <b>4,000</b>，票据 <b>2,000→2,500</b>，覆盖率 <em>77.5% → 92.3%</em>。评分微升至 <b>80</b>，集中度降为提示级。重算约 <b>45s</b>。</>,
  },
];

const SSE_LINES: TraceLine[] = [
  { ts: "10:10:12", stgTag: "prof · 01",    stage: "ev", tx: <>✓ <b>ReportJSON 载入</b> 12 节 <span className="src">SRC agent6_ingest</span></> },
  { ts: "10:10:28", stgTag: "score · 2.1",  stage: "gn", tx: <>✓ <b>经营维度</b> 82 <span className="src">SRC op_indicators</span></> },
  { ts: "10:10:41", stgTag: "score · 2.2",  stage: "gn", tx: <>✓ <b>偿债维度</b> 76（流动比 <em>1.38</em>）<span className="src">SRC financial_analyzer</span></> },
  { ts: "10:10:54", stgTag: "redline · 3.1", stage: "au", tx: <>✓ <b>4 红线 0 触发</b>（实控连带 / 同业违约 / 司法 / 环保）</> },
  { ts: "10:11:08", stgTag: "redline · 3.2", stage: "au", typing: true, tx: <>⚠ <b>集中度黄线</b> CR5=67.2% · <em>建议人审</em></> },
];

const SECTIONS: DocSection[] = [
  {
    n: "01", name: "画像摘要", en: "Profile Summary", state: "ok", stateText: "已载入",
    body: (
      <>
        <p>苏州睿联电子股份有限公司（统一社会信用代码 91320594MA1R5KXY7B），2016 年成立，注册资本 <span className="num">5,000</span> 万元，主营精密连接器研发与制造，归属 C39 计算机通信及其他电子设备制造业。来源 = Agent6 ReportJSON · 12 节全部成稿，摘要自动引入。</p>
        <p>实际控制人陈睿联合计控制 <span className="num">80.0%</span>，历史无重大诉讼、行政处罚及征信不良。现有授信 5 家银行合计 <span className="num">1.2</span> 亿元，近 24 期零逾期、零展期、零重组。</p>
      </>
    ),
  },
  {
    n: "02", name: "四维评分", en: "Four-Dim Score", state: "live", stateText: "生成中", flag: "live",
    body: (
      <>
        <p><em>经营 82</em>：营收三年 CAGR <span className="num">23.1%</span>，2024 前三季度营收 <span className="num">2.14</span> 亿同比 <span className="num">+21.4%</span>，研发占比 <span className="num">18.3%</span>；证据锚点 = 利润表 · 研发投入表 · 主要客户合同样本。</p>
        <p><em>偿债 76</em>：资产负债率 <span className="num">52.4%</span>，流动比 <span className="num">1.38</span>，速动比 <span className="num">0.92</span>，利息保障倍数 <span className="num">6.2</span>；证据锚点 = 资产负债表 · financial_analyzer 指标输出 · 授信余额明细。</p>
        <p><em>成长 81</em>：在 Type-C / 车载高压 / BTB 三细分具备技术壁垒，5 年以上大客户占 <span className="num">4</span> 户，发明专利 <span className="num">17</span> 项；证据锚点 = 专利明细 · 客户合作年限表 · 研发路线图。</p>
        <p><em>合规 73</em>：2026-04-18《小微信贷风控新规》适用性核验通过；环保 / 社保 / 税务等级 A；但内控 A-12 条款历史抽查有一次整改记录，按模型扣 <span className="num">7</span> 分<span className="cursor">▋</span></p>
      </>
    ),
  },
  {
    n: "03", name: "红线检查", en: "Redline", state: "ok", stateText: "4/4 · 0 触发",
    body: <p>四条硬红线逐项核验：① <b>实控人连带失败</b>——陈睿联个人征信 A+ · 苏州睿联投资合伙企业可承担连带，通过；② <b>同业违约</b>——5 家在贷行近 24 期零逾期，通过；③ <b>司法涉诉</b>——天眼查 / 裁判文书网 / 人行征信三源交叉，无重大涉诉，通过；④ <b>环保处罚</b>——近 3 年零行政处罚，通过。</p>,
  },
  {
    n: "04", name: "黄线提示", en: "Yellow Line", state: "warn", stateText: "集中度触黄",
    body: <p><em>客户集中度</em>：CR5 = <span className="num">67.2%</span>，歌尔单客户占比 <span className="num">32%</span>，超模型黄线 <span className="num">30%</span>。建议单客户限额 <span className="num">4,000</span> 万元，并在授信决议中明确&ldquo;歌尔订单波动&gt;20% 触发预警复评&rdquo;条款。此项不阻断上会，但需审贷会讨论。</p>,
  },
  {
    n: "05", name: "额度建议", en: "Proposed Limit", state: "ok", stateText: "8,000 万",
    body: <p>综合授信 <span className="num">8,000</span> 万元：流动资金贷款 <span className="num">5,000</span> 万元 + 银行承兑汇票 <span className="num">2,000</span> 万元 + 票据贴现 <span className="num">1,000</span> 万元。按四维评分 B+ 与对公 A 级模型映射，额度位于模型推荐中枢（<span className="num">7,500~9,500</span> 万）偏下，留足审贷会调整空间。</p>,
  },
  {
    n: "06", name: "还款来源", en: "Repayment", state: "ok", stateText: "覆盖 2.5×",
    body: <p>主营业务月均回款 <span className="num">2,300</span> 万元，按建议额度 <span className="num">8,000</span> 万 · 1 年期滚续测算，月均本息占回款 <span className="num">40%</span>，覆盖倍数 <span className="num">2.5</span>。备用来源 = 厂房抵押 + 实控人连带 + 合伙企业连带。</p>,
  },
  {
    n: "07", name: "担保抵押", en: "Collateral", state: "ok", stateText: "覆盖 77.5%",
    body: <p>组合担保：① 苏州工业园区 A2 地块厂房抵押（<span className="num">6,800</span>㎡ · 评估价 <span className="num">6,200</span> 万）；② 实控人陈睿联个人不可撤销连带；③ 苏州睿联投资合伙企业连带。按建议额度 <span className="num">8,000</span> 万测算抵押覆盖率 <span className="num">77.5%</span>，符合对公 A 级模型 ≥70% 要求。</p>,
  },
  {
    n: "08", name: "利率建议", en: "Pricing", state: "ok", stateText: "LPR+85BP",
    body: <p>按对公 A 类常规定价，流动资金贷款 <span className="num">1</span> 年期 LPR+<span className="num">85</span>BP（当前 <span className="num">4.20%</span>）；银行承兑汇票开证费率 <span className="num">0.05%</span>/月；票据贴现按市场化定价。综合 FTP 测算行内净息差约 <span className="num">1.35%</span>，高于普惠基准 <span className="num">12</span>BP。</p>,
  },
  {
    n: "09", name: "期限建议", en: "Tenor", state: "ok", stateText: "1Y / 6M",
    body: <p>流动资金贷款 <span className="num">12</span> 个月滚续；银行承兑汇票与票据贴现 <span className="num">6</span> 个月。按应收账款 <span className="num">72</span> 天账期与存货周转 <span className="num">68</span> 天测算，经营周期对齐。</p>,
  },
  {
    n: "10", name: "条件前置", en: "Precedents", state: "ok", stateText: "2 项",
    body: <p>放款前提条件：① 同业授信备忘——建行 / 工行 / 招行 / 平安 / 中信五家现有授信行出具非排他性备忘；② 财报季报上传——每季结束后 <span className="num">30</span> 日内向主办行报送财务四表及管理报表。</p>,
  },
  {
    n: "11", name: "人审决议", en: "Human Review", state: "pend", stateText: "待审贷会", flag: "pending",
    body: <p>四维 78 分 / B+ · 红线 0 触发 · 黄线 1（集中度）。待审贷会定稿后 → 支行初审 → 分行复审 → 总行终审。</p>,
  },
  {
    n: "12", name: "案例召回", en: "Case Recall", state: "ok", stateText: "14 户",
    body: <p>近 3 年同行业（C39 精密连接器）对公 A 级客户 <span className="num">14</span> 户，平均授信额度 <span className="num">7,300</span> 万元，平均评分 <span className="num">76</span>，违约率 <span className="num">0.7%</span>，远低于全行对公 <span className="num">1.9%</span>。本案定价与额度位于区间内。</p>,
  },
];

const QC_METRICS: QcMetric[] = [
  { k: "评分置信",   v: "88",    p: "88%" },
  { k: "红线覆盖",   v: "4/4",   p: "100%" },
  { k: "证据溯源",   v: "97.4",  p: "97%" },
  { k: "数字一致",   v: "100",   p: "100%" },
  { k: "口径一致",   v: "99.2",  p: "99%" },
  { k: "案例召回",   v: "14",    p: "93%" },
  { k: "政策对齐",   v: "100",   p: "100%" },
  { k: "期限合理",   v: "95",    p: "95%" },
  { k: "利率市场化", v: "82",    p: "82%", hot: true },
];

export default function CreditV2() {
  return (
    <V2Shell
      agent="credit"
      hero={{
        eyebrowText: "CREDIT AGENT · Agent6 下游决策引擎",
        eyebrowAccent: "四维评分已落 · 集中度黄线待人审",
        heroTitle: (
          <>
            <span className="cn">苏州睿联电子</span> 综合评分 <em>B+ · 78 分</em>，建议额度 <em>8,000 万</em>。
          </>
        ),
        heroSub: (
          <>
            Agent6 ReportJSON 已接入 · 四维评分 <b>经营 / 偿债 / 成长 / 合规</b>均已落盘 · 红线 <b>0</b>/4 触发 · 集中度一项<b>触黄</b>待讨论。
            <span className="bullet" />
            <button type="button" className="pill">上审贷 ↗</button>
            <button type="button" className="pill ghost">降一档试算</button>
          </>
        ),
      }}
      apHead={{
        zh: "授信决策 · 辅助评估",
        en: "Credit Decision Assistant",
        ver: "v3.1",
        metas: [
          { k: "擅长", v: "对公 / 普惠 / 对私三板块四维评分" },
          { k: "当前", v: "评分 B+ 待审贷", state: "warn" },
          { k: "今日", v: "3 次 · 全部留痕" },
        ],
        health: "LLM 在线 · DeepSeek",
        cta: { label: "上审贷会", arrow: "↗" },
      }}
      cap={{ cn: "三阶段", em: "— Profile / Score / Redline", k: "SESSION · 20260420-1010" }}
      stages={[
        { n: "01", nm: "画像", en: "— Profile", state: "done", sub: <>ReportJSON 载入 · <b>12</b> 节全部成稿</> },
        { n: "02", nm: "评分", en: "— Score", state: "live", sub: <>四维模型 · 经营 <b>82</b> · 偿债 <b>76</b> · 成长 <b>81</b> · 合规 <b>73</b></> },
        { n: "03", nm: "红线", en: "— Redline", sub: <><b>4</b>/4 检查 · <b>0</b> 触发 · 集中度黄线建议人审</> },
      ]}
      tplTitle={{
        lbl: "选模型",
        hint: <>已选 <b>对公 A · corp-v3.1</b> · 四维 + 10 红线 · 切换会重跑评分</>,
        k: "CREDIT MODEL",
      }}
      tpls={[
        { key: "corp",   name: "对公 A 级",   tag: "Corp-A",   meta: "corp-A-v3.1 · 标准",     spec: "四维 + 10 红线 · 额度上限 1 亿", on: true },
        { key: "sme",    name: "普惠快贷",   tag: "SME",      meta: "sme-quick-v2.4",          spec: "三维 + 5 红线 · 额度上限 500 万" },
        { key: "retail", name: "对私消费",   tag: "Retail",   meta: "retail-consumer-v2.0",    spec: "纯规则 + FICO 映射" },
        { key: "supply", name: "供应链金融", tag: "SupChain", meta: "supply-chain-v1.5",       spec: "核心企业带链 + 反向保理" },
      ]}
      intake={[
        { kind: "drop", title: "来源 = Agent6 ReportJSON（苏州睿联电子 · v7.23）", sub: "已自动抄送 · 12 节全部成稿 · 可重选其他客户", btn: "重选" },
        { kind: "opt", on: true, k: "业务线", v: <>对公 Corporate</> },
        { kind: "opt", k: "模型版本", v: <>v3.1</> },
        { kind: "opt", k: "Mock 回放", v: <>关</>, toggle: true },
      ]}
      chatSlot={
        <ChatBlk
          title="对话 · 评分与试算"
          subTitle="— Decision Chat"
          kBadge="1 pending · 集中度黄线"
          messages={MESSAGES}
          seeds={[
            { q: "Q1", body: <>切<em>普惠</em>模型试</> },
            { q: "Q2", body: <>拆<em>母子额度</em></> },
            { q: "Q3", body: <>抄送<em>合规 Agent5</em></> },
          ]}
          placeholder="继续追问 · 例如：按 1 年期试算年利息总额…"
        />
      }
      docSlot={
        <>
          <SseBlk
            title={<>事件流 <em>— SSE · profile / score / redline</em></>}
            kBadge="live"
            lines={SSE_LINES}
          />
          <DocWrap
            docTitle="授信评估底稿 · 苏州睿联电子"
            docSubtitle="Decision Memo · corp-v3.1"
            metrics={[
              <>78 分</>,
              <>B+</>,
              <>红线 0/4</>,
              <span className="hot">黄线 1</span>,
              <>额度 8,000 万</>,
            ]}
            sections={SECTIONS}
          />
        </>
      }
      auditSlot={
        <AuditStrip
          verdict={{
            k: "Verdict · 总体",
            v: <>可上审贷 <em>— 红线 0 · 黄线 1</em></>,
            tip: <>四维 <b>78</b>（B+）· 红线 <b>0</b>/4 · 黄线 <b>1</b>（集中度）· 额度 <b>8,000</b> 万 · 利率 LPR+85BP · 覆盖率 <b>77.5%</b>。</>,
            ctas: [
              { label: "降一档试算" },
              { label: "上审贷会 ↗", primary: true },
            ],
          }}
          coverage={[
            { k: "评分维度", v: <>4<sub>/4</sub></> },
            { k: "置信",     v: <>88<sub>%</sub></> },
            { k: "红线触发", v: <>0<sub>项</sub></> },
          ]}
          unfilled={{
            k: "未能自动填写 · 典型 3 项",
            items: (
              <>
                <span className="tag">集中度黄线人审</span>需审贷会讨论 · <span className="tag">担保人净资产</span>需人工补 · <span className="tag">同业对标违约率</span>外部源未全量
              </>
            ),
          }}
          qc={QC_METRICS}
        />
      }
    />
  );
}
