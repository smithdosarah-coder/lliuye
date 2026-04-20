"use client";

/**
 * AlertV2 — DOM port of design_mockups/stage5/mockup-v2/alert.html.
 * Post-Loan Batch Scanner · 客户行为变化驱动 · 外 / 内 / 交叉.
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
    side: "agent", sig: "警.", nameZh: "贷中预警·批量扫描", nameEn: "Alert",
    ts: "08:01:14", ref: "批次 20260420", spineColor: "var(--t-alert)",
    body: <>今早批次 <b>100</b> 户扫完 — 外扫 <b>24</b> 条触发、内核 <b>14</b> 条触发，双路交叉命中 <b>10</b> 户。红 <b>3</b>：<em>苏州华瑞</em>（司法查封 + 对公账户大额划出）、<em>无锡联顺</em>（工商股权冻结 + 征信展期）、<em>常州大卫</em>（实控人涉诉 + 舆情扩散）。</>,
  },
  {
    side: "user", sig: "王.", nameZh: "王哲", nameEn: "华东客户经理",
    ts: "08:04:22",
    body: <><b>3 红</b>直接挂停新放款 + 派合规 Agent5 复核；黄线里头<em>常熟金和</em>是我客户，我去电话核实。</>,
  },
  {
    side: "agent", sig: "警.", nameZh: "贷中预警·批量扫描", nameEn: "Alert",
    ts: "08:04:58", ref: "派单 · 抄送", spineColor: "var(--t-alert)",
    body: <>收到。3 红 <em>熔断清单</em>已生成 · 已抄送合规 Agent5 + 反洗钱团队 · 常熟金和<em>待你回执</em>暂留黄榜。扫描报表 <b>10:30</b> 前推你。</>,
  },
];

const SSE_LINES: TraceLine[] = [
  { ts: "08:00:12", stgTag: "ext · 01",    stage: "ev", tx: <>✓ <b>工商</b> 8 变更 <span className="src">SRC 国家企业信用</span></> },
  { ts: "08:00:31", stgTag: "ext · 02",    stage: "ev", tx: <>✓ <b>诉讼</b> 4 新增 <span className="src">SRC 裁判文书</span></> },
  { ts: "08:00:45", stgTag: "ext · 03",    stage: "ev", tx: <>✓ <b>舆情</b> 12 负面 <span className="src">SRC web_access</span></> },
  { ts: "08:01:02", stgTag: "int · 1.2",   stage: "gn", tx: <>✓ <b>交易异常</b> 6 <span className="src">SRC core_banking</span></> },
  { ts: "08:01:14", stgTag: "cross · 2.1", stage: "au", typing: true, tx: <>⚠ <b>10 户双命中</b> <em>3 红熔断建议</em></> },
];

const SECTIONS: DocSection[] = [
  {
    n: "01", name: "红线熔断", en: "Red — Circuit-Break", state: "warn", stateText: "3 户 · 建议停贷",
    body: (
      <>
        <p><b>① 苏州华瑞精密制造</b>　信用代码 91320594MA1K7R2X5Y · 余额 <span className="num">1,820</span> 万 · 触发规则 <span className="tag">EXT-02 司法查封</span> + <span className="tag">INT-1.2 对公账户大额划出</span> · 外扫证据：苏州工业园区法院 <em>（2026）苏05民初3127号</em>查封不动产；内核证据：04-18 账户单日净流出 <em>1,240 万</em>、流向关联方。<b>建议</b>：停新放款 + 提前回收 + 48h 内抵押物复查。</p>
        <p><b>② 无锡联顺电子</b>　信用代码 91320213MA20N8P5A · 余额 <span className="num">2,450</span> 万 · 触发规则 <span className="tag">EXT-01 股权冻结</span> + <span className="tag">INT-2.1 征信展期</span> · 外扫证据：无锡中院 04-17 冻结大股东持股 <em>45%</em>；内核证据：04-15 他行展期 <em>6 个月</em>、征信查询 <em>5 次/月</em>。<b>建议</b>：停新放款 + 要求补充保证金。</p>
        <p><b>③ 常州大卫塑胶</b>　信用代码 91320411MA1W2T6H3Z · 余额 <span className="num">960</span> 万 · 触发规则 <span className="tag">EXT-02 实控人涉诉</span> + <span className="tag">EXT-03 舆情扩散</span> + <span className="tag">INT-3.1 账户异常</span> · 外扫证据：实控人涉非吸案、微博话题阅读 <em>120 万</em>；内核证据：04-19 账户单日 <em>3 次</em>大额转出。<b>建议</b>：停新放款 + 启动联合催收。</p>
      </>
    ),
  },
  {
    n: "02", name: "黄线关注", en: "Yellow — Watchlist", state: "warn", stateText: "7 户 · 人工复核",
    body: (
      <>
        <p>7 户触发<em>单路命中</em>或<em>轻度双命中</em>，暂不熔断但需客户经理 48h 内回执：</p>
        <p>① <b>常熟金和机械</b>　外：工商变更经营范围 · 内：正常 · 余额 <span className="num">580</span> 万 · 客户经理 王哲 · 动作 电话核实　② <b>昆山永顺包装</b>　外：舆情负面 2 条 · 内：交易笔数环比 -38% · 余额 <span className="num">320</span> 万 · 李娜 · 动作 上门走访　③ <b>太仓宇通五金</b>　外：诉讼被告 · 内：正常 · 余额 <span className="num">710</span> 万 · 陈晓 · 动作 复查合同　④ <b>南通海丰塑料</b>　外：舆情 · 内：征信查询增多 · 余额 <span className="num">420</span> 万 · 张磊 · 动作 征信核查　⑤ <b>扬州德兴机电</b>　外：工商 · 内：账户余额骤降 · 余额 <span className="num">680</span> 万 · 李娜 · 动作 账户对账　⑥ <b>镇江合隆五金</b>　外：诉讼原告 · 内：正常 · 余额 <span className="num">260</span> 万 · 王哲 · 动作 情况说明　⑦ <b>徐州盛达铸造</b>　外：舆情 · 内：交易异常 1 次 · 余额 <span className="num">890</span> 万 · 陈晓 · 动作 48h 内回执</p>
      </>
    ),
  },
  {
    n: "03", name: "绿线正常", en: "Green — Normal", state: "ok", stateText: "90 户 · 月度再扫",
    body: <p>其余 <span className="num">90</span> 户本批次<em>双路均未命中</em>，内部交易 / 征信 / 账户三维指标与历史基线偏差 &lt; <span className="num">1.5</span> 倍标准差，外部工商 / 诉讼 / 舆情无新增负面信号。合计余额 <span className="num">2.38</span> 亿元，平均账龄 <span className="num">14.2</span> 月，加权风险评级 <em>B+</em>。按既定节奏<b>每月 20 日</b>再扫，异常触发即时提级。</p>,
  },
  {
    n: "04", name: "外扫规则命中", en: "External Rules", state: "ok", stateText: "24 条",
    body: (
      <>
        <p><b>工商变更 8 条</b>　股权冻结 <span className="num">2</span>（无锡联顺、宿迁瑞达）· 经营范围变更 <span className="num">3</span>（常熟金和、盐城宏图、淮安联兴）· 法人变更 <span className="num">2</span>（连云港达成、徐州明辉）· 注册资本减资 <span className="num">1</span>（泰州鼎新）。</p>
        <p><b>诉讼新增 4 条</b>　司法查封 <span className="num">1</span>（苏州华瑞）· 被告立案 <span className="num">2</span>（太仓宇通、镇江合隆）· 实控人涉诉 <span className="num">1</span>（常州大卫）。</p>
        <p><b>舆情负面 12 条</b>　微博 <span className="num">5</span> · 抖音 <span className="num">3</span> · 本地门户 <span className="num">2</span> · 知乎问答 <span className="num">2</span> · 涉及企业 <span className="num">6</span> 家，<em>常州大卫</em>话题阅读量最大。</p>
      </>
    ),
  },
  {
    n: "05", name: "内核规则命中", en: "Internal Rules", state: "ok", stateText: "14 条",
    body: (
      <>
        <p><b>交易异常 6 条</b>　单日净流出 &gt; 月均 3σ（苏州华瑞、常州大卫）· 交易笔数环比 -30% 以上（昆山永顺、徐州盛达）· 关联方占比突升（无锡联顺、扬州德兴）。</p>
        <p><b>征信变动 5 条</b>　他行展期（无锡联顺）· 查询频次突增（南通海丰）· 担保人新增对外担保（另 3 户）。</p>
        <p><b>账户风险 3 条</b>　余额骤降 &gt; 50%（扬州德兴）· 账户冻结预警（常州大卫）· 保证金不足（另 1 户）。</p>
      </>
    ),
  },
  {
    n: "06", name: "双路交叉", en: "Crossmatch", state: "warn", stateText: "10 户 · 红 3 / 黄 7",
    body: (
      <>
        <p>外扫 <span className="num">24</span> 条触发 × 内核 <span className="num">14</span> 条触发 去重后，<b>双路命中矩阵</b> <span className="num">10</span> 户——</p>
        <p><b>红线（双强命中）3 户</b>　苏州华瑞（司法查封 × 账户大额划出）· 无锡联顺（股权冻结 × 征信展期）· 常州大卫（涉诉 × 舆情 × 账户异常）。</p>
        <p><b>黄线（双弱命中 / 强弱组合）7 户</b>　见 02 节清单。<em>交叉命中率</em> <span className="num">10%</span>（10/100），高于季度基线 <span className="num">6.8%</span>，本批次风险面显著抬升。</p>
      </>
    ),
  },
  {
    n: "07", name: "处置建议", en: "Actions", state: "ok", stateText: "3 档",
    body: (
      <>
        <p><b>红 · 熔断档</b>　停新放款 + 提前回收 + 抵押物复查 + 派合规 Agent5 介入 · <span className="num">24h</span> 内闭环。</p>
        <p><b>黄 · 复核档</b>　客户经理 48h 回执 + 视情况走访 / 账户对账 / 征信核查 · <span className="num">7</span> 日内结论。</p>
        <p><b>绿 · 再扫档</b>　纳入下月 20 日批次 · 异常触发即时提级，不走人工。</p>
      </>
    ),
  },
  {
    n: "08", name: "抄送清单", en: "CC Routing", state: "ok", stateText: "4 方",
    body: <p>① <b>合规 Agent5</b>　接收 3 红熔断清单，启动制度冲突比对 · ② <b>反洗钱团队</b>　接收账户大额划出明细（苏州华瑞、常州大卫）· ③ <b>分行风险部</b>　接收批次全量报告，周会议题 · ④ <b>客户经理</b>　王哲 / 李娜 / 陈晓 / 张磊 / 李磊 按客户分派。</p>,
  },
  {
    n: "09", name: "熔断条件", en: "Circuit Rules", state: "ok", stateText: "阈值固化",
    body: <p>熔断触发条件 =（外扫规则命中 ∧ 内核规则命中）∧ <em>风险评级 ≥ D</em>。三个要素同时成立即生成熔断建议。本批次 3 红均满足：苏州华瑞 <em>D+</em> · 无锡联顺 <em>D</em> · 常州大卫 <em>D-</em>。熔断执行需支行授权通过。</p>,
  },
  {
    n: "10", name: "复核路径", en: "Review SLA", state: "ok", stateText: "24 / 48 / 72h",
    body: <p>客户经理回执 <span className="num">24h</span> · 合规 Agent5 裁定 <span className="num">48h</span> · 分行风险部落章 <span className="num">72h</span>。超时自动提级至分行行长周例会，逾时客户经理绩效扣分，合规逾时由行监察室接管。</p>,
  },
  {
    n: "11", name: "人审决议", en: "Approval", state: "pend", stateText: "3 红 · 待人审", flag: "pending",
    body: <p>3 红熔断建议需人审签章——支行信贷部初审 → 分行风险部复审 → 分行行长终签。预计链路 <span className="num">72</span> 小时内闭环。常熟金和黄榜等王哲回执后再定档。</p>,
  },
  {
    n: "12", name: "扫描溯源", en: "Trace", state: "ok", stateText: "100/100 · 72s",
    body: <p>本批次覆盖 <span className="num">100</span> 户，外扫 <span className="num">24</span> 条、内核 <span className="num">14</span> 条，去重后双路命中 <span className="num">10</span> 户，总耗时 <span className="num">72</span> 秒。外扫源 <em>国家企业信用 / 裁判文书 / web_access</em>；内核源 <em>core_banking / 征信系统 / 账户主库</em>。全部事件留痕可追溯至 evidence_id。</p>,
  },
];

const QC_METRICS: QcMetric[] = [
  { k: "扫描覆盖",    v: "100",   p: "100%" },
  { k: "双源一致",    v: "99.2",  p: "99%" },
  { k: "规则命中率",  v: "10",    p: "10%" },
  { k: "误报率",      v: "3.1",   p: "3%", hot: true },
  { k: "漏报率",      v: "0.8",   p: "1%" },
  { k: "证据齐",      v: "100",   p: "100%" },
  { k: "时效",        v: "72s",   p: "96%" },
  { k: "派单覆盖",    v: "10/10", p: "100%" },
  { k: "复核回执",    v: "2/10",  p: "20%", hot: true },
];

export default function AlertV2() {
  return (
    <V2Shell
      agent="alert"
      hero={{
        eyebrowText: "ALERT AGENT · 客户行为变化驱动",
        eyebrowAccent: "小微在贷 · 100 户已扫完",
        heroTitle: (
          <>
            <span className="cn">今早批次</span> <em>3 红 7 黄</em>，小微在贷 <em>100 户</em>已扫完。
          </>
        ),
        heroSub: (
          <>
            外部扫 <b>工商 / 诉讼 / 舆情</b> 3 源，内部扫 <b>交易 / 征信 / 账户</b> 3 维，<b>双路交叉</b>命中即告警。<b>3 红</b>建议触发熔断。
            <span className="bullet" />
            <button type="button" className="pill">派合规复核 ↗</button>
            <button type="button" className="pill ghost">仅看红榜</button>
          </>
        ),
      }}
      apHead={{
        zh: "贷中预警 · 批量扫描",
        en: "Post-Loan Batch Scanner",
        ver: "v3.1",
        metas: [
          { k: "擅长", v: "知识库驱动的外/内双路扫描" },
          { k: "当前", v: "3 红 7 黄待处置", state: "warn" },
          { k: "今日", v: "1 批次 100 户" },
        ],
        health: "LLM 在线 · DeepSeek",
        cta: { label: "导出榜单", arrow: "↗" },
      }}
      cap={{ cn: "三阶段", em: "— External / Internal / Crossmatch", k: "SESSION · 20260420-0800" }}
      stages={[
        { n: "01", nm: "外扫", en: "— External", state: "done", sub: <>工商变更 <b>8</b> · 诉讼新增 <b>4</b> · 舆情负面 <b>12</b></> },
        { n: "02", nm: "内核", en: "— Internal", state: "done", sub: <>交易异常 <b>6</b> · 征信变动 <b>5</b> · 账户风险 <b>3</b></> },
        { n: "03", nm: "交叉", en: "— Crossmatch", state: "live", sub: <>双路命中 <b>10</b> 户 · <b>红 3</b> / <b>黄 7</b> / <b>绿 90</b></> },
      ]}
      tplTitle={{
        lbl: "选规则库",
        hint: <>已选 <b>小微在贷 · kb-micro-v3.1</b> · 24 规则 · 每日 08:00 批次 · 切换需重扫</>,
        k: "SCAN KNOWLEDGE BASE",
      }}
      tpls={[
        { key: "micro",  name: "小微在贷",   tag: "Micro",  meta: "kb-micro-v3.1 · 标准",        spec: "规则 24 · 100 户", on: true },
        { key: "sme",    name: "对公在贷",   tag: "SME",    meta: "kb-sme-v2.4",                  spec: "规则 36 · 42 户" },
        { key: "supply", name: "供应链在贷", tag: "Supply", meta: "kb-supply-v1.8 · 核心企业链路", spec: "规则 18" },
        { key: "auto",   name: "汽车金融",   tag: "Auto",   meta: "kb-auto-v1.0",                 spec: "抵押物动态 + 交易异常" },
      ]}
      intake={[
        { kind: "drop", title: "在贷客户池 · 从「小微信贷 2026 Q1」池（100 户）自动载入", sub: "每日 08:00 批次拉取 · 支持上传新池 .csv / .xlsx · 单份 ≤ 20MB", btn: "上传新池" },
        { kind: "opt", on: true, k: "扫描频率", v: <>每日 08:00</> },
        { kind: "opt", k: "时间窗", v: <>今日</> },
        { kind: "opt", k: "Mock 回放", v: <>关</>, toggle: true },
      ]}
      chatSlot={
        <ChatBlk
          title="对话 · 处置流转"
          subTitle="— Triage Chat"
          kBadge="3 红 · 待熔断"
          messages={MESSAGES}
          seeds={[
            { q: "Q1", body: <>复盘<em>外扫舆情源</em>权重</> },
            { q: "Q2", body: <>加一条<em>供应链断链</em>规则</> },
            { q: "Q3", body: <>抄送<em>合规 Agent5</em></> },
          ]}
          placeholder="继续追问 · 例如：扩大时间窗到近 7 日再扫一次…"
        />
      }
      docSlot={
        <>
          <SseBlk
            title={<>事件流 <em>— SSE · external / internal / crossmatch</em></>}
            kBadge="live"
            lines={SSE_LINES}
          />
          <DocWrap
            docTitle="今日预警榜单 · 100 户小微在贷 · 2026-04-20"
            docSubtitle="Alert Board · kb-micro-v3.1"
            metrics={[
              <>3 红</>,
              <>7 黄</>,
              <>90 绿</>,
              <span className="hot">双路命中 10</span>,
            ]}
            sections={SECTIONS}
          />
        </>
      }
      auditSlot={
        <AuditStrip
          verdict={{
            k: "Verdict · 总体",
            v: <>可触发熔断 <em>— 3 红建议停贷</em></>,
            tip: <>扫 <b>100</b> 户耗时 <b>72s</b> · 双路命中 <b>10</b> · <b>3</b> 红 <b>7</b> 黄 · 派合规 Agent5 · 抄送分行。</>,
            ctas: [
              { label: "仅看红榜" },
              { label: "派合规复核 ↗", primary: true },
            ],
          }}
          coverage={[
            { k: "扫描覆盖",   v: <>100<sub>/100</sub></> },
            { k: "双路命中率", v: <>10<sub>%</sub></> },
            { k: "红线",       v: <>3<sub>户</sub></>, hot: true },
          ]}
          unfilled={{
            k: "未能自动填写 · 待补 3 项",
            items: (
              <>
                <span className="tag">常熟金和人外回执</span>待客户经理 · <span className="tag">供应链断链规则</span>规则库缺项 · <span className="tag">舆情源权重校准</span>待本周策略会
              </>
            ),
          }}
          qc={QC_METRICS}
        />
      }
    />
  );
}
