"use client";

/**
 * RiskctrlV2 — DOM port of design_mockups/stage5/mockup-v2/riskctrl.html.
 * DSL Strategy Author · Gen / Backtest / Metrics 三阶段.
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
    side: "agent", sig: "风.", nameZh: "风控策略·DSL", nameEn: "RiskCtrl",
    ts: "11:09:48", ref: "DSL 15 / 回测", spineColor: "var(--t-riskctrl)",
    body: <>DSL 已生成 <b>15</b> 条 — 回测 <b>1.2 万</b>样本 24 月：KS <b>0.38</b>（达标）AUC <b>0.76</b>（达标）通过率 <b>78%</b>（<em>低 5pp</em>）。瓶颈在 <em>R-07 流水真实性</em>门槛卡太严，拒绝掉 6% 优质样本。建议阈值从 <b>0.85</b> 松到 <b>0.78</b>。</>,
  },
  {
    side: "user", sig: "王.", nameZh: "王哲", nameEn: "华东客户经理",
    ts: "11:10:22",
    body: <>调松 R-07 + 再加一条<em>近 12 月税票同比增长 ≥ -10%</em> 的软约束，重跑给我。</>,
  },
  {
    side: "agent", sig: "风.", nameZh: "风控策略·DSL", nameEn: "RiskCtrl",
    ts: "11:10:46", ref: "rerun R-07 / R-16", spineColor: "var(--t-riskctrl)",
    body: <>收到。R-07 <b>0.85 → 0.78</b> + 新增 R-16 税票同比 <em>软约束（权重 0.3）</em>。重跑约 <b>45s</b> · 预估 KS <b>0.36</b> 通过率 <b>82%</b>，<em>达标</em>。若通过 <em>你一键上线灰度 10%</em>。</>,
  },
];

const SSE_LINES: TraceLine[] = [
  { ts: "11:08:12", stgTag: "gen · 01",    stage: "ev", tx: <>✓ <b>策略文本</b> NLU 解析 <span className="src">SRC 诉求</span></> },
  { ts: "11:08:28", stgTag: "gen · 02",    stage: "ev", tx: <>✓ <b>DSL 15 条</b> 落盘 <span className="src">SRC dsl_gen_v3.1</span></> },
  { ts: "11:08:47", stgTag: "bt · 1.2",    stage: "gn", tx: <>✓ <b>样本 1.2 万</b> 载入（电子制造 Q1-Q4）<span className="src">sample_pool</span></> },
  { ts: "11:09:35", stgTag: "bt · 1.3",    stage: "gn", tx: <>✓ <b>回测 24 月</b> 耗时 <em>48s</em> <span className="src">backtest_engine</span></> },
  { ts: "11:09:48", stgTag: "metric · 2.1", stage: "gn", typing: true, tx: <>⚠ KS <em>0.38</em> AUC <em>0.76</em> 通过率 <em>78%</em> · <span className="bad">通过率低 5pp</span></> },
];

const SECTIONS: DocSection[] = [
  {
    n: "01", name: "策略诉求", en: "Strategy Brief", state: "ok", stateText: "已解析",
    body: (
      <>
        <p>原始诉求（自然语言）：<em>电子制造小微 500 万以下 建议通过率 ≥ 80% KS ≥ 0.35</em>。适用板块：对公 · 普惠小微；业务场景：流动资金贷款、票据贴现。</p>
        <p>NLU 三段式解析——<b>目标</b>：电子制造业小微法人客户 · 授信额度 ≤ <span className="num">500</span> 万；<b>约束</b>：通过率红线 ≥ <span className="num">80%</span>、区分度 KS ≥ <span className="num">0.35</span>；<b>红线</b>：关联交易比例 ≤ <span className="num">30%</span>、实控人征信无 M2+。</p>
      </>
    ),
  },
  {
    n: "02", name: "DSL 规则总览", en: "Rule Book", state: "ok", stateText: "15/15",
    body: (
      <>
        <p>共 <span className="num">15</span> 条规则落盘。维度分布：<em>财务健康度 6 条</em>（R-01~R-06）、<em>流水与税票 4 条</em>（R-07~R-10）、<em>上下游与集中度 3 条</em>（R-11~R-13）、<em>实控人与合规 2 条</em>（R-14~R-15）。</p>
        <p>权重分布：硬约束 <span className="num">12</span> 条（权重 1.0）、软约束 <span className="num">3</span> 条（权重 0.3~0.5）。命中率 Top3：R-03 资产负债率（<span className="num">22%</span>）、R-07 流水真实性（<span className="num">38%</span>）、R-11 供应商集中度（<span className="num">14%</span>）。</p>
      </>
    ),
  },
  {
    n: "03", name: "R-07 流水真实性", en: "Rule R-07 Tuning", state: "warn", stateText: "阈值偏严",
    body: (
      <>
        <p>R-07 规则：近 12 月银行流水日均余额 / 申报营收 ≥ <span className="num">0.85</span>（硬约束）。当前阈值下拒件率 <span className="num">38%</span>，但回溯优质样本（前 12 月无逾期 + 税票达标）被拒率 <span className="num">6%</span>，<em>存在误杀</em>。</p>
        <p>建议阈值松到 <span className="num">0.78</span>——预估通过率提升 <span className="num">4pp</span>，KS 回落 <span className="num">0.02</span>（仍达标）。替代方案：R-07 + 新增 R-16 税票同比软约束（权重 0.3），组合后效果更稳。</p>
      </>
    ),
  },
  {
    n: "04", name: "样本分布", en: "Sample Mix", state: "ok", stateText: "1.2 万",
    body: (
      <>
        <p>样本池：电子制造板块 2022 Q1 ~ 2023 Q4，共 <span className="num">12,000</span> 条。分类：<em>优质 6,000</em>（近 24 月无逾期 + 税票达标）、<em>正常 4,000</em>（偶有短期逾期 ≤ 7 天）、<em>不良 2,000</em>（M2+ 或司法风险）。</p>
        <p>行业覆盖：连接器 <span className="num">22%</span>、PCB <span className="num">18%</span>、显示模组 <span className="num">14%</span>、电池配件 <span className="num">12%</span>、其他电子元件 <span className="num">34%</span>。</p>
      </>
    ),
  },
  {
    n: "05", name: "KS 曲线", en: "KS Curve", state: "ok", stateText: "0.38",
    body: (
      <>
        <p>整体 KS 值 <span className="num">0.38</span>，分箱峰值出现在 <em>第 6 分箱</em>（累计坏样本占比 71% vs 累计好样本占比 33%）。达标红线 ≥ <span className="num">0.35</span>，<em>超标 0.03</em>。分箱稳定性 PSI <span className="num">0.08</span>（&lt; 0.1 为稳定）。</p>
        <p>可视代偿：若 R-07 调松后 KS 回落至 <span className="num">0.36</span>，仍在安全带内；若继续下探至 &lt; <span className="num">0.35</span>，自动触发策略回滚。</p>
      </>
    ),
  },
  {
    n: "06", name: "AUC / ROC", en: "AUC", state: "ok", stateText: "0.76",
    body: (
      <>
        <p>AUC 值 <span className="num">0.76</span>，达标红线 ≥ <span className="num">0.72</span>。ROC 曲线拐点出现在 FPR <span className="num">22%</span> / TPR <span className="num">81%</span>，分类器区分能力良好。</p>
        <p>与基线模型（dsl-corp-v2.4）对比：AUC 提升 <span className="num">0.04</span>，主要贡献项 R-11 供应商集中度（+<span className="num">0.02</span>）+ R-14 实控人征信（+<span className="num">0.02</span>）。</p>
      </>
    ),
  },
  {
    n: "07", name: "通过率分布", en: "Approval Rate", state: "warn", stateText: "78% · 低红线 5pp",
    body: (
      <>
        <p>整体通过率 <span className="num">78%</span>，<em>低于红线 80% 共 5pp</em>。拆分：优质样本通过率 <span className="num">94%</span>（达标）、正常样本通过率 <span className="num">71%</span>（偏低）、不良样本拒绝率 <span className="num">88%</span>（达标）。</p>
        <p>通过率缺口主要来自正常样本——被 R-07 / R-11 双约束夹杀。调松 R-07 + 加 R-16 软约束后，预估整体通过率 <span className="num">82%</span>。</p>
      </>
    ),
  },
  {
    n: "08", name: "冠军-挑战", en: "Champion vs Challenger", state: "ok", stateText: "v3.1 vs v2.4",
    body: (
      <>
        <p>冠军 <em>v3.1</em>（当前候选）vs 挑战者 <em>v2.4</em>（在线基线）：KS <span className="num">+0.04</span>、AUC <span className="num">+0.04</span>、通过率 <span className="num">-3pp</span>、坏账率 <span className="num">-1.2pp</span>。</p>
        <p>决策建议：v3.1 在区分度上优势明显，但通过率不达标；待本轮 R-07 调优后形成 v3.2，再做冠军-挑战 A/B 灰度 10% 3 周。</p>
      </>
    ),
  },
  {
    n: "09", name: "拒件原因", en: "Rejection Reasons", state: "ok", stateText: "Top 5",
    body: (
      <>
        <p>拒件原因前 5：<em>R-07 流水真实性 38%</em>、<em>R-03 资产负债率 22%</em>、<em>R-11 供应商集中度 14%</em>、<em>R-14 实控人征信 9%</em>、<em>其他 17%</em>。</p>
        <p>R-07 占比最高且回溯误杀率高，为本轮调优优先项。R-03 分布相对合理；R-11 小微样本天然集中度高，暂不调。</p>
      </>
    ),
  },
  {
    n: "10", name: "建议动作", en: "Action Plan", state: "ok", stateText: "3 项",
    body: (
      <>
        <p><em>① R-07 阈值</em> 0.85 → 0.78；<em>② 新增 R-16</em> 近 12 月税票同比增长 ≥ -10%（权重 0.3 软约束）；<em>③ 灰度</em> 10% 客流、3 周观察、KS/通过率/坏账率三指标日看板。</p>
        <p>预估：KS <span className="num">0.36</span>、AUC <span className="num">0.75</span>、通过率 <span className="num">82%</span>、坏账率 <span className="num">+0.3pp</span>（可接受区间）。</p>
      </>
    ),
  },
  {
    n: "11", name: "人审决议", en: "Approval", state: "pend", stateText: "策略评审会", flag: "pending",
    body: <p>待策略评审会定稿后 → 上线灰度 10% → 3 周观察 → 全量上线 / 回滚决策。评审人：风控总监、数据科学主管、合规代表。</p>,
  },
  {
    n: "12", name: "证据链", en: "Evidence", state: "ok", stateText: "全链留痕",
    body: <p>样本 SRC：<em>电子制造 Q1-Q4 · 1.2 万条</em>；DSL 版本 diff：<em>dsl-corp-v2.4 → v3.1</em> 增减规则清单；指标快照：<em>KS/AUC/通过率/分箱 PSI</em> JSON 快照落 OSS；回测复现：<em>seed 固定 + 容器镜像哈希</em>。</p>,
  },
];

const QC_METRICS: QcMetric[] = [
  { k: "KS 达标",     v: "0.38", p: "100%" },
  { k: "AUC 达标",    v: "0.76", p: "100%" },
  { k: "通过率达标",  v: "78",   p: "78%", hot: true },
  { k: "稳定性 PSI",  v: "0.08", p: "92%" },
  { k: "样本代表性",  v: "94",   p: "94%" },
  { k: "特征漂移",    v: "0.06", p: "94%" },
  { k: "回测复现",    v: "100",  p: "100%" },
  { k: "政策对齐",    v: "98",   p: "98%" },
  { k: "上线前审批",  v: "待",   p: "0%", hot: true },
];

export default function RiskctrlV2() {
  return (
    <V2Shell
      agent="riskctrl"
      hero={{
        eyebrowText: "RISKCTRL AGENT · DSL + 回测双轨",
        eyebrowAccent: "通过率低于红线 5pp",
        heroTitle: (
          <>
            <span className="cn">电子制造信贷</span> DSL <em>15 条</em> · <em>KS 0.38</em> · 通过率 <em>78%</em>。
          </>
        ),
        heroSub: (
          <>
            策略诉求 <b>电子制造业小微</b> · 样本 <b>1.2 万</b> 24 月 · DSL 规则 <b>15</b> 条 · 回测 KS <b>0.38</b> AUC <b>0.76</b>。通过率低于红线 <b>5pp</b>，建议放宽后重跑。
            <span className="bullet" />
            <button type="button" className="pill">上线灰度 ↗</button>
            <button type="button" className="pill ghost">调松重跑</button>
          </>
        ),
      }}
      apHead={{
        zh: "风控策略 · DSL 生成",
        en: "DSL Strategy Author",
        ver: "v3.1",
        metas: [
          { k: "擅长", v: "自然语言→DSL 规则 + 回测闭环" },
          { k: "当前", v: "KS 0.38 通过率 78%", state: "warn" },
          { k: "今日", v: "2 轮策略 · 全部留痕" },
        ],
        health: "LLM 在线 · DeepSeek",
        cta: { label: "上线灰度", arrow: "↗" },
      }}
      cap={{ cn: "三阶段", em: "— Gen / Backtest / Metrics", k: "SESSION · 20260420-1108" }}
      stages={[
        { n: "01", nm: "生成", en: "— Gen", state: "done", sub: <>策略诉求解析 · 规则 <b>15</b> 条落 DSL</> },
        { n: "02", nm: "回测", en: "— Backtest", state: "done", sub: <><b>1.2</b> 万样本 · <b>24</b> 月窗 · 耗时 <b>48</b> 秒</> },
        { n: "03", nm: "指标", en: "— Metrics", state: "live", sub: <>KS <b>0.38</b> · AUC <b>0.76</b> · 通过率 <b>78%</b> · 通过率<em>低 5pp</em></> },
      ]}
      tplTitle={{
        lbl: "选策略",
        hint: <>已选 <b>对公策略 · dsl-corp-v3.1</b> · KS ≥ 0.35 · 通过率 ≥ 80% · 切换会重跑回测</>,
        k: "DSL TEMPLATE",
      }}
      tpls={[
        { key: "corp",   name: "对公策略",   tag: "Corp",   meta: "dsl-corp-v3.1 · 15 规则", spec: "模板化 · KS ≥ 0.35 · 通过率 ≥ 80%", on: true },
        { key: "sme",    name: "普惠策略",   tag: "SME",    meta: "dsl-sme-v2.4 · 12 规则",  spec: "小微 · 通过率 ≥ 85%" },
        { key: "retail", name: "对私策略",   tag: "Retail", meta: "dsl-retail-v2.0",         spec: "FICO 映射 · 个贷" },
        { key: "supply", name: "供应链策略", tag: "Supply", meta: "dsl-supply-v1.5",         spec: "核心企业带链 · N+1 授信" },
      ]}
      intake={[
        { kind: "drop", title: "策略诉求：电子制造小微 500 万以下 通过率 ≥ 80% KS ≥ 0.35", sub: "自然语言输入 · 支持目标 / 约束 / 红线三段式", btn: "编辑" },
        { kind: "opt", on: true, k: "样本池", v: <>电子制造 Q1-Q4 · 1.2 万</> },
        { kind: "opt", k: "回测窗", v: <>24 月</> },
        { kind: "opt", k: "Mock 回放", v: <>关</>, toggle: true },
      ]}
      chatSlot={
        <ChatBlk
          title="对话 · 策略调优"
          subTitle="— Strategy Chat"
          kBadge="1 pending · R-07"
          messages={MESSAGES}
          seeds={[
            { q: "Q1", body: <>看<em>R-07 拒件案例</em></> },
            { q: "Q2", body: <>生成<em>冠军挑战</em>组</> },
            { q: "Q3", body: <>抄送<em>合规 Agent5</em></> },
          ]}
          placeholder="继续追问 · 例如：把通过率红线从 80% 下调到 78% 再跑…"
        />
      }
      docSlot={
        <>
          <SseBlk
            title={<>事件流 <em>— SSE · evidence / grounded / audit</em></>}
            kBadge="live"
            lines={SSE_LINES}
          />
          <DocWrap
            docTitle="DSL 策略底稿 · 电子制造小微 · Q1-Q4 回测"
            docSubtitle="Strategy Book · dsl-corp-v3.1"
            metrics={[
              <>15 规则</>,
              <>KS 0.38</>,
              <>AUC 0.76</>,
              <span className="hot">通过率 78%</span>,
              <>不达标 1/3</>,
            ]}
            sections={SECTIONS}
          />
        </>
      }
      auditSlot={
        <AuditStrip
          verdict={{
            k: "Verdict · 总体",
            v: <>调松重跑再上灰度 <em>— 通过率 5pp 缺口</em></>,
            tip: <>KS <b>0.38</b> ✓ · AUC <b>0.76</b> ✓ · 通过率 <b>78%</b> 低于红线 <b>5pp</b>。建议 R-07 松一档 + R-16 软约束，预估通过率 <b>82%</b>。</>,
            ctas: [
              { label: "调松重跑" },
              { label: "上线灰度 ↗", primary: true },
            ],
          }}
          coverage={[
            { k: "DSL 规则", v: <>15<sub>条</sub></> },
            { k: "达标",     v: <>2<sub>/3</sub></>, hot: true },
            { k: "样本",     v: <>1.2<sub>万</sub></> },
          ]}
          unfilled={{
            k: "待补动作 · 典型 3 项",
            items: (
              <>
                <span className="tag">R-07 拒件样本复核</span>需人工复核 · <span className="tag">冠军挑战 A/B 架</span>评审会后搭 · <span className="tag">灰度监控看板</span>上线前建
              </>
            ),
          }}
          qc={QC_METRICS}
        />
      }
    />
  );
}
