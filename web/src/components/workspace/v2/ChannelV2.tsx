"use client";

/**
 * ChannelV2 — DOM port of design_mockups/stage5/mockup-v2/channel.html.
 * Lookalike acquisition · 信号驱动 · 3 阶段 Signal / Match / Recommend.
 *
 * SSE event stream wired to streamChannelSearch via withFallback (W1 origin
 * commit a147227) with /mock/channel_run.json fallback on 2s timeout.
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
import { streamChannelSearch } from "@/lib/api";
import { withFallback } from "@/lib/fallback";
import type { ChannelSearchEvent } from "@/lib/channel-types";

const MESSAGES: ChatMessage[] = [
  {
    side: "agent",
    sig: "客.",
    nameZh: "获客·信号搜索",
    nameEn: "Channel",
    ts: "10:15:41",
    ref: "候选 18",
    spineColor: "var(--t-channel)",
    body: <>扫完信号池 <b>42</b> 条，去重后 <b>18</b> 家。<b>5</b> 家本周招「电池模组工程师」，<b>3</b> 家刚发布新能源电机专利，<b>2</b> 家申报真空炉采购。优先推 <b>3 家歌尔同类供应商</b>，已对齐 <em>张主任</em> 持仓偏好。</>,
  },
  {
    side: "user",
    sig: "王.",
    nameZh: "王哲",
    nameEn: "华东客户经理",
    ts: "10:16:02",
    body: <>信号时间线回放近 <b>90</b> 天，招聘触发的单独标黄；<span className="tag">出海企业</span>模板先不看，单拎备份。</>,
  },
  {
    side: "agent",
    sig: "客.",
    nameZh: "获客·信号搜索",
    nameEn: "Channel",
    ts: "10:16:18",
    ref: "rerun match",
    spineColor: "var(--t-channel)",
    body: <>收到。<b>90</b> 天回放已开，招聘信号染黄线；出海模板不参与排名，仅备份。重跑约 <b>60s</b>，<em>top-5 派单榜</em> 11:30 前交你。</>,
  },
];

const INITIAL_SSE_LINES: TraceLine[] = [
  { ts: "10:15:03", stgTag: "sig · 01", stage: "ev", tx: <>✓ <b>RSS 5 源</b> · 42 原始 <span className="src">SRC 新能源情报</span></> },
  { ts: "10:15:18", stgTag: "sig · 02", stage: "ev", tx: <>✓ <b>专利命中</b> 3 家 <span className="src">SRC NIPRP 索引</span></> },
  { ts: "10:15:31", stgTag: "sig · 03", stage: "ev", tx: <>✓ <b>实体对齐去重</b> → <em>18 家</em></> },
  { ts: "10:16:04", stgTag: "mat · 1.4", stage: "gn", tx: <>look-alike <b>top-K=50</b> → <em>18</em> <span className="src">look_alike_v3</span></> },
  { ts: "10:16:22", stgTag: "rec · 2.1", stage: "au", typing: true, tx: <>top-5 已派单 · <b>张主任</b> <em>歌尔同类</em> 优先</> },
];

// Map channel SSE stage → bucket for CSS (s-ev / s-gn / s-au)
function channelStageBucket(stage?: string): "ev" | "gn" | "au" {
  if (!stage) return "gn";
  if (stage === "parse" || stage === "signal_scan" || stage === "aggregate") return "ev";
  if (stage === "enrich" || stage === "pitch") return "gn";
  if (stage === "rank") return "au";
  return "gn";
}

function fmtNowHMS(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function channelEventToLine(evt: ChannelSearchEvent, idx: number): TraceLine | null {
  const ts = fmtNowHMS();
  const tag = (b: "ev" | "gn" | "au") => `${b} · ${String(idx).padStart(2, "0")}`;
  if (evt.event === "stage") {
    const bucket = channelStageBucket(evt.stage);
    return {
      ts,
      stgTag: tag(bucket),
      stage: bucket,
      tx: (
        <>
          ▸ <b>{evt.stage}</b>
          {evt.status ? <em> · {evt.status}</em> : null}
          {evt.message ? <span className="src"> {evt.message}</span> : null}
          {typeof evt.count === "number" ? <> <em>count {evt.count}</em></> : null}
        </>
      ),
    };
  }
  if (evt.event === "done") {
    return {
      ts,
      stgTag: tag("au"),
      stage: "au",
      tx: (
        <>
          ✓ <b>候选就绪</b> · 信号 <em>{evt.metrics?.signalTotal ?? 0}</em> · 企业 <em>{evt.metrics?.companiesFound ?? 0}</em> · 终选 <em>{evt.metrics?.final ?? 0}</em>
        </>
      ),
    };
  }
  if (evt.event === "error") {
    return {
      ts,
      stgTag: tag("au"),
      stage: "au",
      tx: <>✗ <span className="bad">{evt.message}</span></>,
    };
  }
  return null;
}

const SECTIONS: DocSection[] = [
  {
    n: "01", name: "苏州锐鑫精密", en: "Suzhou Ruixin", state: "ok", stateText: "相似度 0.84",
    body: (
      <>
        <p>员工 <span className="num">480</span> 人 / 注册资本 <span className="num">8,000</span> 万元 / 2018 年成立 · 主营 <span className="tag">精密连接器</span> + <span className="tag">车载高压部件</span>，位于苏州工业园区。</p>
        <p><b>90 天信号时间线</b>：2026-03 招聘 <em>电池模组工程师 5 人</em> · 2026-04 公开专利 <em>3 项</em>（车载高压连接器）· 2026-04 申报真空炉 <em>1 台</em> 采购，三类信号叠加命中。</p>
        <p>匹配账户经理 <em>张主任</em>（歌尔持仓同类），推荐 <span className="tag">对公流贷</span> <span className="num">5,000</span> 万 + <span className="tag">保函</span> <span className="num">1,000</span> 万，预计首访日 2026-04-22。</p>
      </>
    ),
  },
  {
    n: "02", name: "无锡晟昱新能源", en: "Wuxi Shengyu", state: "live", stateText: "相似度 0.78 · 黄线", flag: "live",
    body: (
      <>
        <p>员工 <span className="num">320</span> 人 / 注册资本 <span className="num">5,000</span> 万元 · 主营 <span className="tag">新能源电机壳体</span>，位于无锡高新区。</p>
        <p>本周招聘信号触发 <em>7 个新岗位</em>（含研发 3 人 · 工艺 2 人），单周同比激增；专利 & 采购信号尚未同步到位。<span className="pending-mark">招聘信号染黄中 · 等 10:32 回放落地</span></p>
      </>
    ),
  },
  {
    n: "03", name: "常州博瑞电气", en: "Changzhou Borui", state: "ok", stateText: "相似度 0.77",
    body: (
      <>
        <p>员工 <span className="num">210</span> 人 / 注册资本 <span className="num">3,500</span> 万元 · 主营 <span className="tag">车载线束</span> + <span className="tag">逆变器组件</span>，位于常州武进。</p>
        <p><b>90 天信号时间线</b>：专利 + 采购双信号同时触发——2026-02 高压逆变模块 <em>2 项</em> 专利，2026-03 三台数控磨床采购公示，设备扩产迹象明显。</p>
      </>
    ),
  },
  {
    n: "04–18", name: "其余 15 家候选", en: "Long tail 0.72–0.76", state: "pend", stateText: "折叠",
    body: <p>另 <span className="num">15</span> 家候选（相似度 0.72–0.76）已入榜 — 含 <b>常熟贝力斯</b> / <b>昆山卓信</b> / <b>嘉兴泰极</b> 等，每家均附 90 天信号时间线与账户经理推荐。点此展开全列表。</p>,
  },
];

const QC_METRICS: QcMetric[] = [
  { k: "信号去重率", v: "97.6", p: "98%" },
  { k: "实体对齐率", v: "96.1", p: "96%" },
  { k: "画像召回", v: "92.4", p: "92%" },
  { k: "相似度置信", v: "88.3", p: "88%" },
  { k: "账户经理匹配", v: "5/5", p: "100%" },
  { k: "产品适配", v: "94.7", p: "95%" },
  { k: "历史命中", v: "81.2", p: "81%" },
  { k: "重复率", v: "0", p: "100%" },
  { k: "评分一致", v: "86", p: "86%", hot: true },
];

export default function ChannelV2() {
  const [lines, setLines] = useState<TraceLine[]>(INITIAL_SSE_LINES);
  const [isMock, setIsMock] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let idx = INITIAL_SSE_LINES.length;

    const replay = (j: unknown): ChannelSearchEvent[] => {
      const obj = j as {
        run_mock_events?: ChannelSearchEvent[];
        done?: ChannelSearchEvent;
      };
      const out: ChannelSearchEvent[] = [...(obj.run_mock_events ?? [])];
      if (obj.done) out.push(obj.done);
      return out;
    };

    (async () => {
      try {
        for await (const [evt, source] of withFallback<ChannelSearchEvent>(
          (signal) =>
            streamChannelSearch(
              { query: "新能源装备 精密连接器 长三角 专精特新", top_n: 8 },
              signal
            ),
          "/mock/channel_run.json",
          { timeoutMs: 2000, replayEvents: replay, replayIntervalMs: 260 }
        )) {
          if (cancelled) return;
          if (source === "mock") setIsMock(true);
          const line = channelEventToLine(evt, idx++);
          if (line) setLines((prev) => [...prev, line]);
        }
      } catch {
        // keep seed
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <V2Shell
      agent="channel"
      hero={{
        eyebrowText: "CHANNEL AGENT · 信号驱动 lookalike",
        eyebrowAccent: "2 条刚触发 · 账户经理 top-5 已绑定",
        heroTitle: (
          <>
            <span className="cn">新能源装备</span> <em>18 家</em> look-alike，<em>2 条信号</em>刚触发。
          </>
        ),
        heroSub: (
          <>
            候选池从 <span className="num">12,000</span> 家中筛出 <span className="num">18</span> 家相似目标，信号覆盖 <b>招聘</b> · <b>专利</b> · <b>设备采购</b> 三类，每家附 90 天时间线。
            <span className="bullet" />
            <button type="button" className="pill">查看榜单 ↗</button>
            <button type="button" className="pill ghost">派发账户经理</button>
          </>
        ),
      }}
      apHead={{
        zh: "获客 · 信号搜索",
        en: "Channel Lookalike Finder",
        ver: "v4.0",
        metas: [
          { k: "擅长", v: "信号多源聚合 + lookalike 推荐" },
          { k: "当前", v: "top-5 已派单", state: "ok" },
          { k: "今日", v: "6 次 · 全部留痕" },
        ],
        health: "LLM 在线 · DeepSeek",
        cta: { label: "派发账户经理", arrow: "↗" },
      }}
      cap={{ cn: "三阶段", em: "— Signal / Match / Recommend", k: "SESSION · 20260420-1015" }}
      stages={[
        { n: "01", nm: "信号", en: "— Signal", state: "done", sub: <>扫 <b>3</b> 类 RSS · 原始 <b>42</b> 条 · 去重 <b>18</b></> },
        { n: "02", nm: "匹配", en: "— Match", state: "live", sub: <>look-alike 向量 · 相似度 ≥ <b>0.72</b> · 命中 <b>18</b></> },
        { n: "03", nm: "推荐", en: "— Recommend", sub: <>按「<em>账户经理持仓</em> × <em>产品适配</em>」排名 <b>top-5</b></> },
      ]}
      tplTitle={{
        lbl: "选模板",
        hint: <>已选 <b>新能源装备 · signal-ev-v3.1</b> · 信号源 3 类 · 候选阈值 ≥ 0.72 · 切换会重跑</>,
        k: "SIGNAL TEMPLATE",
      }}
      tpls={[
        { key: "ev",  name: "新能源装备", tag: "EV",  meta: "signal-ev-v3.1 · 标杆 12 家", spec: "3 类信号源 · 招聘 / 专利 / 设备采购", on: true },
        { key: "med", name: "医疗器械",   tag: "MED", meta: "signal-med-v2.4 · 标杆 8 家", spec: "NMPA 备案触发 · 临床试验公告" },
        { key: "sp",  name: "专精特新",   tag: "SP",  meta: "signal-sp-v1.8",               spec: "工信部榜单 + 招聘信号" },
        { key: "cbc", name: "出海企业",   tag: "CBC", meta: "signal-cbc-v1.0",              spec: "跨境电商 + 外汇登记" },
      ]}
      intake={[
        { kind: "drop", title: "拖标杆种子企业名单 · 或点右侧选取", sub: "已收 12 家样本 · .csv / .docx · 单份 ≤ 20MB", btn: "选文件" },
        { kind: "opt", on: true, k: "目标行业", v: <>新能源装备 Cleantech</> },
        { kind: "opt", k: "城市范围", v: <>长三角 4 市</> },
        { kind: "opt", k: "Mock 回放", v: <>关</>, toggle: true },
      ]}
      chatSlot={
        <ChatBlk
          title="对话 · 边跑边调"
          subTitle="— Refine Chat"
          kBadge="live · top-5 已派单"
          messages={MESSAGES}
          seeds={[
            { q: "Q1", body: <>解释 <em>信号去重</em>逻辑</> },
            { q: "Q2", body: <>加 <em>专精特新</em>融合</> },
            { q: "Q3", body: <>抄送 <em>授信 Agent3</em></> },
          ]}
          placeholder="继续追问 · 例如：只看长三角且研发人数 ≥ 50…"
        />
      }
      docSlot={
        <>
          <SseBlk
            title={<>事件流 <em>— SSE · signal / match / recommend</em></>}
            kBadge={isMock ? "降级 · MOCK" : "live"}
            lines={lines}
          />
          <DocWrap
            docTitle="候选企业 · 18 家 · 信号时间线"
            docSubtitle="Lookalike Board · signal-ev-v3.1"
            metrics={[
              <>18 家候选</>,
              <>信号覆盖 100%</>,
              <span className="hot">top-5 派发</span>,
              <>相似度 ≥ 0.72</>,
            ]}
            sections={SECTIONS}
          />
        </>
      }
      auditSlot={
        <AuditStrip
          verdict={{
            k: "Verdict · 总体",
            v: <>可派发账户经理 <em>— top-5 已绑定</em></>,
            tip: <><b>18</b> 家候选打分 · <b>3</b> 类信号覆盖 · 相似度 ≥ <b>0.72</b> · 账户经理 <b>5</b> 人各认 <b>1</b> 个。</>,
            ctas: [
              { label: "复核榜单" },
              { label: "派发账户经理 ↗", primary: true },
            ],
          }}
          coverage={[
            { k: "候选",   v: <>18<sub>/12000</sub></> },
            { k: "相似度", v: <>≥72<sub>%</sub></> },
            { k: "派发",   v: <>top-5<sub>绑定</sub></>, hot: true },
          ]}
          unfilled={{
            k: "未能自动填写 · 典型 3 项",
            items: (
              <>
                <span className="tag">出海企业</span>模板暂跳 · <span className="tag">供应商合同证据</span>需二阶段校验 · <span className="tag">账户经理偏好</span>手动微调
              </>
            ),
          }}
          qc={QC_METRICS}
        />
      }
    />
  );
}
