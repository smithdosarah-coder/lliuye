"use client";

/**
 * ReportV2 — DOM-aligned port of design_mockups/stage5/mockup-v2/report.html.
 * Structure: .ws-v2 > hero + agent-bar + .ap card (head / cap / stage-flow / tpl-strip /
 * intake-strip / main-board[chat-col + doc-col] / audit-strip).
 *
 * Content defaults mirror the 2026-04-20 mockup (苏州睿联电子 / corp-v7.23). SSE event
 * stream wired to streamReportFill via withFallback (W1 origin commit 8bdafce/a147227)
 * with /mock/report_fill_mock.json fallback on 2s timeout.
 */

import { useEffect, useState } from "react";
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
import { streamReportFill } from "@/lib/api";
import { withFallback } from "@/lib/fallback";
import type { ReportEvent } from "@/lib/credit-types";

const MESSAGES: ChatMessage[] = [
  {
    side: "agent",
    sig: "R.",
    nameZh: "信贷报告·生成",
    nameEn: "Report",
    ts: "10:31:04",
    ref: "3.4 节",
    spineColor: "var(--t-report)",
    body: (
      <>
        已写到 <b>3.4 节 主营业务与上下游</b>，卡在 <em>行业景气度口径</em>：企业材料里没有同期行业增速数据。我暂用 <b>Wind · 连接器</b> 近 4 季度均值 <b>11.8%</b> 占位，是否继续？或你给一个权威来源？
      </>
    ),
  },
  {
    side: "user",
    sig: "王.",
    nameZh: "王哲",
    nameEn: "华东客户经理",
    ts: "10:31:42",
    body: (
      <>
        行业口径换成 <em>Wind 连接器行业</em>，但补一句——我们客户集中度对歌尔 32%，要给一段集中度风险意见到 <code>3.4 节</code>结尾。
      </>
    ),
  },
  {
    side: "agent",
    sig: "R.",
    nameZh: "信贷报告·生成",
    nameEn: "Report",
    ts: "10:31:58",
    ref: "rerun 3.4 / 8",
    spineColor: "var(--t-report)",
    body: (
      <>
        收到。切 <b>Wind 连接器</b> 近 4 季度 <b>11.8%</b>，在 3.4 节结尾追加 <em>对歌尔单客户占比 32%</em> 集中度预警一段，并联动到 <b>8 节 风险识别</b> 黄线标注。局部重跑约 <b>90s</b>，完稿后出自审报告。
      </>
    ),
  },
];

const INITIAL_SSE_LINES: TraceLine[] = [
  { ts: "10:23:41", stgTag: "ev · 01", stage: "ev", tx: <>✓ <b>注册资本</b> 5,000 万 <span className="src">SRC 工商</span></> },
  { ts: "10:23:47", stgTag: "ev · 02", stage: "ev", tx: <>✓ <b>近一年营收</b> 2.14 亿 <span className="src">SRC 利润表</span></> },
  { ts: "10:23:52", stgTag: "ev · 03", stage: "ev", tx: <>✗ <b>实控人关联企业</b> <span className="bad">未找到</span> 挂「需补充」</> },
  { ts: "10:24:03", stgTag: "gn · 2.1", stage: "gn", tx: <>写入 <b>企业基本情况</b>，证据命中 <em>14/14</em> <span className="src">1-9</span></> },
  { ts: "10:24:12", stgTag: "gn · 3.4", stage: "gn", tx: <>写入 <b>主营上下游</b>，占比锚到 <em>合同样本</em> <span className="src">14</span></> },
  { ts: "10:24:19", stgTag: "gn · 4.2", stage: "gn", typing: true, tx: <>写入 <b>财务比率</b> — 资产负债率 <em>52.4%</em> · 流动比 <em>1.38</em> <span className="src">financial_analyzer</span></> },
];

// Map SSE stage key → trace stage bucket used by mockup-v2 CSS (s-ev/s-gn/s-au)
function reportStageBucket(stage?: string): "ev" | "gn" | "au" {
  if (!stage) return "gn";
  if (stage === "ingest" || stage === "extract" || stage === "infer") return "ev";
  if (stage === "write") return "gn";
  if (stage === "audit") return "au";
  return "gn";
}

function fmtNowHMS(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function reportEventToLine(evt: ReportEvent, idx: number): TraceLine | null {
  const ts = fmtNowHMS();
  if (evt.event === "stage") {
    const bucket = reportStageBucket(evt.stage);
    return {
      ts,
      stgTag: `${bucket} · ${String(idx).padStart(2, "0")}`,
      stage: bucket,
      tx: (
        <>
          ▸ <b>{evt.stage}</b> {evt.message ? <span className="src">{evt.message}</span> : null}
        </>
      ),
    };
  }
  if (evt.event === "section") {
    return {
      ts,
      stgTag: `gn · ${String(idx).padStart(2, "0")}`,
      stage: "gn",
      tx: (
        <>
          写入 <b>{evt.section.title}</b> <span className="src">{evt.section.id}</span>
        </>
      ),
    };
  }
  if (evt.event === "profile") {
    const name = evt.profile.company_name ?? "企业画像";
    return {
      ts,
      stgTag: `ev · ${String(idx).padStart(2, "0")}`,
      stage: "ev",
      tx: (
        <>
          ✓ <b>{name}</b> 画像载入 <span className="src">SRC agent6</span>
        </>
      ),
    };
  }
  if (evt.event === "done") {
    const stats = evt.payload.stats;
    return {
      ts,
      stgTag: `au · ${String(idx).padStart(2, "0")}`,
      stage: "au",
      tx: (
        <>
          ✓ <b>自审完成</b>
          {stats
            ? (
              <>
                {" "}
                已填 <em>{stats.auto_filled}/{stats.total_fields}</em> · 未填 <em>{stats.unfilled}</em>
              </>
            )
            : null}
        </>
      ),
    };
  }
  if (evt.event === "error") {
    return {
      ts,
      stgTag: `au · ${String(idx).padStart(2, "0")}`,
      stage: "au",
      tx: (
        <>
          ✗ <span className="bad">{evt.message}</span>
        </>
      ),
    };
  }
  return null;
}

const SECTIONS: DocSection[] = [
  {
    n: "01",
    name: "企业基本情况",
    en: "Basic Profile",
    state: "ok",
    stateText: "18/18",
    body: (
      <>
        <p>苏州睿联电子股份有限公司，成立于 2016 年 3 月，注册地江苏省苏州市工业园区苏虹东路 168 号。注册资本 <span className="num">5,000</span> 万元人民币，实收资本 <span className="num">5,000</span> 万元，统一社会信用代码 91320594MA1R5KXY7B，法定代表人陈睿联。</p>
        <p>公司主营业务为精密连接器的研发、制造及销售，归属计算机、通信和其他电子设备制造业（C39）。员工总数 <span className="num">420</span> 人，其中研发人员 <span className="num">77</span> 人，占比 <span className="num">18.3%</span>。经营期限 30 年，经营范围包括电子元器件及连接器的研发、生产、销售，相关技术服务与咨询，货物进出口。</p>
      </>
    ),
  },
  {
    n: "02",
    name: "股东与实际控制人",
    en: "Shareholders",
    state: "ok",
    stateText: "22/22",
    body: (
      <>
        <p>本公司目前共有股东 3 名。实际控制人陈睿联先生直接持股 <span className="num">58.3%</span>；通过其控股的苏州睿联投资合伙企业（有限合伙）间接持有 <span className="num">21.7%</span>；其配偶李艳华持股 <span className="num">10.0%</span>。三方合计持股 <span className="num">90.0%</span>，陈睿联合计控制 <span className="num">80.0%</span>。</p>
        <p>实际控制人陈睿联，1978 年生，中国国籍，工学硕士。2016 年创立本公司，此前任职于瑞士 TE Connectivity（泰科电子）苏州分公司达 12 年，担任资深研发经理，专业背景扎实。近 5 年无重大对外投资、诉讼及不良记录。</p>
      </>
    ),
  },
  {
    n: "03",
    name: "主营业务与行业",
    en: "Business & Industry",
    state: "warn",
    stateText: "31/40 · 3.4 待补",
    body: (
      <>
        <p>公司专注于精密连接器的研发与制造，产品覆盖消费电子、新能源汽车、通信设备三大下游。2024 年前三季度营收结构：消费电子板块 <span className="num">61%</span>（主要客户歌尔 <span className="num">32%</span>、立讯 <span className="num">21%</span>、瑞声 <span className="num">8%</span>），新能源汽车板块 <span className="num">25%</span>（宁德时代配套 <span className="num">14%</span>、比亚迪 <span className="num">9%</span>、蔚来 <span className="num">2%</span>），通信设备板块 <span className="num">14%</span>（华为、中兴合计）。</p>
        <p>核心产品包括 Type-C 连接器、车载高压连接器、BTB 板对板连接器，在相关细分领域具备一定技术壁垒与客户粘性。</p>
        <p><b>3.4 节 行业景气度</b>　<span className="pending-mark">外因待你补答 · 暂占位 Wind 连接器近 4 季度均值 11.8%</span></p>
        <p>上下游分析：上游主要原材料为铜合金、工程塑料，采购较为集中，前五大供应商占比 <span className="num">68%</span>，铜价敏感度较高；下游客户以大型电子制造商为主，应收账款周转 <span className="num">72</span> 天（上年同期 <span className="num">58</span> 天），账期有所延长。</p>
      </>
    ),
  },
  {
    n: "04",
    name: "财务状况",
    en: "Financials",
    state: "live",
    stateText: "生成中 48/78",
    flag: "live",
    body: (
      <>
        <p>近三年营收年均复合增长率 <span className="num">23.1%</span>，2024 年前三季度营业收入 <span className="num">2.14</span> 亿元，同比增长 <span className="num">21.4%</span>。资产负债率 <span className="num">52.4%</span>，流动比率 <span className="num">1.38</span>，速动比率 <span className="num">0.92</span>。</p>
        <p>主要资产构成：应收账款 <span className="num">0.42</span> 亿（周转 <span className="num">72</span> 天）、存货 <span className="num">0.28</span> 亿、固定资产 <span className="num">1.85</span> 亿（厂房为主）。主要负债构成：短期借款 <span className="num">0.68</span> 亿、应付账款 <span className="num">0.35</span> 亿<span className="cursor">▋</span></p>
      </>
    ),
  },
  {
    n: "05", name: "经营状况", en: "Operations", state: "ok", stateText: "26/26",
    body: (
      <>
        <p>2024 年前三季度营业收入 <span className="num">2.14</span> 亿元，年化人均产值约 <span className="num">68</span> 万元；研发投入 <span className="num">0.39</span> 亿元，占营收 <span className="num">18.3%</span>。主要客户集中度 CR5 为 <span className="num">67.2%</span>，集中度偏高，已在 <em>3.4 节</em>补充行业口径与风险提示。</p>
        <p>主要客户合作稳定，歌尔、立讯、宁德时代均为 5 年以上合作伙伴，近三年无重大客户流失记录。</p>
      </>
    ),
  },
  {
    n: "06", name: "授信历史与关联", en: "Credit History", state: "ok", stateText: "34/34",
    body: (
      <>
        <p>在 5 家银行留有授信记录：建行苏州分行综合授信 <span className="num">5,000</span> 万元（自 2021 年起），工行苏州分行 <span className="num">3,000</span> 万元，招行 <span className="num">2,000</span> 万元，平安 <span className="num">1,500</span> 万元，中信 <span className="num">1,000</span> 万元。</p>
        <p>现有授信余额 <span className="num">1.2</span> 亿元，已用信 <span className="num">8,600</span> 万元。近 24 期零逾期、零展期、零重组。关联方苏州睿联科技有限公司（持股 <span className="num">100%</span>）无不良征信记录。</p>
      </>
    ),
  },
  {
    n: "07", name: "担保/抵押", en: "Collateral", state: "ok", stateText: "14/14",
    body: (
      <p>本次授信拟采取组合担保：① 名下工业园区厂房抵押——苏州工业园区 A2 地块，建筑面积 <span className="num">6,800</span>㎡，评估价 <span className="num">6,200</span> 万元；② 法定代表人陈睿联个人不可撤销连带责任保证；③ 苏州睿联投资合伙企业（有限合伙）连带责任保证。抵押覆盖率约 <span className="num">77.5%</span>。</p>
    ),
  },
  {
    n: "08", name: "风险识别", en: "Risk", state: "warn", stateText: "23/28 · 担保人净资产待补",
    body: (
      <p>主要风险：<em>① 客户集中度</em>——CR5 <span className="num">67.2%</span>，歌尔单客户占比 <span className="num">32%</span>（触黄线），已在 3.4 节补集中度风险口径；<em>② 应收账款周转</em>——由 <span className="num">58</span> 天延至 <span className="num">72</span> 天，需关注回款节奏；<em>③ 原材料铜价敏感</em>——铜在成本中占比约 <span className="num">22%</span>，已与客户建立铜价联动结算条款；<em>④ 担保人净资产</em>　<span className="pending-mark">待人工补</span>。</p>
    ),
  },
  {
    n: "09", name: "合规情况", en: "Compliance", state: "ok", stateText: "16/16",
    body: <p>经与合规助手 Agent5 交叉校验：近 3 年无重大行政处罚；环保、社保、税务合规等级 A；2026-04-18 发布的《小微信贷风控新规》3 节适用范围与本公司业务无直接冲突；内控 A-12 条款已纳入授信方案条件。</p>,
  },
  {
    n: "10", name: "授信方案", en: "Proposal", state: "ok", stateText: "24/24 · via Agent3",
    body: (
      <>
        <p>建议综合授信 <span className="num">8,000</span> 万元。其中：流动资金贷款 <span className="num">5,000</span> 万元（期限 1 年，LPR+85BP，按月付息到期还本）；银行承兑汇票 <span className="num">2,000</span> 万元（期限 6 个月，保证金比例 <span className="num">30%</span>）；票据贴现 <span className="num">1,000</span> 万元（期限 6 个月）。</p>
        <p>还款来源：主营业务回款（月均 <span className="num">2,300</span> 万元）可覆盖本息 <span className="num">2.5</span> 倍；厂房抵押覆盖率 <span className="num">77.5%</span>；实控人连带担保。建议由苏州工业园区支行作为主办行。</p>
      </>
    ),
  },
  {
    n: "11", name: "审批意见", en: "Approval", state: "pend", stateText: "人审", flag: "pending",
    body: <p>待客户经理定稿后 → 支行初审 → 分行复审 → 总行终审。</p>,
  },
  {
    n: "12", name: "附件清单", en: "Appendix", state: "ok", stateText: "14/14",
    body: <p>共 <span className="num">14</span> 份附件：① 营业执照复印件；② 章程及股东会决议；③ 财务三表·近 3 年审计报告（立信会计师事务所）；④ 人行企业征信报告（编号 SZ-20241128-0417）；⑤ 纳税申报表·近 24 期；⑥ 授信申请书；⑦ 抵押物评估报告（沃克森评估）；⑧ 主要客户合同样本（歌尔、立讯、宁德时代）；⑨ 主要供应商合同样本；⑩ 环保合规证明；⑪ 担保人征信；⑫ 董事会决议；⑬ 授权委托书；⑭ 其他。</p>,
  },
];

const QC_METRICS: QcMetric[] = [
  { k: "字段完整度", v: "93.5", p: "94%" },
  { k: "证据溯源率", v: "98.2", p: "98%" },
  { k: "幻觉检出", v: "0", p: "100%" },
  { k: "数字一致性", v: "100", p: "100%" },
  { k: "QC 阻断", v: "0", p: "100%" },
  { k: "占位符残留", v: "0", p: "100%" },
  { k: "合规术语", v: "99.1", p: "99%" },
  { k: "章节完整", v: "12/12", p: "100%" },
  { k: "评分一致", v: "87", p: "87%", hot: true },
];

export default function ReportV2() {
  const [lines, setLines] = useState<TraceLine[]>(INITIAL_SSE_LINES);
  const [isMock, setIsMock] = useState(false);
  const [started, setStarted] = useState(false);

  // SSE kickoff — no longer mount-auto; waits for `started` CTA press.
  useEffect(() => {
    if (!started) return;
    let cancelled = false;
    let idx = INITIAL_SSE_LINES.length;

    // Adapt mock fixture JSON → flat ReportEvent[] for withFallback replay.
    const replay = (j: unknown): ReportEvent[] => {
      const obj = j as {
        stages?: Array<{ event: "stage"; stage: string; message?: string }>;
        sections?: Array<{ event: "section"; section: { id: string; title: string; content: string } }>;
        done?: { event: "done"; enterprise_profile?: unknown; payload?: unknown };
      };
      const events: ReportEvent[] = [];
      for (const s of obj.stages ?? []) events.push(s as ReportEvent);
      for (const s of obj.sections ?? []) events.push(s as ReportEvent);
      if (obj.done) {
        // Fixture uses `enterprise_profile` at top-level of done — remap into ReportDonePayload.payload.
        const done = obj.done as Record<string, unknown>;
        const payload = (done.payload ?? {
          profile: done.enterprise_profile,
          sections: (obj.sections ?? []).map((s) => s.section),
          stats: { total_fields: 460, auto_filled: 428, unfilled: 32 },
          docx_url: done.report_docx_url,
        }) as unknown;
        events.push({ event: "done", payload } as ReportEvent);
      }
      return events;
    };

    (async () => {
      try {
        for await (const [evt, source] of withFallback<ReportEvent>(
          (signal) =>
            streamReportFill({ preset: "dingsheng_trade", mock: false }, signal),
          "/mock/report_fill_mock.json",
          { timeoutMs: 2000, replayEvents: replay, replayIntervalMs: 550 }
        )) {
          if (cancelled) return;
          if (source === "mock") setIsMock(true);
          const line = reportEventToLine(evt, idx++);
          if (line) setLines((prev) => [...prev, line]);
        }
      } catch {
        // swallow — visual stays on INITIAL_SSE_LINES seed
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [started]);

  const handleTrigger = () => {
    if (started) {
      // Re-run: reset all derived state then kick again next tick
      setLines(INITIAL_SSE_LINES);
      setIsMock(false);
      setStarted(false);
      setTimeout(() => setStarted(true), 16);
    } else {
      setStarted(true);
    }
  };

  return (
    <V2Shell
      agent="report"
      hero={{
        eyebrowText: "REPORT AGENT · 待你补答",
        eyebrowAccent: "外因追问停在第 11 分钟",
        heroTitle: (
          <>
            <span className="cn">苏州睿联电子</span> <em>3.4 节</em> 行业口径等你 <em>1 条</em> 补答。
          </>
        ),
        heroSub: (
          <>
            460 项字段已写 <span className="num">428</span>，覆盖 <span className="num">93.5%</span>，<em>外因</em> 1 条材料未覆盖 — 补完后局部重跑约 <span className="num">90s</span>。
            <span className="bullet" />
            <button type="button" className="v2-cta" onClick={handleTrigger}>
              {started ? <>重新演示 <em>↻</em></> : <>开始生成报告 <em>↗</em></>}
            </button>
            <button type="button" className="pill ghost">先跳过，进自审</button>
          </>
        ),
      }}
      apHead={{
        zh: "信贷报告 · 生成",
        en: "Credit Report Drafter",
        ver: "v7.23",
        metas: [
          { k: "擅长", v: "中小企业信贷申报书 · 460 项字段初稿" },
          { k: "当前", v: "3.4 节停待补答", state: "warn" },
          { k: "今日", v: "4 次 · 全部留痕" },
        ],
        health: "LLM 在线 · DeepSeek",
        cta: { label: "导出 Word", arrow: "↗" },
      }}
      cap={{ cn: "三阶段", em: "— Evidence / Grounded / Self-Audit", k: "SESSION · 20260420-1024" }}
      stages={[
        { n: "01", nm: "证据", en: "— Evidence", state: "done", sub: <><em>KB 已建</em> · 扫 <b>4</b> 源材料 · 抽中 <b>418</b> 数据点 · <b>42</b> 项待补</> },
        { n: "02", nm: "生成", en: "— Grounded", state: "live", sub: <>LLM 仅用证据写正文 · 已落 <b>428 / 460</b> 段 · <em>3.4 节挂起</em> 待补答</> },
        { n: "03", nm: "自审", en: "— Self-Audit", sub: <>核对 <em>数字 · 出处 · 口径</em>，标出 <em>重复 / 矛盾 / 缺证</em>，由你签字定稿</> },
      ]}
      tplTitle={{
        lbl: "选模板",
        hint: <>已选 <b>对公 · corp-v7.23</b> · 12 节 · 460 字段 · 切换会整卷重跑</>,
        k: "REPORT TEMPLATE",
      }}
      tpls={[
        { key: "corp",   name: "对公信贷调查",   tag: "Corp",   meta: "corp-v7.23 · 标准", spec: "12 节 · 460 字段 · 2~3 万字", on: true },
        { key: "sme",    name: "普惠小微快报",   tag: "SME",    meta: "sme-v5.1 · 轻量",   spec: "8 节 · 210 字段 · 8~12 千字" },
        { key: "retail", name: "对私个贷尽调",   tag: "Retail", meta: "retail-v4.2",        spec: "6 节 · 140 字段 · 5~8 千字" },
        { key: "green",  name: "绿色金融专项",   tag: "Green",  meta: "green-v2.0 · ESG",   spec: "14 节 · 520 字段 · 含碳核算" },
      ]}
      intake={[
        { kind: "drop", title: "拖客户资料到此 · 或点右侧选取", sub: "已收 4/6 件 · .pdf / .docx / .xlsx · 单份 ≤ 20MB", btn: "选文件" },
        { kind: "opt", on: true, k: "业务线", v: <>对公 Corporate</> },
        { kind: "opt", k: "预置案例", v: <>睿联电子</> },
        { kind: "opt", k: "Mock 回放", v: <>关</>, toggle: true },
      ]}
      chatSlot={
        <ChatBlk
          title="对话 · 边写边补"
          subTitle="— Refine Chat"
          kBadge="1 pending · 3.4 节"
          messages={MESSAGES}
          seeds={[
            { q: "Q1", body: <>补<em>实控人关联企业</em>名单</> },
            { q: "Q2", body: <>加一段集中度意见到 <em>3.4 节</em></> },
            { q: "Q3", body: <>底稿抄送 <em>授信 Agent3</em></> },
          ]}
          placeholder="继续追问 · 例如：补一段还款来源分析到 10 节…"
        />
      }
      docSlot={
        <>
          <SseBlk
            title={<>事件流 <em>— SSE · evidence / grounded / audit</em></>}
            kBadge={isMock ? "降级 · MOCK" : "live"}
            lines={lines}
          />
          <DocWrap
            docTitle="信贷申报书 · 苏州睿联电子股份"
            docSubtitle="Draft · corp-v7.23"
            metrics={[
              <>428 / 460</>,
              <>93.5%</>,
              <span className="hot">32 项未填</span>,
              <>证据 98.2%</>,
            ]}
            sections={SECTIONS}
          />
        </>
      }
      auditSlot={
        <AuditStrip
          verdict={{
            k: "Verdict · 总体",
            v: <>可提交审贷 <em>— 补 1 项外因即完稿</em></>,
            tip: <>四大板块已成稿（<b>428 / 460</b> 段），外因追问 <b>1</b> 条待补答后局部重跑约 <b>90s</b>。自审门控未启。</>,
            ctas: [
              { label: "复核底稿" },
              { label: "导出 Word ↗", primary: true },
            ],
          }}
          coverage={[
            { k: "填写", v: <>428<sub>/460</sub></> },
            { k: "覆盖", v: <>93.5<sub>%</sub></> },
            { k: "未填", v: <>32<sub>项</sub></>, hot: true },
          ]}
          unfilled={{
            k: "未能自动填写 · 典型 3 项",
            items: (
              <>
                <span className="tag">实控人关联企业名单</span>材料未覆盖 · <span className="tag">担保人净资产</span>需人工补 · <span className="tag">行业景气度口径</span>外因追问
              </>
            ),
          }}
          qc={QC_METRICS}
        />
      }
    />
  );
}
