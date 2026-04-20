"use client";

/**
 * ReportV2 — DOM-aligned port of design_mockups/stage5/mockup-v2/report.html,
 * with full feature surface merged from legacy ReportWorkspaceClient.tsx
 * (MockToggle / 5 presets / template + materials upload / LLM health / docx url).
 *
 * IM-chat paradigm: legacy form controls are wrapped as chat messages + composer.
 * - Agent first msg invites user to pick a preset or upload
 * - Preset quick-reply chips under agent msg → click injects user msg + auto-runs
 * - Mock toggle + LLM status pills sit in composer
 * - 📎 attachment picker + run CTA in composer
 * - Agent reply msg after done shows docx attachment chip (real URL)
 *
 * SSE wired via streamReportFill + withFallback (W1/W5 origin) with
 * /mock/report_fill_mock.json fallback on 2s timeout.
 */

import { useEffect, useRef, useState } from "react";
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
  type PresetChip,
  type ComposerPillBarItem,
} from "./V2Shell";
import { streamReportFill, getReportHealth } from "@/lib/api";
import { withFallback } from "@/lib/fallback";
import type { BusinessLine, ReportEvent } from "@/lib/credit-types";

type PresetDef = {
  key: string;
  name: string;
  tagline: string;
  business_line: BusinessLine;
};

const PRESETS: PresetDef[] = [
  { key: "dingsheng_trade",     name: "鼎盛商贸",     tagline: "对公 · 建材批发 · 流贷 500 万", business_line: "corporate" },
  { key: "suzhou_ruilian",      name: "苏州睿联",     tagline: "对公 · 精密连接器 · 8,000 万",   business_line: "corporate" },
  { key: "zhangsan_restaurant", name: "张某餐饮",     tagline: "普惠 · 个体经营 · 50 万",        business_line: "inclusive" },
  { key: "haiwan_trade",        name: "海湾贸易",     tagline: "对公 · 进出口 · 2,000 万",       business_line: "corporate" },
  { key: "lixiangjiafu",        name: "理想家服",     tagline: "普惠 · 家政连锁 · 80 万",        business_line: "inclusive" },
];

const INITIAL_SSE_LINES: TraceLine[] = [
  { ts: "10:23:41", stgTag: "ev · 01", stage: "ev", tx: <>✓ <b>注册资本</b> 5,000 万 <span className="src">SRC 工商</span></> },
  { ts: "10:23:47", stgTag: "ev · 02", stage: "ev", tx: <>✓ <b>近一年营收</b> 2.14 亿 <span className="src">SRC 利润表</span></> },
  { ts: "10:23:52", stgTag: "ev · 03", stage: "ev", tx: <>✗ <b>实控人关联企业</b> <span className="bad">未找到</span> 挂「需补充」</> },
  { ts: "10:24:03", stgTag: "gn · 2.1", stage: "gn", tx: <>写入 <b>企业基本情况</b>，证据命中 <em>14/14</em> <span className="src">1-9</span></> },
  { ts: "10:24:12", stgTag: "gn · 3.4", stage: "gn", tx: <>写入 <b>主营上下游</b>，占比锚到 <em>合同样本</em> <span className="src">14</span></> },
  { ts: "10:24:19", stgTag: "gn · 4.2", stage: "gn", typing: true, tx: <>写入 <b>财务比率</b> — 资产负债率 <em>52.4%</em> · 流动比 <em>1.38</em> <span className="src">financial_analyzer</span></> },
];

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

function fmtSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${bytes}B`;
}

function reportEventToLine(evt: ReportEvent, idx: number): TraceLine | null {
  const ts = fmtNowHMS();
  if (evt.event === "stage") {
    const bucket = reportStageBucket(evt.stage);
    return {
      ts, stgTag: `${bucket} · ${String(idx).padStart(2, "0")}`, stage: bucket,
      tx: <>▸ <b>{evt.stage}</b> {evt.message ? <span className="src">{evt.message}</span> : null}</>,
    };
  }
  if (evt.event === "section") {
    return {
      ts, stgTag: `gn · ${String(idx).padStart(2, "0")}`, stage: "gn",
      tx: <>写入 <b>{evt.section.title}</b> <span className="src">{evt.section.id}</span></>,
    };
  }
  if (evt.event === "profile") {
    const name = evt.profile.company_name ?? "企业画像";
    return {
      ts, stgTag: `ev · ${String(idx).padStart(2, "0")}`, stage: "ev",
      tx: <>✓ <b>{name}</b> 画像载入 <span className="src">SRC agent6</span></>,
    };
  }
  if (evt.event === "done") {
    const stats = evt.payload.stats;
    return {
      ts, stgTag: `au · ${String(idx).padStart(2, "0")}`, stage: "au",
      tx: <>✓ <b>自审完成</b>{stats ? <> 已填 <em>{stats.auto_filled}/{stats.total_fields}</em> · 未填 <em>{stats.unfilled}</em></> : null}</>,
    };
  }
  if (evt.event === "error") {
    return {
      ts, stgTag: `au · ${String(idx).padStart(2, "0")}`, stage: "au",
      tx: <>✗ <span className="bad">{evt.message}</span></>,
    };
  }
  return null;
}

const SECTIONS: DocSection[] = [
  { n: "01", name: "企业基本情况", en: "Basic Profile", state: "ok", stateText: "18/18",
    body: (<>
      <p>苏州睿联电子股份有限公司，成立于 2016 年 3 月，注册地江苏省苏州市工业园区苏虹东路 168 号。注册资本 <span className="num">5,000</span> 万元人民币，实收资本 <span className="num">5,000</span> 万元，统一社会信用代码 91320594MA1R5KXY7B，法定代表人陈睿联。</p>
      <p>公司主营业务为精密连接器的研发、制造及销售，归属计算机、通信和其他电子设备制造业（C39）。员工总数 <span className="num">420</span> 人，其中研发人员 <span className="num">77</span> 人，占比 <span className="num">18.3%</span>。</p>
    </>),
  },
  { n: "02", name: "股东与实际控制人", en: "Shareholders", state: "ok", stateText: "22/22",
    body: <p>本公司目前共有股东 3 名。实际控制人陈睿联先生直接持股 <span className="num">58.3%</span>；通过其控股的苏州睿联投资合伙企业（有限合伙）间接持有 <span className="num">21.7%</span>；其配偶李艳华持股 <span className="num">10.0%</span>。</p>,
  },
  { n: "03", name: "主营业务与行业", en: "Business & Industry", state: "warn", stateText: "31/40 · 3.4 待补",
    body: (<>
      <p>公司专注于精密连接器的研发与制造，产品覆盖消费电子、新能源汽车、通信设备三大下游。</p>
      <p><b>3.4 节 行业景气度</b>　<span className="pending-mark">外因待你补答 · 暂占位 Wind 连接器近 4 季度均值 11.8%</span></p>
    </>),
  },
  { n: "04", name: "财务状况", en: "Financials", state: "live", stateText: "生成中 48/78", flag: "live",
    body: <p>近三年营收年均复合增长率 <span className="num">23.1%</span>，资产负债率 <span className="num">52.4%</span>，流动比率 <span className="num">1.38</span>。<span className="cursor">▋</span></p>,
  },
  { n: "05", name: "经营状况", en: "Operations", state: "ok", stateText: "26/26",
    body: <p>2024 年前三季度营业收入 <span className="num">2.14</span> 亿元，年化人均产值约 <span className="num">68</span> 万元。</p>,
  },
  { n: "06", name: "授信历史与关联", en: "Credit History", state: "ok", stateText: "34/34",
    body: <p>在 5 家银行留有授信记录，现有授信余额 <span className="num">1.2</span> 亿元，已用信 <span className="num">8,600</span> 万元。近 24 期零逾期、零展期、零重组。</p>,
  },
  { n: "07", name: "担保/抵押", en: "Collateral", state: "ok", stateText: "14/14",
    body: <p>本次授信拟采取组合担保，抵押覆盖率约 <span className="num">77.5%</span>。</p>,
  },
  { n: "08", name: "风险识别", en: "Risk", state: "warn", stateText: "23/28 · 担保人净资产待补",
    body: <p>主要风险：客户集中度 CR5 <span className="num">67.2%</span>；担保人净资产　<span className="pending-mark">待人工补</span>。</p>,
  },
  { n: "09", name: "合规情况", en: "Compliance", state: "ok", stateText: "16/16",
    body: <p>经与合规助手 Agent5 交叉校验：近 3 年无重大行政处罚。</p>,
  },
  { n: "10", name: "授信方案", en: "Proposal", state: "ok", stateText: "24/24 · via Agent3",
    body: <p>建议综合授信 <span className="num">8,000</span> 万元。</p>,
  },
  { n: "11", name: "审批意见", en: "Approval", state: "pend", stateText: "人审", flag: "pending",
    body: <p>待客户经理定稿后 → 支行初审 → 分行复审 → 总行终审。</p>,
  },
  { n: "12", name: "附件清单", en: "Appendix", state: "ok", stateText: "14/14",
    body: <p>共 <span className="num">14</span> 份附件。</p>,
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

const INITIAL_AGENT_MSG: ChatMessage = {
  side: "agent",
  sig: "R.",
  nameZh: "信贷报告·生成",
  nameEn: "Report",
  ts: "10:30:00",
  spineColor: "var(--t-report)",
  body: <>晨间您好。请选择 <em>内置演示数据</em>，或 📎 上传 <b>新客户材料</b> + <b>申报书模板</b>。默认对公 corp-v7.23。</>,
};

export default function ReportV2() {
  // Legacy-ported state
  const [preset, setPreset] = useState<string>("dingsheng_trade");
  const [businessLine, setBusinessLine] = useState<BusinessLine>("corporate");
  const [uploaded, setUploaded] = useState<File[]>([]);
  const [templateUpload, setTemplateUpload] = useState<File | undefined>(undefined);
  const [mockMode, setMockMode] = useState(true);
  const [llmConnected, setLlmConnected] = useState<boolean | null>(null);
  const [docxUrl, setDocxUrl] = useState<string | undefined>(undefined);
  const abortRef = useRef<AbortController | null>(null);
  const tplInputRef = useRef<HTMLInputElement>(null);

  // V2 SSE state
  const [lines, setLines] = useState<TraceLine[]>(INITIAL_SSE_LINES);
  const [isMock, setIsMock] = useState(false);
  const [started, setStarted] = useState(false);
  const [finished, setFinished] = useState(false);

  // Chat messages — dynamic; starts with one agent intro msg
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_AGENT_MSG]);

  // Query LLM health once on mount (legacy behavior).
  useEffect(() => {
    getReportHealth()
      .then((h) => setLlmConnected(h.llm_connected))
      .catch(() => setLlmConnected(false));
  }, []);

  const pushMsg = (m: ChatMessage) => setMessages((prev) => [...prev, m]);

  // Preset click → push user msg + auto-run
  const handlePreset = (p: PresetDef) => {
    if (started && !finished) return; // ignore while running
    setPreset(p.key);
    setBusinessLine(p.business_line);
    pushMsg({
      side: "user", sig: "王.", nameZh: "王哲", nameEn: "华东客户经理",
      ts: fmtNowHMS(),
      body: <>使用预设：<b>{p.name}</b>　<em>{p.tagline}</em></>,
    });
    // kick run next tick so state settles
    setTimeout(() => runReport(p.key, p.business_line), 30);
  };

  const handleMockToggle = () => {
    if (started && !finished) return;
    const next = !mockMode;
    setMockMode(next);
    pushMsg({
      side: "user", sig: "王.", nameZh: "王哲", nameEn: "华东客户经理",
      ts: fmtNowHMS(),
      body: next ? <>切回 <em>演示模式</em>（Mock 回放）</> : <>切换到 <em>真实接口模式</em>（走 agent_report 后端）</>,
    });
  };

  const handleMaterialsPick = (files: File[]) => {
    if (files.length === 0) return;
    setUploaded((prev) => [...prev, ...files]);
    pushMsg({
      side: "user", sig: "王.", nameZh: "王哲", nameEn: "华东客户经理",
      ts: fmtNowHMS(),
      body: <>上传客户材料 <b>{files.length}</b> 份</>,
      attachments: files.map((f) => ({ name: f.name, size: fmtSize(f.size) })),
    });
  };

  const handleTemplatePick = (files: File[]) => {
    const f = files[0];
    if (!f) return;
    setTemplateUpload(f);
    pushMsg({
      side: "user", sig: "王.", nameZh: "王哲", nameEn: "华东客户经理",
      ts: fmtNowHMS(),
      body: <>上传 <em>申报书模板</em></>,
      attachments: [{ name: f.name, size: fmtSize(f.size), icon: "📄" }],
    });
  };

  // Real run — merges legacy run() with V2 SSE UI feedback
  const runReport = async (presetKey?: string, line?: BusinessLine) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setLines(INITIAL_SSE_LINES);
    setIsMock(false);
    setFinished(false);
    setStarted(true);
    setDocxUrl(undefined);

    const pKey = presetKey ?? preset;
    const bLine = line ?? businessLine;

    pushMsg({
      side: "agent", sig: "R.", nameZh: "信贷报告·生成", nameEn: "Report",
      ts: fmtNowHMS(), ref: "evidence → grounded → audit", spineColor: "var(--t-report)",
      body: <>收到，正在解析材料 · <em>三阶段 Evidence</em> · 预计 <b>90s</b> 完稿。事件流同步到右侧。</>,
    });

    let idx = INITIAL_SSE_LINES.length;

    const replay = (j: unknown): ReportEvent[] => {
      const obj = j as {
        stages?: Array<{ event: "stage"; stage: string; message?: string }>;
        sections?: Array<{ event: "section"; section: { id: string; title: string; content: string } }>;
        done?: { event: "done"; enterprise_profile?: unknown; payload?: unknown; report_docx_url?: string };
      };
      const events: ReportEvent[] = [];
      for (const s of obj.stages ?? []) events.push(s as ReportEvent);
      for (const s of obj.sections ?? []) events.push(s as ReportEvent);
      if (obj.done) {
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

    try {
      for await (const [evt, source] of withFallback<ReportEvent>(
        (signal) => streamReportFill({
          preset: pKey,
          mock: mockMode,
          business_line: bLine,
          files: mockMode ? undefined : uploaded,
          template_file: mockMode ? undefined : templateUpload,
        }, signal),
        "/mock/report_fill_mock.json",
        { timeoutMs: 2000, replayEvents: replay, replayIntervalMs: 550 }
      )) {
        if (ctrl.signal.aborted) return;
        if (source === "mock") setIsMock(true);
        const line = reportEventToLine(evt, idx++);
        if (line) setLines((prev) => [...prev, line]);
        if (evt.event === "done") {
          const url = evt.payload.docx_url;
          setDocxUrl(url);
          const stats = evt.payload.stats;
          setFinished(true);
          pushMsg({
            side: "agent", sig: "R.", nameZh: "信贷报告·生成", nameEn: "Report",
            ts: fmtNowHMS(), ref: "done", spineColor: "var(--t-report)",
            body: (
              <>
                ✓ 报告已生成。
                {stats ? <> <b>{stats.total_fields}</b> 字段 · <b>{stats.auto_filled}</b> 自动 · <em>{stats.unfilled}</em> 未填。</> : null}
              </>
            ),
            attachments: url && !url.startsWith("#")
              ? [{ name: `${pKey}-报告.docx`, href: url, icon: "📄" }]
              : [{ name: `${pKey}-报告.docx（mock · 占位）`, icon: "📄" }],
          });
        }
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      pushMsg({
        side: "agent", sig: "R.", nameZh: "信贷报告·生成", nameEn: "Report",
        ts: fmtNowHMS(), ref: "error", spineColor: "var(--t-report)",
        body: <>✗ 生成中断：<em>{String(e)}</em></>,
      });
    }
  };

  const presetChips: PresetChip[] = PRESETS.map((p) => ({
    key: p.key,
    label: <>{p.name}<em style={{ opacity: .65, marginLeft: 6, fontSize: 10 }}>{p.tagline}</em></>,
    active: preset === p.key,
    disabled: started && !finished,
    onClick: () => handlePreset(p),
  }));

  const realRunBlocked = !mockMode && llmConnected === false;
  const realNeedsFiles = !mockMode && uploaded.length === 0;
  const runDisabled = (started && !finished) || realRunBlocked || realNeedsFiles;
  const runTitle = realRunBlocked
    ? "LLM 未连接 · 联系 IT 配置 DEEPSEEK_API_KEY，或切回演示模式"
    : realNeedsFiles
    ? "真实模式需先上传客户材料"
    : undefined;

  const composerPills: ComposerPillBarItem[] = [
    {
      key: "mock",
      label: mockMode ? "演示模式 · MOCK ON" : "真实接口 · LIVE",
      active: !mockMode,
      disabled: started && !finished,
      onClick: handleMockToggle,
      title: mockMode ? "当前走 mock 回放" : "当前走 agent_report 真实后端",
    },
    {
      key: "llm",
      label: llmConnected === null
        ? "LLM 检测中…"
        : llmConnected
        ? "LLM · 已连接"
        : "LLM · 未连接",
      active: llmConnected === true,
      disabled: true,
      title: "后端 /api/report/health",
    },
    {
      key: "tpl",
      label: templateUpload ? `模板 · ${templateUpload.name}` : "模板 · 内置 corp-v7.23",
      active: !!templateUpload,
      disabled: started && !finished,
      onClick: () => tplInputRef.current?.click(),
      title: "点击上传自定义模板 (.doc/.docx)",
    },
    {
      key: "line",
      label: businessLine === "corporate" ? "业务线 · 对公" : businessLine === "inclusive" ? "业务线 · 普惠" : "业务线 · 其他",
      active: true,
      disabled: true,
      title: "随预置切换",
    },
  ];

  const dropCell =
    finished
      ? { kind: "drop" as const, title: "已生成 · 460 项字段 · 428 自动填写 · 32 项需人工补", sub: "自审通过 · 可导出 Word · 或点右侧「重新演示」", btn: "看自审" }
      : started
        ? { kind: "drop" as const, title: "正在生成 · 三阶段 Evidence → Grounded → Self-Audit", sub: "事件流实时写入右侧 SSE 面板 · 预计 90 秒完稿", btn: "生成中…" }
        : { kind: "drop" as const, title: uploaded.length > 0 ? `已收 ${uploaded.length} 件材料 · 点「开始生成」` : "拖客户资料到聊天附件 · 或点右下 📎", sub: "已收 4/6 件 · .pdf / .docx / .xlsx · 单份 ≤ 20MB", btn: "选文件" };

  const auxLine = templateUpload ? (
    <>模板：<em>{templateUpload.name}</em> · 点 pill 可替换</>
  ) : (
    <>模板：<em>内置 {businessLine === "corporate" ? "对公 corp-v7.23" : "普惠 sme-v5.1"}</em> · 点「模板」pill 上传自定义 .docx</>
  );

  return (
    <V2Shell
      agent="report"
      hero={{
        eyebrowText: "REPORT AGENT · 待你补答",
        eyebrowAccent: "外因追问停在第 11 分钟",
        heroTitle: (<>
          <span className="cn">苏州睿联电子</span> <em>3.4 节</em> 行业口径等你 <em>1 条</em> 补答。
        </>),
        heroSub: (<>
          460 项字段已写 <span className="num">428</span>，覆盖 <span className="num">93.5%</span>，<em>外因</em> 1 条材料未覆盖 — 补完后局部重跑约 <span className="num">90s</span>。
          <span className="bullet" />
          <button type="button" className="v2-cta" onClick={() => runReport()} disabled={runDisabled} title={runTitle}>
            {started ? <>重新演示 <em>↻</em></> : <>开始生成报告 <em>↗</em></>}
          </button>
          <button type="button" className="pill ghost">先跳过，进自审</button>
        </>),
      }}
      apHead={{
        zh: "信贷报告 · 生成", en: "Credit Report Drafter", ver: "v7.23",
        metas: [
          { k: "擅长", v: "中小企业信贷申报书 · 460 项字段初稿" },
          { k: "当前", v: "3.4 节停待补答", state: "warn" },
          { k: "今日", v: "4 次 · 全部留痕" },
        ],
        health: llmConnected === false ? "LLM 未连接" : "LLM 在线 · DeepSeek",
        cta: docxUrl && !docxUrl.startsWith("#")
          ? { label: "导出 Word", arrow: "↗" }
          : { label: "导出 Word", arrow: "↗" },
      }}
      cap={{ cn: "三阶段", em: "— Evidence / Grounded / Self-Audit", k: "SESSION · 20260420-1024" }}
      stages={[
        { n: "01", nm: "证据", en: "— Evidence", state: "done", sub: <><em>KB 已建</em> · 扫 <b>4</b> 源材料 · 抽中 <b>418</b> 数据点 · <b>42</b> 项待补</> },
        { n: "02", nm: "生成", en: "— Grounded", state: "live", sub: <>LLM 仅用证据写正文 · 已落 <b>428 / 460</b> 段 · <em>3.4 节挂起</em> 待补答</> },
        { n: "03", nm: "自审", en: "— Self-Audit", sub: <>核对 <em>数字 · 出处 · 口径</em>，标出 <em>重复 / 矛盾 / 缺证</em>，由你签字定稿</> },
      ]}
      tplTitle={{
        lbl: "选模板",
        hint: <>已选 <b>{businessLine === "corporate" ? "对公 · corp-v7.23" : "普惠 · sme-v5.1"}</b> · 切换会整卷重跑</>,
        k: "REPORT TEMPLATE",
      }}
      tpls={[
        { key: "corp",   name: "对公信贷调查",   tag: "Corp",   meta: "corp-v7.23 · 标准", spec: "12 节 · 460 字段 · 2~3 万字", on: businessLine === "corporate" },
        { key: "sme",    name: "普惠小微快报",   tag: "SME",    meta: "sme-v5.1 · 轻量",   spec: "8 节 · 210 字段 · 8~12 千字",  on: businessLine === "inclusive" },
        { key: "retail", name: "对私个贷尽调",   tag: "Retail", meta: "retail-v4.2",        spec: "6 节 · 140 字段 · 5~8 千字" },
        { key: "green",  name: "绿色金融专项",   tag: "Green",  meta: "green-v2.0 · ESG",   spec: "14 节 · 520 字段 · 含碳核算" },
      ]}
      intake={[
        dropCell,
        { kind: "opt", on: true, k: "业务线", v: <>{businessLine === "corporate" ? "对公 Corporate" : businessLine === "inclusive" ? "普惠 Inclusive" : "—"}</> },
        { kind: "opt", k: "预置案例", v: <>{PRESETS.find((p) => p.key === preset)?.name ?? "—"}</> },
        { kind: "opt", k: "Mock 回放", v: <>{mockMode ? "开" : "关"}</>, toggle: true },
      ]}
      runState={finished ? "done" : started ? "running" : "idle"}
      chatSlot={
        <>
          {/* Hidden template file input — triggered by the 模板 pill in composer */}
          <input
            ref={tplInputRef}
            type="file"
            accept=".doc,.docx"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleTemplatePick([f]);
              e.currentTarget.value = "";
            }}
          />
          <ChatBlk
            title="对话 · 边写边补"
            subTitle="— Refine Chat"
            kBadge={isMock ? "降级 · MOCK" : "1 pending · 3.4 节"}
            messages={messages}
            presets={presetChips}
            composer={{
              pills: composerPills,
              auxLine,
              placeholder: "输入补充信息或 @ 客户名…（演示仅视觉，真实补答走 /refine）",
              attach: {
                accept: ".pdf,.doc,.docx,.xlsx,.png,.jpg",
                multiple: true,
                onPick: handleMaterialsPick,
                title: "上传客户材料（可多选）",
              },
              cta: {
                label: started && !finished ? "生成中…" : started ? "重跑" : "开始生成 ↗",
                disabled: runDisabled,
                onClick: () => runReport(),
                title: runTitle,
              },
            }}
          />
        </>
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
              <span className="hot" key="u">32 项未填</span>,
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
            tip: <>四大板块已成稿（<b>428 / 460</b> 段），外因追问 <b>1</b> 条待补答后局部重跑约 <b>90s</b>。</>,
            ctas: [
              { label: "复核底稿" },
              { label: docxUrl && !docxUrl.startsWith("#") ? "下载 Word ↗" : "导出 Word ↗", primary: true },
            ],
          }}
          coverage={[
            { k: "填写", v: <>428<sub>/460</sub></> },
            { k: "覆盖", v: <>93.5<sub>%</sub></> },
            { k: "未填", v: <>32<sub>项</sub></>, hot: true },
          ]}
          unfilled={{
            k: "未能自动填写 · 典型 3 项",
            items: (<>
              <span className="tag">实控人关联企业名单</span>材料未覆盖 · <span className="tag">担保人净资产</span>需人工补 · <span className="tag">行业景气度口径</span>外因追问
            </>),
          }}
          qc={QC_METRICS}
        />
      }
    />
  );
}
