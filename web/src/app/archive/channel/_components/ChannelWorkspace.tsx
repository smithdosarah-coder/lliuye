"use client";

/**
 * /archive/channel · Agent1 获客 (Scout) workspace · 三栏对话式
 * 2026-04-21 H1 · canon 横向迁移（从 Agent6 ReportWorkspace 复用 shell + 右栏换业务 viz）
 *
 * 左 Query / Signals / Recent · 中 Conversation + Composer · 右 Radar + Funnel + Candidates
 *
 * 继承 canon A 章 8 条 primitive
 * Agent tint 注入：.v-archive--canon[data-agent="channel"] { --agent: var(--t-channel) }  (青绿)
 * 业务：look-alike 获客 —— 标杆画像 → 8 信号扫描 → 相似度打分 → Top N 推荐
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent, ChangeEvent, DragEvent } from "react";
import { useAuthStore } from "@/lib/store";
import { DataSourceBadge } from "@/components/shared/DataSourceBadge";
import { CARD_PIN_MIME } from "@/lib/store/whiteboard-store";
import { PANEL_PIN_MIME } from "@/lib/store/panel-canvas-store";
import { LiveFailError, liveFailBannerText, streamSse } from "@/lib/api/_live";
import { type DataSourceKind, normalizeDataSource } from "@/lib/api/_data-source";
import { nextThinkDelayMs, pickReply } from "../_mock/canned-replies";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import {
  CHANNEL_GLOBAL_STATS,
  MOCK_SESSIONS_MAP,
  MOCK_SESSIONS_LIST,
  DEFAULT_SESSION_ID,
  type Candidate,
  type ChannelSession,
  type ConversationMessage,
  type FunnelStage,
  type MatchDimension,
  type MatchSetting,
  type PitchScript,
  type ProductRec,
  type RadarDimension,
  type RecentScoutSession,
  type ScoutQuery,
  type SignalEvent,
  type SignalSource,
} from "@/lib/mock/agent-channel-sessions";

/* PM 2026-05-07 ALL IN 真产品 · 接 codex R1 立场: channel 一线 0 mock · 仅 live · 源挂降级.
   sessionData fallback 用此空对象 · 数组字段空 → panel 内 .find/.map/.reduce 不 crash · 无虚构 candidate */
const EMPTY_SESSION: ChannelSession = {
  id: "empty",
  benchmarkName: "",
  candidateCount: 0,
  stage: "",
  updated: "",
  query: {
    id: "",
    benchmark: "",
    industry: "",
    geo: "",
    scaleRange: "",
    featureTags: [],
    updated: "",
    kbRefs: [],
  } as ScoutQuery,
  signals: [],
  match: {} as MatchSetting,
  conversation: [],
  radar: [],
  funnel: [],
  candidates: [],
  qcCounts: { block: 0, warn: 0, info: 0 },
  recentSessions: [],
};

/* B.6b · 12 维 IdealProfile (后端 agent_channel/ideal_profile.py · IdealProfile12 schema)
   消费 /api/channel/profile 返回的 ideal_profile 字段 */
type IdealProfile12 = {
  industry_focus: string[];
  scale_preference: string[];
  geo_coverage: string[];
  stage: string;
  capital_relation: string;
  business_size: string;
  employee_size: string;
  customer_type: string[];
  product_keywords: string[];
  value_chain_position: string;
  growth_signals: string[];
  risk_signals: string[];
};

type IdealProfileResponse = {
  ideal_profile: IdealProfile12;
  confidence_score: number;
  reasoning_text: string;
};

/* B.6 · 3 类 KB type (per agent-channel-spec.md §C1) */
type KbType = "customer_list" | "policy" | "industry_guide";

type KbUploadResult = {
  kb_id: string;
  kb_type: KbType;
  source_filename: string;
  summary_text: string;
  n_rows?: number;
  n_pages?: number;
  n_paragraphs?: number;
};

type KbUploadStatus = "idle" | "uploading" | "success" | "error";
import { PanelPinHandle } from "@/components/shell/PanelPinHandle";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";
import { EvidenceProvider } from "@/components/evidence";
// Phase B.1.1 hotfix · 删 CHANNEL_EVIDENCE fixtures (codex 复盘抓 · ALL IN 漏修)
// fixtures.ts 硬编"福鼎明辉/F5189/地铁配件" 跟真候选脱钩 · 红线 #3 假证据

/** 截断消息内容作 pin title，避免白板/画布过长；尾部加 …。 */
function msgTitle(raw: string): string {
  const flat = raw.replace(/\s+/g, " ").trim();
  return flat.length > 42 ? `${flat.slice(0, 40)}…` : flat;
}

/** 统一消息 PinHandle props 生成。 */
function msgPinProps(msg: ConversationMessage, speaker: string) {
  return {
    id: `channel:msg:${msg.id}`,
    title: msgTitle(msg.content),
    subtitle: `${speaker} · ${msg.at}`,
    accentVar: "--t-channel",
    agentKey: "channel",
    href: "/archive/channel",
    fullText: msg.content,
  };
}

export default function ChannelWorkspace() {
  /* workspace-state-protocol §2 · 4 gate state model · Phase A worker-A3 (2026-04-29)
     (1) started · (2) selectedSession · (3) liveData · (4) selectedCandidate
     sessionData = liveData ?? mock[selectedSession] · 5 panel 单点派生 */

  const [started, setStarted] = useState<boolean>(false);
  const [selectedSession, setSelectedSession] = useState<string>(DEFAULT_SESSION_ID);
  const [liveData, setLiveData] = useState<ChannelSession | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<string | null>(null);
  /* F-bug-2 · 抽屉 open state 跟 panel 联动 state 拆开
     点企业 → 同时 setSelected + setDrawerOpen(true) · panel 持续联动
     关抽屉 → 仅 setDrawerOpen(false) · selectedCandidate 保留 · panel 不回退
     切 session → setSelected(null) · useEffect 自动关抽屉 */
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  useEffect(() => {
    if (!selectedCandidate) setDrawerOpen(false);
  }, [selectedCandidate]);

  /* PM 2026-05-07 ALL IN 真产品 · 接 codex R1 立场: 一线 0 mock · 生产仅 live ·
     源挂时降级标"旧数据/缺失" 不 fallback 假 candidate.
     sessionData 不再 fallback 到 MOCK_SESSIONS_MAP · 改 EMPTY_SESSION (空数组安全 render)
     panel 渲染条件 started && liveData != null 双重保护 · 没 liveData 显示 empty state */
  const sessionData: ChannelSession = liveData ?? EMPTY_SESSION;
  const s = sessionData;
  const topSim = Math.round((s.candidates[0]?.similarity ?? 0) * 100);
  /* PM 2026-05-07 ALL IN: 删 forceMock state · channel 不再有 mock 切换 · 仅 live 一态 */
  const isLive = liveData !== null;
  /* 件 #2 · data_source SSOT 真消费 (per Q-054 risk #1 + AGENT_IDENTITY).
     默认 "mock" (no run yet) · QueryBar 收 done event 时 setCurrentDataSource(normalize(data.data_source))
     · LiveFailError 时 setCurrentDataSource("mock_fallback") · forceMock toggle 时 "mock_forced". */
  const [currentDataSource, setCurrentDataSource] = useState<DataSourceKind>("mock");
  const [currentProvider, setCurrentProvider] = useState<string | undefined>(undefined);

  /* F-044 · 2026-04-28 · master plan §B.6 · 3 类 KB upload UI
     kbIds[type] = kb_id (uuid) · null = 未上传 · upload 后 setter 写入 */
  const [kbIds, setKbIds] = useState<Record<KbType, string | null>>({
    customer_list: null,
    policy: null,
    industry_guide: null,
  });
  const [kbSummaries, setKbSummaries] = useState<Record<KbType, KbUploadResult | null>>({
    customer_list: null,
    policy: null,
    industry_guide: null,
  });
  const [kbStatus, setKbStatus] = useState<Record<KbType, KbUploadStatus>>({
    customer_list: "idle",
    policy: "idle",
    industry_guide: "idle",
  });
  const [kbErrors, setKbErrors] = useState<Record<KbType, string>>({
    customer_list: "",
    policy: "",
    industry_guide: "",
  });

  /* F-045 · 2026-04-28 · master plan §B.6b · IdealProfile 12 维画像卡 + 用户 confirm
     customer_list 上传完成 → 自动 POST /api/channel/profile → 12 chip + reasoning
     用户点 "开始扫描" → setStarted(true) → 走 /api/channel/run */
  const [idealProfile, setIdealProfile] = useState<IdealProfileResponse | null>(null);
  const [profileFetching, setProfileFetching] = useState(false);
  const [profileError, setProfileError] = useState<string>("");

  /* F-045 · external SSE trigger · profile card "开始扫描" 按钮发 nonce + query · QueryBar 自动 run */
  const [externalTrigger, setExternalTrigger] = useState<{
    input: string;
    nonce: number;
  } | null>(null);

  /* B-banner · streamError 从 QueryBar lift 上来 · 顶部 banner 渲染
     合并 kbErrors 任一非空 → workspace 顶部统一红条提示 + retry/dismiss
     C4 · banner-spec rule 2 · bannerKind 区分 info (mock_fallback warn 黄) vs error (LiveFailError 红) */
  const [streamErrorTop, setStreamErrorTop] = useState<string | null>(null);
  const [bannerKind, setBannerKind] = useState<"info" | "error">("error");
  const aggregatedKbError = (Object.values(kbErrors).find((e) => e) || "");
  const topBannerMessage = streamErrorTop || aggregatedKbError;
  /* aggregatedKbError 是 KB 上传失败 · 强制为 error · stream warning 由 setBannerKind 显式 set */
  const effectiveBannerKind: "info" | "error" =
    aggregatedKbError && !streamErrorTop ? "error" : bannerKind;
  const dismissTopBanner = useCallback(() => {
    setStreamErrorTop(null);
    setBannerKind("error");
    setKbErrors({ customer_list: "", policy: "", industry_guide: "" });
  }, []);

  /* C4 · 给 QueryBar 用的 bundled setter · 让 callback 选 info/error */
  const setStreamWarning = useCallback((msg: string | null) => {
    setStreamErrorTop(msg);
    setBannerKind(msg ? "info" : "error");
  }, []);
  const setStreamFatal = useCallback((msg: string | null) => {
    setStreamErrorTop(msg);
    setBannerKind(msg ? "error" : "error");
  }, []);

  /* derive selected candidate object · sessionData.candidates 已 live-or-mock 单源 */
  const selectedCandidateData: Candidate | null = selectedCandidate
    ? sessionData.candidates.find((c) => c.id === selectedCandidate) ?? null
    : null;

  /* ESC 关 drawer */
  useEffect(() => {
    if (!selectedCandidate) return;
    function onKey(e: globalThis.KeyboardEvent) {
      if (e.key === "Escape") setSelectedCandidate(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedCandidate]);

  /* Step 2 · 2026-04-22 CLI-C
     conversation state hoist 到这里：ConversationPanel 渲染、Composer 提交都走它。
     切 session 时同步 reset 到该 session 的 mock conversation · live SSE 时由 submit append。
     纯 demo · 不接 API · pickReply 走 _mock/canned-replies.ts 关键词 + round-robin。 */
  const [messages, setMessages] = useState<ConversationMessage[]>(s.conversation);

  /* 切 session 时 reset conversation + 清 liveData + 关 drawer · 让 panel 全 swap 干净 */
  const handleSelectSession = useCallback(
    (id: string) => {
      const sess = MOCK_SESSIONS_MAP[id];
      if (!sess) return;
      setSelectedSession(id);
      setMessages(sess.conversation);
      setLiveData(null);
      setSelectedCandidate(null);
    },
    [],
  );

  /* F-044 · master plan §B.6 · 单文件 KB 上传 (multipart) → /api/channel/upload_kb
     成功后写 kbIds[type] · customer_list 触发 IdealProfile 自动抽取 (B.6b) */
  const handleKbUpload = useCallback(
    async (kbType: KbType, file: File) => {
      const apiBase =
        (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) ||
        "";
      setKbStatus((prev) => ({ ...prev, [kbType]: "uploading" }));
      setKbErrors((prev) => ({ ...prev, [kbType]: "" }));
      try {
        const fd = new FormData();
        fd.append("kb_type", kbType);
        fd.append("file", file, file.name);
        const res = await fetch(`${apiBase}/api/channel/upload_kb`, {
          method: "POST",
          body: fd,
        });
        if (!res.ok) {
          const text = await res.text().catch(() => "");
          throw new Error(`HTTP ${res.status}: ${text.slice(0, 120)}`);
        }
        const data = (await res.json()) as KbUploadResult;
        setKbIds((prev) => ({ ...prev, [kbType]: data.kb_id }));
        setKbSummaries((prev) => ({ ...prev, [kbType]: data }));
        setKbStatus((prev) => ({ ...prev, [kbType]: "success" }));

        /* B.6b · customer_list 上传成功 → 自动 POST /api/channel/profile 抽 12 维画像 */
        if (kbType === "customer_list") {
          setProfileFetching(true);
          setProfileError("");
          try {
            const pres = await fetch(`${apiBase}/api/channel/profile`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ kb_id: data.kb_id, kb_type: kbType }),
            });
            if (!pres.ok) {
              const text = await pres.text().catch(() => "");
              throw new Error(`HTTP ${pres.status}: ${text.slice(0, 120)}`);
            }
            const pdata = (await pres.json()) as IdealProfileResponse;
            setIdealProfile(pdata);
          } catch (err) {
            setProfileError(
              err instanceof Error ? err.message : String(err),
            );
          } finally {
            setProfileFetching(false);
          }
        }
      } catch (err) {
        setKbStatus((prev) => ({ ...prev, [kbType]: "error" }));
        setKbErrors((prev) => ({
          ...prev,
          [kbType]: err instanceof Error ? err.message : String(err),
        }));
      }
    },
    [],
  );

  const seq = useRef(0);

  const submit = useCallback((raw: string) => {
    const text = raw.trim();
    if (!text) return;
    seq.current += 1;
    const ts = `${Date.now()}-${seq.current}`;
    const isCmd = text.startsWith("/");
    const userMsg: ConversationMessage = {
      id: `u-${ts}`,
      at: "刚刚",
      kind: isCmd ? "user-command" : "user-reply",
      content: text,
    };
    setMessages((prev) => [...prev, userMsg]);

    /* 2026-04-27 · archive ConversationPanel 真接 LLM (替代 canned-replies mock)
       fetch /api/im/send · target_agent="channel" · 后端用 Agent1 Scout 角色 prompt
       prod 相对 path 走 nginx · dev NEXT_PUBLIC_API_BASE=http://localhost:8000
       fetch fail 在 dev 时 fallback canned · prod 时显占位错误 */
    const thinkingId = `t-${ts}`;
    const thinkingMsg: ConversationMessage = {
      id: thinkingId,
      at: "刚刚",
      kind: "ai-thinking",
      content: "思考中…",
      thinking: { steps: [] },
    };
    setMessages((prev) => [...prev, thinkingMsg]);

    const apiBase =
      (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) ||
      "";
    fetch(`${apiBase}/api/im/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include", // W-FIX2-A2 · 带 zhongan_auth cookie
      body: JSON.stringify({
        message: text,
        thread_id: "archive:channel",
        target_agent: "channel",
      }),
    })
      .then((r) =>
        r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
      )
      .then((data: { reply: string; agent: string }) => {
        const reply = (data.reply || "").trim();
        const aiMsg: ConversationMessage = {
          id: `a-${ts}`,
          at: "刚刚",
          kind: "ai-response",
          content: reply || "(AI 无响应 · 请重试)",
        };
        setMessages((prev) =>
          prev.map((m) => (m.id === thinkingId ? aiMsg : m)),
        );
      })
      .catch((err) => {
        console.warn("[ChannelComposer] LLM fetch failed:", err);
        if (process.env.NODE_ENV !== "development") {
          const errMsg: ConversationMessage = {
            id: `a-${ts}`,
            at: "刚刚",
            kind: "ai-response",
            content: "(AI 暂时不可用 · 请稍后重试)",
          };
          setMessages((prev) =>
            prev.map((m) => (m.id === thinkingId ? errMsg : m)),
          );
          return;
        }
        const delay = nextThinkDelayMs();
        window.setTimeout(() => {
          const reply = pickReply(text);
          const aiMsg: ConversationMessage = {
            id: `a-${ts}`,
            at: "刚刚",
            kind: "ai-response",
            content: reply.content,
            fieldRef: reply.fieldRef,
            sectionDiff: reply.sectionDiff,
          };
          setMessages((prev) =>
            prev.map((m) => (m.id === thinkingId ? aiMsg : m)),
          );
        }, delay);
      });
  }, []);

  /* Phase B.2 §9 (PM 2026-05-10) · evidence drawer 真 wire ·
     live 数据触发 · 从 sessionData.signals (SSE done envelope `signals` panel) 派生 EvidenceItem
     · 不再用 CHANNEL_EVIDENCE fixture · 不引入硬编"福鼎明辉" 等假证据
     · 派生规则: 每条 SignalSource → ref_id=`signal-${source.id}` · snippet=`${label} · ${hits} 命中 · 覆盖率 ${coverage}%` */
  const liveEvidenceItems = useMemo(() => {
    if (!isLive) return [];
    return sessionData.signals.map((src) => ({
      source: src.note ? `signal://${src.key} · ${src.note}` : `signal://${src.key}`,
      snippet: `${src.label} · ${src.hits} 命中 · 覆盖率 ${src.coverage}% · 频次 ${src.freq}`,
      ref_id: `signal-${src.id}`,
      confidence: Math.min(1, Math.max(0, src.coverage / 100)),
      meta: {
        entity: src.label,
        signal_key: src.key,
        signal_status: src.status,
        signal_hits: src.hits,
      },
    }));
  }, [isLive, sessionData.signals]);

  return (
    <EvidenceProvider
      items={liveEvidenceItems}
      unfilledFields={[]}
    >
    <div
      data-view="archive-channel"
      className="ch-v2"
      data-started={started ? "yes" : "no"}
    >
      {/* B-banner · workspace 顶部统一错误条 · streamError + kbError 合并 · retry/dismiss */}
      {topBannerMessage ? (
        <div
          role={effectiveBannerKind === "error" ? "alert" : "status"}
          data-testid={
            effectiveBannerKind === "info"
              ? "channel-pilot-banner-mock-fallback"
              : "channel-pilot-banner-live-fail"
          }
          data-banner-kind={effectiveBannerKind}
          className={`ch-error-banner ch-error-banner--${effectiveBannerKind}`}
        >
          <span className="ch-error-banner__icon" aria-hidden>⚠</span>
          <span className="ch-error-banner__text">
            <b>{effectiveBannerKind === "info" ? "演示模式" : "操作失败"}</b>
            <span className="ch-error-banner__detail">{topBannerMessage}</span>
          </span>
          <button
            type="button"
            className="ch-error-banner__dismiss"
            onClick={dismissTopBanner}
            aria-label="关闭提示"
          >
            ×
          </button>
        </div>
      ) : null}
      <ChannelHero
        sessionData={s}
        topSim={topSim}
        isLive={isLive}
        currentDataSource={currentDataSource}
        currentProvider={currentProvider}
      />
      {/* F-044 · master plan §B.6 · 3 类 KB upload UI (客户名录 / 政策 / 行业指引) */}
      <KbUploadStrip
        kbIds={kbIds}
        kbStatus={kbStatus}
        kbSummaries={kbSummaries}
        kbErrors={kbErrors}
        onUpload={handleKbUpload}
      />
      {/* F-045 · master plan §B.6b · IdealProfile 12 维画像卡 + "开始扫描" CTA
         显示条件: 正在抽取 · 已抽取 · 抽取失败 (任一即显) · null/false/empty 均不显 */}
      {(profileFetching || idealProfile !== null || profileError !== "") && (
        <IdealProfileCard
          profile={idealProfile}
          loading={profileFetching}
          error={profileError}
          onStartScan={() => {
            const trig = idealProfileToQuery(idealProfile);
            if (!trig) return;
            setExternalTrigger({ input: trig, nonce: Date.now() });
          }}
        />
      )}
      <QueryBar
        sessionData={s}
        selectedSession={selectedSession}
        onSelectSession={handleSelectSession}
        setLiveData={setLiveData}
        setMessages={setMessages}
        setSelectedCandidate={setSelectedCandidate}
        setStarted={setStarted}
        externalTrigger={externalTrigger}
        onStreamError={setStreamFatal}
        onStreamWarning={setStreamWarning}
        onDataSource={(kind, provider) => {
          setCurrentDataSource(kind);
          setCurrentProvider(provider);
        }}
      />
      {started && liveData != null ? (
        <>
          <FunnelStrip sessionData={s} />
          <div className="ch-cross">
            <div className="ch-canvas">
              <div className="ch-canvas-top">
                <RadarPanel sessionData={s} selectedCandidate={selectedCandidate} />
                <CandidatesPanel
                  sessionData={s}
                  isLive={isLive}
                  onSelectCandidate={(id) => {
                    setSelectedCandidate(id);
                    setDrawerOpen(true);
                  }}
                />
              </div>
              <ConversationPanel sessionData={s} messages={messages} />
            </div>
            <aside className="ch-aside">
              <SignalTimelinePanel sessionData={s} selectedCandidate={selectedCandidate} />
            </aside>
          </div>
          <ChannelComposer sessionData={s} onSubmit={submit} />

          {/* Phase B.1.1 hotfix (PM 2026-05-10 抓 production bug · ALL IN 漏修):
           * 删 CHANNEL_EVIDENCE.summary 硬编"福鼎明辉/F5189/地铁配件订单" · 跟真候选脱钩
           * 红线 #3 无证据 claim · 真闭环 (live 数据出来时由 evidence drawer 渲染) */}
        </>
      ) : (
        <section
          aria-label="等待触发"
          data-testid="channel-empty-state"
          style={{
            padding: "44px 32px 38px 32px",
            background:
              "color-mix(in srgb, var(--chalk) 55%, transparent)",
            borderRadius: "var(--r-md)",
            border: "1px dashed var(--ink-14)",
            margin: "20px 0",
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 28,
          }}
        >
          {/* 左 · 自由查询 (RM 主路径) */}
          <div>
            <div
              style={{
                fontFamily: "var(--cjk)",
                fontSize: 11,
                color: "var(--ink-48)",
                letterSpacing: ".08em",
                textTransform: "uppercase",
                marginBottom: 8,
              }}
            >
              形态 · A · 自由查询
            </div>
            <h3
              style={{
                fontFamily: "var(--display)",
                fontSize: 18,
                color: "var(--ink)",
                fontWeight: 500,
                margin: "0 0 10px 0",
              }}
            >
              输入业务诉求 → 真接 Tavily/AI 搜出 look-alike
            </h3>
            <p
              style={{
                fontFamily: "var(--cjk)",
                fontSize: 13,
                color: "var(--ink-65)",
                lineHeight: 1.65,
                margin: "0 0 14px 0",
              }}
            >
              上方搜索框输入业务诉求 (e.g.{" "}
              <strong style={{ color: "var(--accent)" }}>
                找江苏中型 SaaS · ARR 1-3 亿 · 专精特新
              </strong>
              ) · 多源信源 (工商 + 司法 + 招投标 + 资质 + 行情) 实搜 · 9 维评分 · 字段级溯源.
            </p>
            <div
              style={{
                display: "flex",
                gap: 8,
                flexWrap: "wrap",
              }}
            >
              {[
                "江苏中型 SaaS · ARR 1-3 亿",
                "长三角专精特新小巨人 · 工业软件",
                "B 轮已完成 · CFO 公开活跃",
              ].map((q) => (
                <button
                  key={q}
                  type="button"
                  data-testid="channel-empty-quick"
                  onClick={() => setExternalTrigger({ input: q, nonce: Date.now() })}
                  style={{
                    fontFamily: "var(--cjk)",
                    fontSize: 12,
                    padding: "6px 12px",
                    borderRadius: 999,
                    border: "1px solid var(--ink-20)",
                    background: "transparent",
                    color: "var(--ink-65)",
                    cursor: "pointer",
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
          {/* 右 · 一键示例 (channel-kb 优质 batch · PM 真意) */}
          <div
            style={{
              borderLeft: "1px solid var(--ink-14)",
              paddingLeft: 28,
            }}
          >
            <div
              style={{
                fontFamily: "var(--cjk)",
                fontSize: 11,
                color: "var(--accent)",
                letterSpacing: ".08em",
                textTransform: "uppercase",
                marginBottom: 8,
                fontWeight: 600,
              }}
            >
              形态 · B · 一键示例 · 推荐
            </div>
            <h3
              style={{
                fontFamily: "var(--display)",
                fontSize: 18,
                color: "var(--ink)",
                fontWeight: 500,
                margin: "0 0 10px 0",
              }}
            >
              银行营销倾向 docx → 真后端跑一遍
            </h3>
            <p
              style={{
                fontFamily: "var(--cjk)",
                fontSize: 13,
                color: "var(--ink-65)",
                lineHeight: 1.65,
                margin: "0 0 14px 0",
              }}
            >
              用 <code style={{ fontFamily: "var(--mono)", color: "var(--accent)" }}>
                channel-kb/marketing-preferences/
              </code> 真上传 · 派生 seed query · 走真 Tavily/AI 跑全管线 · 候选/评分/匹配理由全 LLM 抽 · 不写死.
            </p>
            <p
              style={{
                fontFamily: "var(--cjk)",
                fontSize: 12,
                color: "var(--ink-48)",
                lineHeight: 1.6,
                margin: "0 0 14px 0",
              }}
            >
              已加载: 2026-Q1-重点拓展.docx · 2026-Q2-区域重点.docx · 2026年度行业组合建议.docx
            </p>
            <div style={{ fontFamily: "var(--cjk)", fontSize: 12, color: "var(--ink-48)" }}>
              ↑ 上方切到 <strong style={{ color: "var(--accent)" }}>"一键示例"</strong> tab 即可点 3 档难度运行
            </div>
          </div>
        </section>
      )}
      {/* F-042 · master plan §B.4 + §B.4b + §B.4c · candidate detail drawer */}
      <CandidateDetailDrawer
        candidate={drawerOpen ? selectedCandidateData : null}
        sessionData={s}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
    </EvidenceProvider>
  );
}

/* ── Hero ────────────────────────────────────────────── */

function ChannelHero({
  sessionData,
  topSim,
  isLive,
  currentDataSource,
  currentProvider,
}: {
  sessionData: ChannelSession;
  topSim: number;
  isLive: boolean;
  /* 件 #2 · data_source SSOT 真消费 · 显式 5-enum trust model badge */
  currentDataSource: DataSourceKind;
  currentProvider?: string;
}) {
  const s = sessionData;
  return (
    <header className="rpt-hero">
      <div className="rpt-hero-left">
        <div className="rpt-hero-badge" aria-hidden>◈</div>
        <div>
          {/* PM bug #3 fix · hero code 中文优先 · 英文 codename 保留 */}
          <div className="rpt-hero-code">AGENT · 01 · 获客 Scout</div>
          <h1 className="rpt-hero-title">
            获客 <em>Scout.</em>
          </h1>
          <div className="rpt-hero-sub">
            {isLive
              ? `${s.benchmarkName} · ${s.candidateCount} 家候选 · ${s.stage} · 首推相似度 ${topSim}%`
              : "等待业务诉求 · 输入诉求开始真接多源信源搜索"}
          </div>
        </div>
      </div>
      {/* PM 2026-05-07 ALL IN 真产品 · 删 ModePill · 没 liveData 时不渲染 DataSourceBadge (待机不展示 mock 标识)
         有 liveData 时才显示当前数据源真假 (live/cached/mock_fallback 三态) */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        {isLive && (
          <DataSourceBadge
            kind={currentDataSource}
            provider={currentProvider}
            testId="channel-data-source-badge"
          />
        )}
        <div className="rpt-hero-stats">
          <Stat label="本周处理" value={CHANNEL_GLOBAL_STATS.weeklyProcessed} />
          <Stat label="命中率" value={CHANNEL_GLOBAL_STATS.hitRate} />
          <Stat label="平均时长" value={CHANNEL_GLOBAL_STATS.avgDuration} />
        </div>
      </div>
    </header>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rpt-stat">
      <div className="rpt-stat-label">{label}</div>
      <div className="rpt-stat-value">{value}</div>
    </div>
  );
}

/* ── 左栏 · Query 画像 ──────────────────────────────── */

function QueryPanel({ sessionData }: { sessionData: ChannelSession }) {
  const q = sessionData.query;
  return (
    <section className="rpt-panel rpt-panel--tpl">
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">QUERY · 标杆画像</div>
          <h3 className="rpt-panel-title">{q.benchmark}</h3>
        </div>
        <span className="rpt-panel-meta">{q.updated}</span>
      </div>
      <div className="rpt-panel-body ch-q-body">
        <dl className="ch-q-meta">
          <div>
            <dt>行业</dt>
            <dd>{q.industry}</dd>
          </div>
          <div>
            <dt>地域</dt>
            <dd>{q.geo}</dd>
          </div>
          <div>
            <dt>规模</dt>
            <dd>{q.scaleRange}</dd>
          </div>
        </dl>
        <div className="ch-q-tags-wrap">
          <div className="ch-q-tags-lbl">12 维特征</div>
          <div className="ch-q-tags">
            {q.featureTags.map((t) => (
              <span key={t} className="ch-q-tag">
                {t}
              </span>
            ))}
          </div>
        </div>
        <div className="ch-q-kb">
          <div className="ch-q-kb-lbl">知识库命中</div>
          {q.kbRefs.map((k) => (
            <div key={k.id} className="ch-q-kb-row">
              <span className="name">{k.label}</span>
              <span className="hit">← {k.hitBy}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── 左栏 · Signals 信号源 ─────────────────────────── */

const SIG_STATUS_LABEL: Record<SignalSource["status"], string> = {
  active: "在线",
  degraded: "降级",
  off: "关",
};

function SignalsPanel({ sessionData }: { sessionData: ChannelSession }) {
  const sigs = sessionData.signals;
  const active = sigs.filter((x) => x.status === "active").length;
  const totalHits = sigs.reduce((a, b) => a + b.hits, 0);
  return (
    <section className="rpt-panel rpt-panel--mat">
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">SIGNALS · 8 信号源</div>
          <h3 className="rpt-panel-title">
            {active} / {sigs.length} 活跃
          </h3>
        </div>
        <span className="rpt-panel-meta">{totalHits.toLocaleString()} 命中</span>
      </div>
      <div className="rpt-panel-body ch-sig-body">
        {sigs.map((g) => (
          <article
            key={g.id}
            className="ch-sig-card"
            data-status={g.status}
          >
            <header className="ch-sig-head">
              <span className="ch-sig-kind" data-k={g.key}>
                {g.label}
              </span>
              <span className="ch-sig-status" data-s={g.status}>
                {SIG_STATUS_LABEL[g.status]}
              </span>
            </header>
            <div className="ch-sig-stats">
              <div>
                <span className="num">{g.hits.toLocaleString()}</span>
                <span className="lbl">命中</span>
              </div>
              <div>
                <span className="num">{g.coverage}%</span>
                <span className="lbl">覆盖</span>
              </div>
              <div>
                <span className="num">{(g.weight * 100).toFixed(0)}</span>
                <span className="lbl">权重</span>
              </div>
            </div>
            <div className="ch-sig-bar" aria-hidden>
              <div
                className="ch-sig-bar-fill"
                style={{ width: `${g.coverage}%` }}
              />
            </div>
            <div className="ch-sig-meta">
              <span>{g.freq}</span>
              {g.note && <span className="note">· {g.note}</span>}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

/* ── 左栏 · Recent sessions ───────────────────────── */

function RecentPanel({ sessionData }: { sessionData: ChannelSession }) {
  const recent = sessionData.recentSessions;
  return (
    <section className="rpt-panel rpt-panel--tl">
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">RECENT · 近期扫描</div>
          <h3 className="rpt-panel-title">{recent.length} 条</h3>
        </div>
        <select
          className="rpt-tl-switch"
          aria-label="切换 session"
          defaultValue={sessionData.id}
        >
          {recent.map((r) => (
            <option key={r.id} value={r.id}>
              {r.benchmark}
            </option>
          ))}
        </select>
      </div>
      <div className="rpt-panel-body rpt-tl-body">
        <ol className="ch-rc-list">
          {recent.map((r) => (
            <RecentRow key={r.id} row={r} />
          ))}
        </ol>
      </div>
    </section>
  );
}

function RecentRow({ row }: { row: RecentScoutSession }) {
  const pct = Math.round(row.progress * 100);
  const isDone = row.progress >= 1;
  return (
    <li className="ch-rc-row" data-done={isDone}>
      <span className="rpt-tl-bar" aria-hidden />
      <div className="rpt-tl-row">
        <span className="rpt-tl-kind">{isDone ? "完成" : "进行中"}</span>
        <span className="rpt-tl-at">{row.updated}</span>
      </div>
      <div className="rpt-tl-label">{row.benchmark}</div>
      <div className="ch-rc-bar" aria-hidden>
        <div className="ch-rc-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="rpt-tl-detail">
        {row.stage} · {pct}%
      </div>
    </li>
  );
}

/* ── 中栏 · Conversation ────────────────────────────── */

function ConversationPanel({
  sessionData,
  messages,
}: {
  sessionData: ChannelSession;
  messages: ConversationMessage[];
}) {
  const s = sessionData;
  const blurb = `${messages.length} 条对话 · 候选 ${s.candidateCount} · 阻断 ${s.qcCounts.block}`;
  /* 新消息进来自动滚到底部（Composer 提交后看到自己的话） */
  const bodyRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = bodyRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages.length]);
  /* PM 2026-05-07 ALL IN v2: 实时流版面控高 · 永远固定可视区 + 永远滚动 + 永远显展开按钮
     不再按消息数 trigger · 即使少消息也限高 · 多消息时点"展开全部"放高
     UX 简单: 默认看最近的 · 想看历史用展开 (放高) 或 scroll
     Phase B.2 (PM 2026-05-10 §7 信息密度): 默认展开 · 短对话不顶高 · 长对话减少 1 次点击 */
  const [expanded, setExpanded] = useState(true);
  const total = messages.length;
  return (
    <section className="rpt-panel rpt-panel--conv" data-testid="channel-pilot-conversation">
      <PanelPinHandle
        id="channel:conversation"
        title="获客对话"
        subtitle={`获客 · ${s.benchmarkName}`}
        accentVar="--t-channel"
        agentKey="channel"
        href="/archive/channel"
        blurb={blurb}
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">CONVERSATION · 对话协作</div>
          <h3 className="rpt-panel-title">
            {s.benchmarkName} · {total} 条
          </h3>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span className="rpt-panel-meta">
            候选 {s.candidateCount} · 阻断 {s.qcCounts.block}
          </span>
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            data-testid="channel-conversation-toggle"
            style={{
              fontFamily: "var(--cjk)",
              fontSize: 11,
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid var(--ink-20)",
              background: "transparent",
              color: "var(--accent)",
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            {expanded ? "折叠" : "展开全部"}
          </button>
        </div>
      </div>
      <div
        ref={bodyRef}
        className="rpt-panel-body rpt-conv-body"
        style={{
          /* 永远限高 · 默认 240px 显约 3-4 条 · 展开后 720px · 都可滚动 */
          maxHeight: expanded ? 720 : 240,
          overflowY: "auto",
        }}
      >
        <ol className="rpt-conv-list">
          {messages.map((m) => (
            <ConversationItem key={m.id} msg={m} />
          ))}
        </ol>
      </div>
    </section>
  );
}

function ConversationItem({ msg }: { msg: ConversationMessage }) {
  switch (msg.kind) {
    case "system-event":
      return <SystemEventMsg msg={msg} />;
    case "ai-question":
      return <AiQuestionMsg msg={msg} />;
    case "ai-response":
      return <AiResponseMsg msg={msg} />;
    case "ai-thinking":
      return <AiThinkingMsg msg={msg} />;
    case "user-reply":
      return <UserReplyMsg msg={msg} />;
    case "user-command":
      return <UserCommandMsg msg={msg} />;
    default:
      return null;
  }
}

function SystemEventMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--sys">
      <MessagePinHandle {...msgPinProps(msg, "系统事件")} />
      <span className="rpt-msg-sys-chip">
        <span aria-hidden>◎</span> {msg.content}
      </span>
      <span className="rpt-msg-at">{msg.at}</span>
    </li>
  );
}

function AiQuestionMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--ai rpt-msg--ask wc-msg wc-msg--ai">
      <MessagePinHandle {...msgPinProps(msg, "AI · Scout")} />
      <div className="wc-msg-avatar wc-msg-avatar--ai" aria-hidden>◈</div>
      <div className="wc-msg-bubble wc-msg-bubble--ai wc-msg-bubble--ask">
        <span className="wc-msg-bubble-ic" aria-hidden>?</span>
        <span className="wc-msg-bubble-text">{msg.content}</span>
      </div>
      <div className="wc-msg-foot wc-msg-foot--ai">
        {msg.fieldRef && <span className="wc-msg-fieldref">{msg.fieldRef}</span>}
        <span className="wc-msg-at">{msg.at}</span>
      </div>
    </li>
  );
}

function AiResponseMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--ai wc-msg wc-msg--ai">
      <MessagePinHandle {...msgPinProps(msg, "AI · Scout")} />
      <div className="wc-msg-avatar wc-msg-avatar--ai" aria-hidden>◈</div>
      <div className="wc-msg-bubble wc-msg-bubble--ai">
        <div className="wc-msg-bubble-text">{msg.content}</div>
        {msg.sectionDiff && (
          <div className="rpt-msg-diff">
            <div className="rpt-msg-diff-lbl">
              更新 {msg.sectionDiff.sectionAnchor}
            </div>
            <div className="rpt-msg-diff-after">{msg.sectionDiff.after}</div>
          </div>
        )}
      </div>
      <div className="wc-msg-foot wc-msg-foot--ai">
        {msg.fieldRef && <span className="wc-msg-fieldref">{msg.fieldRef}</span>}
        <span className="wc-msg-at">{msg.at}</span>
      </div>
    </li>
  );
}

function AiThinkingMsg({ msg }: { msg: ConversationMessage }) {
  const [open, setOpen] = useState(false);
  const steps = msg.thinking?.steps ?? [];
  /* Step 2 · 当 steps 为空（demo 占位场景）时，展示三点 typing 指示，不渲染折叠按钮。
     已有 mock 数据带 steps 的走原有可折叠 UI。 */
  const isTyping = steps.length === 0;
  return (
    <li className="rpt-msg rpt-msg--ai rpt-msg--thinking wc-msg wc-msg--ai">
      <MessagePinHandle {...msgPinProps(msg, "AI · thinking")} />
      <div className="wc-msg-avatar wc-msg-avatar--ai wc-msg-avatar--thinking" aria-hidden>◈</div>
      <div className="wc-msg-bubble wc-msg-bubble--think">
        {isTyping ? (
          <div
            className="wc-msg-typing"
            role="status"
            aria-live="polite"
            aria-label={msg.content}
          >
            <span /><span /><span />
          </div>
        ) : (
          <>
            <button
              type="button"
              className="wc-msg-think"
              aria-expanded={open}
              onClick={() => setOpen((v) => !v)}
            >
              <span className="wc-msg-think-text">{msg.content}</span>
              <span className="wc-msg-think-caret" aria-hidden>
                {open ? "▾" : "▸"}
              </span>
            </button>
            {open && (
              <ol className="rpt-msg-steps">
                {steps.map((st, i) => (
                  <li key={i} className="rpt-msg-step">
                    <div className="rpt-msg-step-lbl">
                      <span className="rpt-msg-step-n">{i + 1}</span>
                      {st.label}
                    </div>
                    <ul className="rpt-msg-step-evs">
                      {st.evidences.map((e, j) => (
                        <li key={j} className="rpt-msg-step-ev">
                          {e}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
      </div>
      <div className="wc-msg-foot wc-msg-foot--ai">
        <span className="wc-msg-at">{msg.at}</span>
      </div>
    </li>
  );
}

/* PM bug #3 · P1 · conversation hardcode '王' / '王哲' 改 currentUser 动态
   per useAuthStore · 切李华登录显李华 · 切周敏显周敏 · 不再固定 */
function _useUserAvatar(): { avatar: string; name: string; subtitle: string } {
  const u = useAuthStore((s) => s.currentUser);
  if (!u) return { avatar: "?", name: "未登录", subtitle: "未登录用户" };
  return {
    avatar: u.avatar || u.name.slice(0, 1),
    name: u.name,
    subtitle: `${u.team} · ${u.name}`,
  };
}

function UserReplyMsg({ msg }: { msg: ConversationMessage }) {
  const { avatar, subtitle } = _useUserAvatar();
  return (
    <li className="rpt-msg rpt-msg--user wc-msg wc-msg--user">
      <MessagePinHandle {...msgPinProps(msg, subtitle)} />
      <div className="wc-msg-bubble wc-msg-bubble--user">{msg.content}</div>
      <div className="wc-msg-avatar wc-msg-avatar--user" aria-hidden>{avatar}</div>
      <div className="wc-msg-foot wc-msg-foot--user">
        <span className="wc-msg-at">{msg.at}</span>
      </div>
    </li>
  );
}

function UserCommandMsg({ msg }: { msg: ConversationMessage }) {
  const { avatar, subtitle } = _useUserAvatar();
  return (
    <li className="rpt-msg rpt-msg--user rpt-msg--cmd wc-msg wc-msg--user">
      <MessagePinHandle {...msgPinProps(msg, `${subtitle} · /command`)} />
      <div className="wc-msg-bubble wc-msg-bubble--user wc-msg-bubble--cmd">
        <code>{msg.content}</code>
      </div>
      <div className="wc-msg-avatar wc-msg-avatar--user" aria-hidden>{avatar}</div>
      <div className="wc-msg-foot wc-msg-foot--user">
        <span className="wc-msg-at">{msg.at}</span>
      </div>
    </li>
  );
}

/* ── 中栏 · Composer ────────────────────────────────── */

type ComposerHint = "idle" | "slash" | "mention" | "industry";

function ChannelComposer({
  sessionData,
  onSubmit,
}: {
  sessionData: ChannelSession;
  onSubmit: (text: string) => void;
}) {
  const [value, setValue] = useState("");
  const [hint, setHint] = useState<ComposerHint>("idle");
  const [dropHover, setDropHover] = useState(false);
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 180) + "px";
  }, [value]);

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    /* 类微信：纯 Enter 直接发；Shift+Enter 才换行；⌘/Ctrl+Enter 也发（保留快捷键） */
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function handleChange(e: ChangeEvent<HTMLTextAreaElement>) {
    const v = e.target.value;
    setValue(v);
    const last = v.slice(-1);
    if (last === "/") setHint("slash");
    else if (last === "@") setHint("mention");
    else if (last === "#") setHint("industry");
    else setHint("idle");
  }

  function submit() {
    const text = value.trim();
    if (!text) return;
    onSubmit(text);
    setValue("");
    setHint("idle");
  }

  /* ── Drop target：接 PANEL_PIN / CARD_PIN / text/plain ──
     读到 payload 后把 title 以 `@引用:<title> ` 形式插入 textarea 当前光标位
     （无焦点就 append 到末尾）；阻止 textarea 原生 drop 吃掉 text/plain。 */
  function hasPin(e: DragEvent<HTMLDivElement>): boolean {
    const ts = Array.from(e.dataTransfer.types);
    return ts.includes(PANEL_PIN_MIME) || ts.includes(CARD_PIN_MIME);
  }

  function onDragEnter(e: DragEvent<HTMLDivElement>) {
    if (!hasPin(e)) return;
    e.preventDefault();
    setDropHover(true);
  }
  function onDragOver(e: DragEvent<HTMLDivElement>) {
    if (!hasPin(e)) return;
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
    if (!dropHover) setDropHover(true);
  }
  function onDragLeave(e: DragEvent<HTMLDivElement>) {
    // 只有真正离开 slot 边界才清（子元素间切换 relatedTarget 仍在内部）
    const node = e.currentTarget;
    const next = e.relatedTarget as Node | null;
    if (!next || !node.contains(next)) setDropHover(false);
  }
  function onDrop(e: DragEvent<HTMLDivElement>) {
    if (!hasPin(e)) return;
    e.preventDefault();
    e.stopPropagation();
    setDropHover(false);
    let title = "";
    const rawPanel = e.dataTransfer.getData(PANEL_PIN_MIME);
    const rawCard = e.dataTransfer.getData(CARD_PIN_MIME);
    try {
      if (rawPanel) title = (JSON.parse(rawPanel) as { title?: string }).title ?? "";
      else if (rawCard) title = (JSON.parse(rawCard) as { title?: string }).title ?? "";
    } catch {
      title = e.dataTransfer.getData("text/plain");
    }
    if (!title) return;
    insertAtCursor(`@引用:${title} `);
  }

  function insertAtCursor(fragment: string) {
    const ta = taRef.current;
    if (!ta) {
      setValue((v) => v + fragment);
      return;
    }
    const start = ta.selectionStart ?? value.length;
    const end = ta.selectionEnd ?? value.length;
    const next = value.slice(0, start) + fragment + value.slice(end);
    setValue(next);
    // 光标移到插入片段之后
    requestAnimationFrame(() => {
      if (!taRef.current) return;
      const pos = start + fragment.length;
      taRef.current.focus();
      taRef.current.setSelectionRange(pos, pos);
    });
  }

  const sigCount = sessionData.signals.length;
  const tagCount = sessionData.query.featureTags.length;

  const slotCls = [
    "rpt-composer-slot",
    "rpt-composer",
    dropHover ? "rpt-composer--drop-hover" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={slotCls}
      data-hint={hint}
      onDragEnter={onDragEnter}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <div className="rpt-composer-bar">
        <textarea
          ref={taRef}
          className="rpt-composer-ta"
          placeholder="提问或下指令 · 输入 / 触发命令 · @ 引用信号源 · # 换行业"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKey}
          rows={1}
        />
        <button
          type="button"
          className="rpt-composer-send"
          onClick={submit}
          disabled={!value.trim()}
        >
          <span>发送</span>
          <kbd>↩</kbd>
        </button>
      </div>
      <div className="rpt-composer-hints">
        <span className="rpt-composer-hint" data-active={hint === "slash"}>
          <kbd>/</kbd> 指令 · confirm / expand / exclude
        </span>
        <span className="rpt-composer-hint" data-active={hint === "mention"}>
          <kbd>@</kbd> 信号源 · {sigCount} 个
        </span>
        <span className="rpt-composer-hint" data-active={hint === "industry"}>
          <kbd>#</kbd> 画像特征 · {tagCount} 维
        </span>
      </div>
    </div>
  );
}

/* ── 区域 1 · Query 输入条（顶部全宽） ───────────────── */

type ChannelStreamEvent = {
  event?: string;
  stage?: string;
  status?: string;
  pct?: number;
  message?: string;
  candidates?: unknown[];
  tags?: unknown[];
  count?: number;
  total?: number;
  route?: string;
  routes_done?: number;
  routes_total?: number;
  metrics?: { signalTotal?: number; companiesFound?: number; final?: number };
  data_source?: string;
  [k: string]: unknown;
};

/* F-005 Phase 3 · 2026-04-27 · friendly stream event formatter
   替代 raw JSON dump · 让 user 看人话 (PARSE/SIGNAL_SCAN/AGGREGATE/ENRICH/PITCH/RANK/DONE/ERROR) */
function formatChannelEvent(evt: ChannelStreamEvent): {
  stage: string;
  msg: string;
  pct?: number;
} {
  const baseStage = String(evt.stage ?? evt.event ?? "·").toUpperCase();
  if (evt.event === "stage") {
    const status = evt.status;
    if (evt.stage === "parse") {
      if (status === "running") return { stage: baseStage, msg: "解析用户意图..." };
      if (status === "done") {
        const tags = (evt.tags as unknown[] | undefined) ?? [];
        return { stage: baseStage, msg: `已解析 ${tags.length} 个特征标签` };
      }
    }
    if (evt.stage === "signal_scan") {
      if (status === "running") return { stage: baseStage, msg: "并行扫描 5 路信号源 (中标 / 认可 / 技术 / 增长 / 获奖)..." };
      if (status === "done") {
        const count = evt.count;
        /* V2 issue 3 · data_source 已 normalize 为 envelope enum (live/mock_forced/mock_fallback) ·
           provider_source 是 backend 单独透传的 provider 标识 (e.g. "tavily") · 优先显 provider 细节 */
        const provider = evt.provider_source as string | undefined;
        const ds = provider ?? evt.data_source ?? "mock";
        return { stage: baseStage, msg: `扫描完 · ${count ?? "?"} 条信号 · 来源 ${ds}` };
      }
    }
    if (evt.stage === "aggregate") {
      if (status === "running") return { stage: baseStage, msg: "实体聚合去重..." };
      if (status === "done") return { stage: baseStage, msg: `聚合完 · ${evt.total ?? "?"} 个实体` };
    }
    if (evt.stage === "enrich") {
      if (status === "running") return { stage: baseStage, msg: "企查查补全工商信息 + 产品匹配..." };
      if (status === "done") return { stage: baseStage, msg: "工商 + 产品匹配完成" };
    }
    if (evt.stage === "pitch") {
      if (status === "running") return { stage: baseStage, msg: "推荐配比生成..." };
      if (status === "done") return { stage: baseStage, msg: "推荐生成完" };
    }
    if (evt.stage === "rank") {
      if (status === "running") return { stage: baseStage, msg: "信号密度排序..." };
      if (status === "done") return { stage: baseStage, msg: "排序完成" };
    }
  }
  if (evt.event === "progress") {
    const route = String(evt.route ?? "?");
    const done = evt.routes_done;
    const total = evt.routes_total;
    return {
      stage: "PROGRESS",
      msg: `${route} · ${done ?? 0}/${total ?? 0}`,
      pct: total ? Math.round(((done ?? 0) / total) * 100) : undefined,
    };
  }
  if (evt.event === "done") {
    const cs = (evt.candidates as unknown[] | undefined) ?? [];
    const m = evt.metrics;
    return { stage: "DONE", msg: `完成 · ${cs.length} 候选 · ${m?.companiesFound ?? "?"} 命中` };
  }
  if (evt.event === "error") {
    return { stage: "ERROR", msg: String(evt.message ?? "AI 解析失败 · 请重试") };
  }
  return { stage: baseStage, msg: String(evt.message ?? "进行中…") };
}

/* F-043 · master plan §B.5b · backend candidate (snake_case) → 前端 Candidate (含 drawer 三件套)
   消费 agent_channel/sse_extras.py + realtime_stream._build_final_output 的 done event
   - Q-041 fix: industry/geo/scale 不再 "—" fallback 而是用 backend 真值 (extras.industry 等)
   - drawer 4 区数据: match_dimensions / product_recommendations / pitch_scripts / timeline */
function normalizeBackendCandidate(
  c: Record<string, unknown>,
  index: number,
): Candidate {
  const id = String(c.id ?? c.uscc ?? `live-${index}`);
  const name = String(c.name ?? c.company_name ?? "(未命名)");

  /* signals · backend [{type, title, detail, date, source, url}] · 既给 timeline 也给 chip 列表 */
  const rawSignals = Array.isArray(c.signals)
    ? (c.signals as Array<unknown>)
    : [];

  /* signal chip list · CandidateCard 的命中信号 chip (字符串数组) */
  const signalChips: string[] = rawSignals
    .map((s) => {
      if (typeof s === "string") return s;
      if (s && typeof s === "object") {
        const r = s as Record<string, unknown>;
        return String(r.title ?? r.label ?? r.type ?? r.kind ?? "");
      }
      return "";
    })
    .filter(Boolean);

  /* signal_types fallback (legacy snake_case · 当 signals 缺时) */
  const fallbackSignalChips =
    signalChips.length === 0 && Array.isArray(c.signal_types)
      ? (c.signal_types as unknown[]).map(String)
      : signalChips;

  /* timeline · backend signals 转 SignalEvent[] (drawer §一 信号时间线 + Timeline panel) */
  const timeline: SignalEvent[] = rawSignals
    .filter((s): s is Record<string, unknown> => s !== null && typeof s === "object")
    .map((s, j) => {
      const type = String(s.type ?? s.kind ?? "news");
      const kindMap: Record<string, SignalEvent["kind"]> = {
        bidding: "bid-win",
        recognition: "policy",
        tech: "policy",
        growth: "fund",
        award: "policy",
        news: "news",
        biz: "biz-change",
        legal: "legal",
        tax: "tax",
        recruit: "recruit",
        fund: "fund",
        policy: "policy",
      };
      const kind = (kindMap[type] ?? "news") as SignalEvent["kind"];
      const url = String(s.url ?? "");
      const sourceLabel = String(s.source ?? "外网");
      return {
        id: `live-${id}-tl-${j}`,
        at: String(s.date ?? ""),
        kind,
        title: String(s.title ?? ""),
        detail: String(s.detail ?? ""),
        source: { label: sourceLabel, url: url || undefined },
        severity: "neu" as SignalEvent["severity"],
      };
    });

  /* 匹配维度 chip (B.4b · backend: [{dim_name, hit_evidence, score}]) */
  const matchDimensions: MatchDimension[] = Array.isArray(c.match_dimensions)
    ? (c.match_dimensions as Array<Record<string, unknown>>).map((m, j) => ({
        id: String(m.id ?? `live-${id}-md-${j}`),
        dim_name: String(m.dim_name ?? m.dim ?? ""),
        display: String(
          m.display ??
            m.label ??
            `${m.dim_name ?? ""} · ${m.hit_evidence ?? ""}`,
        ),
        hit_evidence: String(m.hit_evidence ?? m.evidence_source ?? ""),
        score: typeof m.score === "number" ? (m.score as number) : 0,
      }))
    : [];

  /* Top3 产品 (B.4c · backend: [{product_name, fit_score, intro, category}]) */
  const productRecommendations: ProductRec[] = Array.isArray(
    c.product_recommendations,
  )
    ? (c.product_recommendations as Array<Record<string, unknown>>).map(
        (p, j) => ({
          id: String(p.id ?? `live-${id}-prod-${j}`),
          product_name: String(p.product_name ?? p.name ?? ""),
          fit_score:
            typeof p.fit_score === "number" ? (p.fit_score as number) : 0,
          intro: String(p.intro ?? p.category ?? ""),
          amount_range:
            typeof p.amount_range === "string"
              ? (p.amount_range as string)
              : undefined,
          rate_band:
            typeof p.rate_band === "string"
              ? (p.rate_band as string)
              : undefined,
        }),
      )
    : [];

  /* 切入话术 (B.4c · backend: [{customer_name_placeholder, script_text, source}]) */
  const pitchScripts: PitchScript[] = Array.isArray(c.pitch_scripts)
    ? (c.pitch_scripts as Array<Record<string, unknown>>).map((p, j) => ({
        id: String(p.id ?? `live-${id}-pitch-${j}`),
        customer_name_placeholder: String(
          p.customer_name_placeholder ?? "{客户名}",
        ),
        script_text: String(p.script_text ?? p.text ?? ""),
        product_ref:
          typeof p.product_ref === "string"
            ? (p.product_ref as string)
            : undefined,
      }))
    : [];

  return {
    id,
    name,
    similarity:
      typeof c.similarity === "number"
        ? (c.similarity as number)
        : typeof c.match_score === "number"
        ? (c.match_score as number)
        : 0,
    /* Q-041 fix · industry/geo/scale 用 backend 真值 (sse_extras.extract_metadata 返) */
    industry: String(c.industry ?? "—"),
    geo: String(c.geo ?? c.region ?? "—"),
    scale: String(c.scale ?? c.scale_band ?? "—"),
    signals: fallbackSignalChips,
    riskTags: Array.isArray(c.riskTags)
      ? (c.riskTags as unknown[]).map(String)
      : Array.isArray(c.risk_tags)
      ? (c.risk_tags as unknown[]).map(String)
      : [],
    products: Array.isArray(c.products)
      ? (c.products as unknown[]).map(String)
      : Array.isArray(c.recommended_products)
      ? (c.recommended_products as unknown[]).map(String)
      : productRecommendations.map((p) => p.product_name),
    /* B.4 · drawer 三件套 + timeline */
    timeline,
    match_dimensions: matchDimensions,
    product_recommendations: productRecommendations,
    pitch_scripts: pitchScripts,
  };
}

/* C2 · workspace-state-protocol §2 · backend done event → 整 ChannelSession (5 panel 单源消费)
   shared/sse_envelope.py make_done(panels=...) 把 panels expand 到 done event 顶层 (扁平 · 非嵌套 envelope) ·
   故这里直接读 evt.candidates / evt.radar / evt.signals / evt.funnel / evt.match_dimensions /
   evt.product_recommendations / evt.pitch_scripts (CHANNEL_PANEL_KEYS 7 keys).
   tplFallback: backend 阶段性输出 panel 字段缺时 (C3 之前) · 用 mock 模板兜底 · 视觉不空 panel */
function normalizeBackendDone(
  evt: Record<string, unknown>,
  tplFallback: ChannelSession,
): ChannelSession {
  const candidatesRaw = Array.isArray(evt.candidates)
    ? (evt.candidates as Array<Record<string, unknown>>)
    : [];
  const candidates = candidatesRaw.map((c, i) => normalizeBackendCandidate(c, i));

  const radar = Array.isArray(evt.radar) && (evt.radar as unknown[]).length > 0
    ? (evt.radar as RadarDimension[])
    : tplFallback.radar;
  const signals = Array.isArray(evt.signals) && (evt.signals as unknown[]).length > 0
    ? (evt.signals as SignalSource[])
    : tplFallback.signals;
  const funnel = Array.isArray(evt.funnel) && (evt.funnel as unknown[]).length > 0
    ? (evt.funnel as FunnelStage[])
    : tplFallback.funnel;
  /* V3 fix · ConversationPanel 从 done envelope 派生 (codex review issue 1 根因 fix) ·
     CHANNEL_PANEL_KEYS 8th key "conversation" · 当前 backend 默认 [] · 缺/空时 fallback
     tplFallback.conversation (mock session 模板的对话) · A4-channel AI 复盘 turn 落地后真填 */
  const conversation =
    Array.isArray(evt.conversation) && (evt.conversation as unknown[]).length > 0
      ? (evt.conversation as ConversationMessage[])
      : tplFallback.conversation;

  return {
    ...tplFallback,
    id: "live",
    benchmarkName: "实时搜索",
    candidates: candidates.length > 0 ? candidates : tplFallback.candidates,
    candidateCount: candidates.length || tplFallback.candidateCount,
    stage: "已扫描",
    radar,
    signals,
    funnel,
    conversation,
  };
}

function QueryBar({
  sessionData,
  selectedSession,
  onSelectSession,
  setLiveData,
  setMessages,
  setSelectedCandidate,
  setStarted,
  externalTrigger,
  onStreamError,
  onStreamWarning,
  onDataSource,
}: {
  sessionData: ChannelSession;
  selectedSession: string;
  onSelectSession: (id: string) => void;
  /* C2 · 改 setLive(Candidate[]|null) → setLiveData(ChannelSession|null) · 整 session 形态注入 */
  setLiveData: (s: ChannelSession | null) => void;
  /* V2 issue 1 · 与 setLiveData 一起 set live conversation · 防 ConversationPanel stale on mock */
  setMessages: (msgs: ConversationMessage[]) => void;
  /* V2 issue 1 · live 注入时关 drawer · 防 stale candidate id 指 mock session */
  setSelectedCandidate: (id: string | null) => void;
  setStarted: (v: boolean) => void;
  /* F-045 · IdealProfile card "开始扫描" · external trigger · 不需要 user 再 click QueryBar */
  externalTrigger?: { input: string; nonce: number } | null;
  /* B-banner · 上抛 stream error 给 workspace 顶部 banner · QueryBar 内 inline error 删除 */
  onStreamError?: (msg: string | null) => void;
  /* C4 · banner-spec rule 2 · 上抛 stream warning (mock_fallback / Tavily 0 命中) · 黄色 info banner */
  onStreamWarning?: (msg: string | null) => void;
  /* 件 #2 · data_source SSOT · done event 收 normalize 后回报 + provider_source 透传 */
  onDataSource?: (kind: DataSourceKind, provider?: string) => void;
}) {
  const q = sessionData.query;
  /* F-005 · 2026-04-27 双模式实装:
     · 历史 session select onChange → 切到对应 mock session (parent ChannelWorkspace 切 sessionData)
     · 自由 textbox onSubmit → fetch /api/channel/run SSE · 真调 DeepSeek + Tavily
     F-041 · 2026-04-28 · master plan B.1+B.2 · 5 sessions select 真切全 panel */
  const [input, setInput] = useState(
    "找做工业软件的 SaaS 公司 · B 轮后 · 华东 · 年营收 1-3 亿"
  );
  const [streaming, setStreaming] = useState(false);
  const [streamEvents, setStreamEvents] = useState<ChannelStreamEvent[]>([]);
  const [streamError, setStreamError] = useState<string | null>(null);
  /* Phase B.2 真意 reframe (PM 2026-05-10) · 形态切换 toggle:
     · "free"  · 自由查询 (用户输入 query → /api/channel/run 真 Tavily/LLM)
     · "sample" · 一键示例 (channel-kb 派生 seed → /api/channel/demo/run 真 Tavily/LLM)
     两形态都跑真后端 · 区别是 input 来源 · 不是数据真假 */
  const [inputMode, setInputMode] = useState<"free" | "sample">("free");
  /* demo_context event payload · sample 形态展示当前 sample 来源 + 派生 query (透明) */
  const [demoContext, setDemoContext] = useState<{
    scenarioId: string;
    sampleFiles: string[];
    seedQuery: string;
  } | null>(null);

  /* PB#5 · AbortController · 组件卸载/切 session/重新触发时 abort 进行中 SSE · 防僵尸连接 */
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  /* Phase B.2 真意 reframe (PM 2026-05-10) · /api/channel/demo/run 改真后端 ·
     与旧 B.1 fixture event 路径区别:
     - 旧 B.1: yield 写死 candidates/signals from data/mock/workspace/channel/scenarios/<id>.json
     - 新 B.2: load channel-kb marketing-preferences docx → seed query → 真 Tavily/LLM
     scenario_id 现仅决定从 channel-kb seed query list 取第几条 · 结果由 backend 真跑产生 */
  async function runDemoScenario(scenarioId: "easy" | "medium" | "hard") {
    if (streaming) return;
    setStarted(true);
    setStreaming(true);
    setStreamEvents([]);
    setStreamError(null);
    setDemoContext(null);
    onStreamError?.(null);
    /* PB#5 · cancel 之前未完成的 SSE (e.g. 用户连点 demo 按钮) */
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    const apiBase =
      (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) ||
      "";
    try {
      await streamSse(
        `${apiBase}/api/channel/demo/run`,
        { scenario_id: scenarioId },
        (sseEvt) => {
          if (ac.signal.aborted) return;
          const data = sseEvt.data as ChannelStreamEvent;
          setStreamEvents((prev) => [...prev, data]);
          /* Phase B.2 · demo_context event · 透出 sample 来源 + 派生 query · 演示透明 */
          if ((data as Record<string, unknown>).event === "demo_context") {
            const d = data as Record<string, unknown>;
            setDemoContext({
              scenarioId: String(d.scenario_id ?? scenarioId),
              sampleFiles: Array.isArray(d.sample_files)
                ? (d.sample_files as string[])
                : [],
              seedQuery: String(d.derived_seed_query ?? ""),
            });
          }
          /* Phase B.2 · backend yield 'error' event (typed banner) · 不 throw HTTP error
             触发: TAVILY_KEY_MISSING_FOR_DEMO / DEMO_KB_EMPTY / DEMO_SCENARIO_INVALID */
          if ((data as Record<string, unknown>).event === "error") {
            const d = data as Record<string, unknown>;
            const code = String(d.code ?? "DEMO_ERROR");
            const msg = String(d.message ?? "演示后端报错");
            setStreamError(`⚠️ [${code}] ${msg}`);
            onStreamError?.(`⚠️ [${code}] ${msg}`);
            /* TAVILY 缺时 trust model 一级降级 banner */
            onDataSource?.("mock_fallback");
            return;
          }
          /* Phase B.2 · backend stage event status="warning" · Tavily silent fallback 透明化 */
          if (sseEvt.type === "stage" && data.status === "warning" && typeof data.message === "string") {
            onStreamWarning?.(`⚠️ ${data.message}`);
          }
          if (sseEvt.type === "done") {
            const live = normalizeBackendDone(
              data as Record<string, unknown>,
              sessionData,
            );
            setLiveData(live);
            setMessages(live.conversation);
            setSelectedCandidate(null);
            /* Phase B.2 · demo run 现走真后端 · data_source 由 run_channel_search_stream 决定 ·
               默认 "live" (Tavily 真搜成功) · Tavily fallback → "mock_fallback" · 不再硬编 mock_forced */
            const rawDs = (data as Record<string, unknown>).data_source;
            const kind = rawDs ? normalizeDataSource(rawDs) : "live";
            const provider = (data as Record<string, unknown>).provider_source as string | undefined;
            onDataSource?.(kind, provider);
            /* done envelope.warnings · backend mock_fallback 透传 · 顶部 banner 二级提示 */
            const wlist = (data as Record<string, unknown>).warnings;
            if (Array.isArray(wlist) && wlist.length > 0) {
              onStreamWarning?.(`⚠️ ${String(wlist[0])}`);
            }
          }
        },
        { signal: ac.signal },
      );
    } catch (err) {
      /* PB#5 · AbortError 是预期 (组件卸载 / 重新触发) · 不显 banner */
      if (err instanceof DOMException && err.name === "AbortError") return;
      if (err instanceof LiveFailError) {
        const msg = liveFailBannerText(err, "Channel /api/channel/demo/run");
        setStreamError(msg);
        onStreamError?.(msg);
        /* 件 #2 · live 失败 → trust model 一级降级 (banner-spec rule 1) */
        onDataSource?.("mock_fallback");
      } else {
        const msg = err instanceof Error ? err.message : String(err);
        setStreamError(msg);
        onStreamError?.(msg);
        onDataSource?.("mock_fallback");
      }
    } finally {
      if (!ac.signal.aborted) setStreaming(false);
    }
  }

  async function runRealSearch(queryOverride?: string) {
    const queryText = (queryOverride ?? input).trim();
    if (!queryText || streaming) return;
    setStarted(true); // #3 · 触发 ChannelWorkspace render 完整 panel
    setStreaming(true);
    setStreamEvents([]);
    setStreamError(null);
    onStreamError?.(null);
    /* PB#5 · cancel 之前未完成的 SSE (e.g. 用户连点 search 按钮) */
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    /* C2 · streamSse 替代内联 res.body.getReader() · LiveFailError 走顶部 banner (banner-spec rule 1)
       done event 走 normalizeBackendDone(evt, tplFallback) 整 ChannelSession 注入 setLiveData */
    const apiBase =
      (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) ||
      "";
    try {
      await streamSse(
        `${apiBase}/api/channel/run`,
        { query: queryText, mock: false, top_n: 8 },
        (sseEvt) => {
          if (ac.signal.aborted) return;
          const data = sseEvt.data as ChannelStreamEvent;
          setStreamEvents((prev) => [...prev, data]);
          /* C4 banner-spec rule 2 · backend stage event status="warning" → 顶部黄条
             触发源:Tavily key 缺 / TavilyClient init 失败 / 5 路 0 命中 · realtime_stream._parallel_signal_search_core */
          if (sseEvt.type === "stage" && data.status === "warning" && typeof data.message === "string") {
            onStreamWarning?.(`⚠️ ${data.message}`);
          }
          if (sseEvt.type === "done") {
            const live = normalizeBackendDone(
              data as Record<string, unknown>,
              sessionData,
            );
            setLiveData(live);
            /* V2 issue 1 · 与 setLiveData 一起 swap · ConversationPanel / drawer 不留 stale */
            setMessages(live.conversation);
            setSelectedCandidate(null);
            /* done envelope.warnings · backend mock_fallback 透传 · 顶部 banner 二级提示 */
            const wlist = (data as Record<string, unknown>).warnings;
            if (Array.isArray(wlist) && wlist.length > 0) {
              onStreamWarning?.(`⚠️ ${String(wlist[0])}`);
            }
            /* 件 #2 · data_source SSOT · run 走 backend canon · 默认 live · provider_source 透出 */
            const rawDs = (data as Record<string, unknown>).data_source;
            const kind = rawDs ? normalizeDataSource(rawDs) : "live";
            const provider = (data as Record<string, unknown>).provider_source as string | undefined;
            onDataSource?.(kind, provider);
          }
        },
        { signal: ac.signal },
      );
    } catch (err) {
      /* PB#5 · AbortError 是预期 (组件卸载 / 重新触发) · 不显 banner */
      if (err instanceof DOMException && err.name === "AbortError") return;
      if (err instanceof LiveFailError) {
        const msg = liveFailBannerText(err, "Channel /api/channel/run");
        setStreamError(msg);
        onStreamError?.(msg);
        /* 件 #2 · live 失败 → trust model 一级降级 (banner-spec rule 1) */
        onDataSource?.("mock_fallback");
      } else {
        const msg = err instanceof Error ? err.message : String(err);
        setStreamError(msg);
        onStreamError?.(msg);
        onDataSource?.("mock_fallback");
      }
    } finally {
      if (!ac.signal.aborted) setStreaming(false);
    }
  }

  /* B-2 click-to-fire · dropdown 仅 set pending 选择 · 显式 button 触发切换 */
  const [pendingSessionId, setPendingSessionId] = useState<string>(selectedSession);
  function onSessionSelectChange(e: ChangeEvent<HTMLSelectElement>) {
    setPendingSessionId(e.target.value);
  }
  function onApplySessionSwitch() {
    /* F-041 · "切换演示" button → mock 模式 · 切 parent state · 清 stream 残留
       parent.handleSelectSession 会 reset conversation + setLiveData(null) */
    if (!pendingSessionId || pendingSessionId === selectedSession) return;
    setStarted(true);
    setStreamEvents([]);
    setStreamError(null);
    onSelectSession(pendingSessionId);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      void runRealSearch();
    }
  }

  /* F-045 · external trigger: IdealProfile "开始扫描" button → 写 input + 自动 run
     query 直接通过参数传 · 不依赖 setInput flush (避免 closure stale state) */
  const lastNonceRef = useRef<number>(-1);
  useEffect(() => {
    if (!externalTrigger) return;
    if (externalTrigger.nonce === lastNonceRef.current) return;
    lastNonceRef.current = externalTrigger.nonce;
    setInput(externalTrigger.input);
    void runRealSearch(externalTrigger.input);
    /* eslint-disable-next-line react-hooks/exhaustive-deps */
  }, [externalTrigger]);

  return (
    <section className="rpt-panel ch-querybar">
      <div className="ch-querybar-head">
        <div>
          <div className="rpt-panel-eyebrow">QUERY · 形态切换</div>
          <h3 className="rpt-panel-title ch-querybar-title">
            一句话描述要找的企业 · <em>两形态都跑真后端 (Tavily + AI)</em>
          </h3>
        </div>
        {/* Phase B.2 (PM 2026-05-10) · 形态切换 segmented control · 不是 ModePill 切假
            · 都跑真后端 · 区别仅 input 来源 (用户输入 vs channel-kb 派生) */}
        <div
          className="ch-input-mode"
          role="tablist"
          aria-label="输入形态切换"
          style={{
            display: "inline-flex",
            border: "1px solid var(--ink-14)",
            borderRadius: 999,
            padding: 3,
            background: "color-mix(in srgb, var(--chalk) 60%, transparent)",
            fontFamily: "var(--cjk)",
            fontSize: 12,
          }}
        >
          {[
            { key: "free", label: "自由查询", hint: "RM 输入业务诉求" },
            { key: "sample", label: "一键示例", hint: "channel-kb 优质 batch 派生" },
          ].map((opt) => {
            const active = inputMode === opt.key;
            return (
              <button
                key={opt.key}
                type="button"
                role="tab"
                aria-selected={active}
                title={opt.hint}
                onClick={() => setInputMode(opt.key as "free" | "sample")}
                disabled={streaming}
                data-testid={`input-mode-${opt.key}`}
                style={{
                  padding: "6px 14px",
                  borderRadius: 999,
                  border: "none",
                  background: active ? "var(--ink)" : "transparent",
                  color: active ? "var(--chalk)" : "var(--ink-65)",
                  fontFamily: "inherit",
                  fontSize: 12,
                  cursor: streaming ? "not-allowed" : "pointer",
                  fontWeight: active ? 600 : 400,
                  transition: "background 120ms",
                }}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>
      {inputMode === "free" ? (
        <div className="ch-querybar-body">
          <input
            type="text"
            className="ch-querybar-input"
            placeholder="自然语言描述业务诉求 · 真接 AI 解析 + 多源信源 (工商/司法/招投标/资质/行情) 搜出 look-alike"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={streaming}
          />
          <button
            type="button"
            className="ch-querybar-btn"
            data-testid="scout-search"
            onClick={() => void runRealSearch()}
            disabled={!input.trim() || streaming}
          >
            <span>{streaming ? "AI 解析中…" : "AI 搜索"}</span>
            <span className="kbd">{streaming ? "···" : "⌘↩"}</span>
          </button>
        </div>
      ) : (
        <div
          className="ch-querybar-sample"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
            padding: "14px 18px",
            background: "color-mix(in srgb, var(--chalk) 40%, transparent)",
            border: "1px dashed var(--ink-14)",
            borderRadius: "var(--r-md)",
          }}
        >
          <div
            style={{
              fontFamily: "var(--cjk)",
              fontSize: 13,
              color: "var(--ink-65)",
              lineHeight: 1.7,
            }}
          >
            从 <code style={{ fontFamily: "var(--mono)", color: "var(--accent)" }}>
              data/mock/channel-kb/marketing-preferences/
            </code> 真读银行营销倾向 docx · 派生 seed query · 走真 Tavily/AI 跑一遍 · 候选/评分/匹配理由全 LLM 抽 · 不写死.
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {(["easy", "medium", "hard"] as const).map((sid) => (
              <button
                key={sid}
                type="button"
                onClick={() => void runDemoScenario(sid)}
                disabled={streaming}
                data-testid={`scout-sample-${sid}`}
                style={{
                  fontFamily: "var(--cjk)",
                  fontSize: 13,
                  padding: "8px 18px",
                  borderRadius: 999,
                  border: "1px solid var(--accent)",
                  background: "var(--accent)",
                  color: "var(--chalk)",
                  cursor: streaming ? "not-allowed" : "pointer",
                  fontWeight: 500,
                }}
              >
                {streaming ? "AI 跑中…" : `运行示例 · ${sid === "easy" ? "简单" : sid === "medium" ? "中等" : "复杂"}`}
              </button>
            ))}
          </div>
          {demoContext && (
            <div
              data-testid="scout-demo-context"
              style={{
                fontFamily: "var(--cjk)",
                fontSize: 12,
                color: "var(--ink-48)",
                lineHeight: 1.6,
                paddingTop: 6,
                borderTop: "1px solid var(--ink-14)",
              }}
            >
              <div>
                <strong style={{ color: "var(--ink-65)" }}>Sample 文件:</strong>{" "}
                {demoContext.sampleFiles.length > 0
                  ? demoContext.sampleFiles.join(" · ")
                  : "(无)"}
              </div>
              <div>
                <strong style={{ color: "var(--ink-65)" }}>派生 seed query:</strong>{" "}
                <code style={{ fontFamily: "var(--mono)", color: "var(--accent)" }}>
                  {demoContext.seedQuery || "(无)"}
                </code>
              </div>
            </div>
          )}
        </div>
      )}
      <div className="ch-querybar-tags">
        <span className="lbl">AI 解析的特征 · 12 维</span>
        <div className="tags">
          {q.featureTags.map((t) => (
            <span key={t} className="tag">
              {t}
            </span>
          ))}
        </div>
      </div>
      {/* B-banner · streamError 已上抛到 workspace 顶部 banner · 此处仅渲事件流 */}
      {streamEvents.length > 0 && (
        <div className="ch-querybar-stream" data-testid="scout-live-stream">
          <div className="ch-querybar-stream-head">
            ▶ AI 实时流 ·{" "}
            {inputMode === "sample"
              ? "/api/channel/demo/run · 真后端跑 channel-kb 派生 query"
              : "/api/channel/run · 真后端跑 RM 输入 query"}
          </div>
          {(
            <ul className="ch-querybar-stream-list">
              {streamEvents.map((evt, i) => {
                const f = formatChannelEvent(evt);
                return (
                  <li key={i} className="ch-querybar-stream-row">
                    <span className="stage">{f.stage}</span>
                    <span className="msg">{f.msg}</span>
                    {typeof f.pct === "number" && (
                      <span className="pct">{f.pct}%</span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

/* ── 顶栏 · Funnel 5 阶段横条 ───────────────────────── */

function FunnelStrip({ sessionData }: { sessionData: ChannelSession }) {
  const s = sessionData;
  const funnel = s.funnel;
  const max = Math.max(...funnel.map((f) => f.count));
  return (
    <section className="rpt-panel ch-funnel-strip" data-testid="channel-pilot-funnel">
      <div className="ch-funnel-strip-head">
        <span className="eyebrow">FUNNEL · 5 阶段扫描</span>
        <span className="flow">
          {funnel[0].count.toLocaleString()} <span className="arr">→</span>{" "}
          {funnel[funnel.length - 1].count} <span className="tail">候选</span>
        </span>
      </div>
      <ol className="ch-funnel-strip-list">
        {funnel.map((f, i) => {
          const pct = Math.round((f.count / max) * 100);
          return (
            <li key={f.id} className="ch-funnel-strip-cell" data-i={i}>
              <div className="ch-funnel-strip-n">{i + 1}</div>
              <div className="ch-funnel-strip-lbl">{f.label}</div>
              <div className="ch-funnel-strip-count">{f.count.toLocaleString()}</div>
              <div className="ch-funnel-strip-bar" aria-hidden>
                <div className="ch-funnel-strip-fill" style={{ width: `${pct}%` }} />
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

/* ── 区域 2 左 · Radar 独立面板 ──────────────────────── */

/* PM 2026-05-07 ALL IN step 2.4a · 后端 sse_extras.build_radar_8axis 给每家 candidate 算 8 维 dict
   前端 adapter: dict → RadarDimension[] · benchmark 默认 P50=50 · quadrant 按 axis 名派生
   切候选时 RadarView 数据真变 (不再 session 共用) · 解 PM "左右两侧不会随点击企业改变" 痛点 */
function candidateRadarToDimensions(
  radar_8axis: Record<string, number> | undefined,
): RadarDimension[] | null {
  if (!radar_8axis || Object.keys(radar_8axis).length === 0) return null;
  /* axis name → quadrant 派生 (粗略 · 仅影响列表 chip 颜色 · 雷达图本身不依赖) */
  const quadrantMap: Record<string, RadarDimension["quadrant"]> = {
    "信号密度": "base",
    "近期活跃度": "base",
    "行业匹配": "market",
    "区域匹配": "market",
    "规模匹配": "market",
    "资质含金量": "bonus",
    "技术强度": "bonus",
    "相似度": "market",
  };
  return Object.entries(radar_8axis).map(([axis, score]) => ({
    axis,
    score,
    benchmark: 50,
    quadrant: quadrantMap[axis] ?? "base",
    note: `${axis} ${score} 分 (vs P50 50)`,
  }));
}

function RadarPanel({
  sessionData,
  selectedCandidate,
}: {
  sessionData: ChannelSession;
  /* F-bug · 父级选中企业变 → 雷达图 top + 数据跟随 */
  selectedCandidate: string | null;
}) {
  const s = sessionData;
  const top =
    (selectedCandidate ? s.candidates.find((c) => c.id === selectedCandidate) : null) ??
    s.candidates[0];
  /* 优先用候选自己的 8 维 (后端 sse_extras 算) · 没数据 fallback session 共用 radar */
  const candidateRadarRaw = (top as { radar_8axis?: Record<string, number> })?.radar_8axis;
  const candidateRadar = candidateRadarToDimensions(candidateRadarRaw);
  const radarToShow = candidateRadar ?? s.radar;
  return (
    <section className="rpt-panel ch-radar-panel" data-testid="channel-pilot-radar">
      <PanelPinHandle
        id="channel:radar"
        title="营销优先级雷达"
        subtitle={`获客 · ${top?.name ?? "—"}`}
        accentVar="--t-channel"
        agentKey="channel"
        href="/archive/channel"
        blurb={`8 维 P50 对标 · 该企业均分 ${Math.round(
          radarToShow.reduce((a, d) => a + d.score, 0) / (radarToShow.length || 1),
        )}`}
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">RADAR · 营销优先级 8 维</div>
          <h3 className="rpt-panel-title">{top?.name} · P50 对标</h3>
        </div>
        <span className="rpt-panel-meta">B++ 方案</span>
      </div>
      <div className="rpt-panel-body">
        <RadarView radar={radarToShow} />
      </div>
    </section>
  );
}

/* ── 区域 2 右 · 候选企业列表 ────────────────────────── */

function CandidatesPanel({
  sessionData,
  isLive,
  onSelectCandidate,
}: {
  sessionData: ChannelSession;
  /* C1 · workspace-state-protocol §2 · sessionData 已 live-or-mock 单源 · isLive 仅控 UI 标识 */
  isLive: boolean;
  /* F-042 · click 回调 · 父级 setSelectedCandidate 触发 drawer */
  onSelectCandidate?: (id: string) => void;
}) {
  const s = sessionData;
  const cs = s.candidates;
  return (
    <section
      className="rpt-panel ch-cand-panel"
      data-mode={isLive ? "live" : "mock"}
      data-testid="channel-pilot-candidates"
    >
      <PanelPinHandle
        id="channel:candidates"
        title="候选企业 Top 推荐"
        subtitle={`获客 · 共 ${cs.length} 家${isLive ? " · live" : ""}`}
        accentVar="--t-channel"
        agentKey="channel"
        href="/archive/channel"
        blurb={`Top ${cs.length} · 阈值 ${(s.match.similarity * 100).toFixed(0)}% · 首推 ${cs[0]?.name ?? "—"}`}
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">
            CANDIDATES · Top 推荐{isLive ? " · LIVE" : ""}
          </div>
          <h3 className="rpt-panel-title">
            Top {cs.length} · 共 {isLive ? cs.length : s.candidateCount} 家
          </h3>
          {/* Sprint 5 D1-2 · 90 秒画像 affordance · 用户可点 Top N 任一卡 → 信号时间线下拉切换 (per PM bug #5 反馈)
              不只第一家可交互 · CandidatesView (line 2063) 全部 onSelect · SignalTimelinePanel (line 2105) dropdown 切换 */}
          <p
            className="rpt-panel-hint"
            data-testid="channel-cand-hint"
            style={{ fontSize: 12, opacity: 0.78, margin: "4px 0 0 0", lineHeight: 1.5 }}
          >
            ⓘ 全部 {cs.length} 家可点 · 切换信号时间线下拉看不同候选 · 90 秒内 AI 给齐画像
          </p>
        </div>
        <div className="rpt-panel-meta">
          阈值 {(s.match.similarity * 100).toFixed(0)}%
        </div>
      </div>
      <div className="rpt-panel-body">
        <CandidatesView candidates={cs} onSelectCandidate={onSelectCandidate} />
      </div>
    </section>
  );
}

/* ── 右栏 · Radar + Funnel + Candidates ─────────────── */

const OUTPUT_ACTIONS = [
  { key: "export", glyph: "⇩", label: "导出", title: "导出 Top 推荐列表 (.xlsx)" },
  { key: "crm",    glyph: "↗", label: "CRM",  title: "推送到 CRM · 待跟进" },
  { key: "assign", glyph: "☰", label: "分配", title: "分配给客户经理" },
  { key: "rerun",  glyph: "⟳", label: "重扫", title: "调参后重新扫描" },
] as const;

function ScoutOutputPanel({ sessionData }: { sessionData: ChannelSession }) {
  const s = sessionData;
  const [tab, setTab] = useState<"radar" | "funnel" | "cand">("radar");

  return (
    <section className="rpt-panel rpt-panel--preview">
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">OUTPUT · Scout 推荐</div>
          <h3 className="rpt-panel-title">Top {s.candidates.length} 候选</h3>
        </div>
        <div className="rpt-panel-meta">
          <span className="rpt-pv-pct">{s.candidateCount} 家</span>
        </div>
      </div>

      <div className="rpt-pv-toolbar" role="toolbar" aria-label="导出 / CRM / 分配 / 重扫">
        {OUTPUT_ACTIONS.map((a) => (
          <button key={a.key} type="button" className="rpt-pv-btn" title={a.title}>
            <span className="ic" aria-hidden>{a.glyph}</span>
            <span>{a.label}</span>
          </button>
        ))}
      </div>

      <nav className="rpt-pv-toc ch-out-tabs" aria-label="输出视图切换">
        <button
          type="button"
          className={tab === "radar" ? "on" : undefined}
          onClick={() => setTab("radar")}
        >
          <span className="a">§一</span>
          <span className="t">信号雷达</span>
        </button>
        <button
          type="button"
          className={tab === "funnel" ? "on" : undefined}
          onClick={() => setTab("funnel")}
        >
          <span className="a">§二</span>
          <span className="t">扫描 Funnel</span>
        </button>
        <button
          type="button"
          className={tab === "cand" ? "on" : undefined}
          onClick={() => setTab("cand")}
        >
          <span className="a">§三</span>
          <span className="t">Top 推荐</span>
        </button>
      </nav>

      <div className="rpt-pv-paper-wrap">
        <article className="rpt-pv-paper ch-out-paper" aria-label="Scout 推荐输出">
          <div className="rpt-pv-paper-head">
            <div className="doc-title">Scout · look-alike 推荐</div>
            <div className="doc-sub">
              {s.benchmarkName} · 阈值相似度 {(s.match.similarity * 100).toFixed(0)}% · 预览稿 v1
            </div>
          </div>
          {tab === "radar" && <RadarView radar={s.radar} />}
          {tab === "funnel" && <FunnelView funnel={s.funnel} />}
          {tab === "cand" && <CandidatesView candidates={s.candidates} />}
          <div className="rpt-pv-paper-foot">
            — 以上为 AI 初筛推荐稿 · 未经客户经理复核不得作为外呼名单 —
          </div>
        </article>
      </div>

      <footer className="rpt-pv-status">
        <span className="pg">视图 {tab === "radar" ? "1/3" : tab === "funnel" ? "2/3" : "3/3"}</span>
        <span className="sep">·</span>
        <span className="cov">
          候选 <b>{s.candidates.length}/{s.candidateCount}</b>
        </span>
        <span className="sep">·</span>
        <span className="qc" aria-label="QC 徽章">
          QC
          <span className="qc-chip" data-l="block">● {s.qcCounts.block}</span>
          <span className="qc-chip" data-l="warn">● {s.qcCounts.warn}</span>
          <span className="qc-chip" data-l="info">● {s.qcCounts.info}</span>
        </span>
      </footer>
    </section>
  );
}

const QUADRANT_LABEL: Record<RadarDimension["quadrant"], string> = {
  base: "基本盘",
  bonus: "加分项",
  demand: "需求信号",
  health: "合规健康",
  market: "可营销",
};

function RadarView({ radar }: { radar: RadarDimension[] }) {
  const data = radar.map((d) => ({
    axis: d.axis,
    score: d.score,
    benchmark: d.benchmark,
  }));
  const avgScore = Math.round(radar.reduce((a, b) => a + b.score, 0) / radar.length);
  const avgBench = Math.round(radar.reduce((a, b) => a + b.benchmark, 0) / radar.length);
  const lead = avgScore - avgBench;
  return (
    <section className="ch-rad-sec">
      <header className="ch-out-sec-head">
        <h4 className="ch-out-sec-title">
          <span className="rpt-pv-anchor">§一</span>
          <span>营销优先级 · 8 维评分</span>
        </h4>
        <div className="ch-out-legend">
          <span className="lg" data-k="score">● 该企业</span>
          <span className="lg" data-k="benchmark">○ 行业 P50</span>
        </div>
      </header>
      <div className="ch-rad-chart">
        <ResponsiveContainer width="100%" height={320}>
          <RadarChart data={data} outerRadius="72%">
            <PolarGrid stroke="var(--ink-20)" />
            <PolarAngleAxis dataKey="axis" tick={{ fill: "var(--ink-80)", fontSize: 11 }} />
            <PolarRadiusAxis
              domain={[0, 100]}
              tick={{ fill: "var(--ink-40)", fontSize: 9 }}
              axisLine={false}
            />
            <Radar
              name="行业 P50"
              dataKey="benchmark"
              stroke="var(--ink-48)"
              fill="var(--ink-48)"
              fillOpacity={0.08}
              strokeWidth={1.1}
              strokeDasharray="3 3"
            />
            <Radar
              name="该企业"
              dataKey="score"
              stroke="var(--agent)"
              fill="var(--agent)"
              fillOpacity={0.22}
              strokeWidth={1.8}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <div className="ch-rad-summary">
        <div className="ch-rad-summary-row">
          <span className="lbl">综合得分</span>
          <span className="v main">{avgScore}</span>
          <span className="sep">vs</span>
          <span className="v bench">P50 {avgBench}</span>
          <span className={`ch-rad-lead ${lead >= 0 ? "pos" : "neg"}`}>
            {lead >= 0 ? "+" : ""}{lead}
          </span>
        </div>
      </div>
      <ul className="ch-rad-legend">
        {radar.map((r) => {
          const delta = r.score - r.benchmark;
          return (
            <li key={r.axis} className="ch-rad-row" data-q={r.quadrant} title={r.note}>
              <span className="q-chip" data-q={r.quadrant}>{QUADRANT_LABEL[r.quadrant]}</span>
              <span className="axis">{r.axis}</span>
              <span className="pair">
                <span className="v score">{r.score}</span>
                <span className="sep">/</span>
                <span className="v bench">P50 {r.benchmark}</span>
                <span className={`delta ${delta >= 0 ? "pos" : "neg"}`}>
                  {delta >= 0 ? "+" : ""}{delta}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function FunnelView({ funnel }: { funnel: FunnelStage[] }) {
  const max = Math.max(...funnel.map((f) => f.count));
  return (
    <section className="ch-fn-sec">
      <header className="ch-out-sec-head">
        <h4 className="ch-out-sec-title">
          <span className="rpt-pv-anchor">§二</span>
          <span>5 阶段扫描漏斗</span>
        </h4>
        <div className="ch-out-meta">
          {funnel[0]?.count.toLocaleString()} → {funnel[funnel.length - 1]?.count}
        </div>
      </header>
      <ol className="ch-fn-list">
        {funnel.map((f, i) => {
          const pct = Math.round((f.count / max) * 100);
          const prev = i > 0 ? funnel[i - 1].count : f.count;
          const passRate = i > 0 ? Math.round((f.count / prev) * 100) : 100;
          return (
            <li key={f.id} className="ch-fn-row" data-i={i}>
              <div className="ch-fn-head">
                <span className="ch-fn-n">{i + 1}</span>
                <span className="ch-fn-lbl">{f.label}</span>
                <span className="ch-fn-count">{f.count.toLocaleString()}</span>
                {i > 0 && <span className="ch-fn-pass">透过 {passRate}%</span>}
              </div>
              <div className="ch-fn-bar" aria-hidden>
                <div className="ch-fn-bar-fill" style={{ width: `${pct}%` }} />
              </div>
              {f.detail && <div className="ch-fn-detail">{f.detail}</div>}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function CandidatesView({
  candidates,
  onSelectCandidate,
}: {
  candidates: Candidate[];
  onSelectCandidate?: (id: string) => void;
}) {
  /* Sprint 5+ D1-2 · Top10 fixed slice (per PM "未来一定能实现" + xlsx v2 1.3 verbatim "Top10 推荐")
     超过 10 时显示 "Top 10 (X 家命中 · 仅显前 10)" · 不足 10 时显示真实数量 */
  const TOP_N = 10;
  const displayed = candidates.slice(0, TOP_N);
  const total = candidates.length;
  const truncated = total > TOP_N;
  return (
    <section className="ch-cd-sec">
      <header className="ch-out-sec-head">
        <h4 className="ch-out-sec-title">
          <span className="rpt-pv-anchor">§三</span>
          <span>
            Top {displayed.length} 推荐 · 相似度排序
            {truncated ? ` (共 ${total} 家命中 · 仅显前 ${TOP_N})` : ""}
          </span>
        </h4>
      </header>
      <ol className="ch-cd-list" data-testid="channel-cand-list" data-truncated={truncated ? "yes" : "no"}>
        {displayed.map((c, i) => (
          <CandidateCard
            key={c.id}
            rank={i + 1}
            c={c}
            onSelect={onSelectCandidate}
          />
        ))}
      </ol>
    </section>
  );
}

/* ── 右栏 · Signal Timeline (区域 3) ───────────────── */

const SIG_EVENT_LABEL: Record<SignalEvent["kind"], string> = {
  "biz-change": "工商",
  "bid-win":    "招投标",
  "recruit":    "招聘",
  "fund":       "投融资",
  "policy":     "资质",
  "legal":      "司法",
  "tax":        "纳税",
  "news":       "舆情",
};

function SignalTimelinePanel({
  sessionData,
  selectedCandidate,
}: {
  sessionData: ChannelSession;
  /* F-bug · 父级选中企业变 → 信号时间线 sync (保留 dropdown 可独立切) */
  selectedCandidate: string | null;
}) {
  const s = sessionData;
  /* F-041 · 切 session 时 reset activeId 到当前 session 候选第一个 (有 timeline 优先) */
  const initialId =
    s.candidates.find((c) => c.timeline?.length)?.id ?? s.candidates[0]?.id ?? "";
  const [activeId, setActiveId] = useState<string>(initialId);
  /* 当 session 切换 (s.id 变) 时 sync activeId 到当前 session 第一个候选 */
  useEffect(() => {
    setActiveId(initialId);
  }, [s.id, initialId]);
  /* F-bug · 父级 selectedCandidate 变 → sync activeId · dropdown 仍可独立切 */
  useEffect(() => {
    if (selectedCandidate) setActiveId(selectedCandidate);
  }, [selectedCandidate]);
  const active = s.candidates.find((c) => c.id === activeId) ?? s.candidates[0];
  const events = active?.timeline ?? [];

  return (
    <section className="rpt-panel rpt-panel--tl ch-tl-panel" data-testid="channel-pilot-signals">
      <PanelPinHandle
        id={`channel:timeline:${active?.id ?? "none"}`}
        title={`信号时间线 · ${active?.name ?? "—"}`}
        subtitle="获客 · 候选信号流"
        accentVar="--t-channel"
        agentKey="channel"
        href="/archive/channel"
        blurb={
          events.length
            ? `${events.length} 条聚合信号 · 最近 ${events[0]?.at ?? ""}`
            : "该候选暂无信号"
        }
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">TIMELINE · 候选信号流</div>
          <h3 className="rpt-panel-title">{active?.name}</h3>
        </div>
        <select
          className="rpt-tl-switch"
          aria-label="切换候选企业"
          value={activeId}
          onChange={(e) => setActiveId(e.target.value)}
        >
          {s.candidates.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
              {c.timeline?.length ? ` · ${c.timeline.length} 事件` : " · 无信号"}
            </option>
          ))}
        </select>
      </div>
      <div className="rpt-panel-body ch-tl-body">
        {events.length === 0 ? (
          <div className="ch-tl-empty">
            <span className="ic" aria-hidden>◌</span>
            <span>该候选暂无聚合信号流 · 将在下轮扫描后补全</span>
          </div>
        ) : (
          <ol className="ch-tl-list">
            {events.map((ev) => (
              <TimelineEvent key={ev.id} ev={ev} />
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}

function TimelineEvent({ ev }: { ev: SignalEvent }) {
  return (
    <li className="ch-tl-row" data-kind={ev.kind} data-sev={ev.severity}>
      <span className="ch-tl-dot" aria-hidden />
      <div className="ch-tl-card">
        <div className="ch-tl-meta">
          <span className="kind" data-kind={ev.kind}>{SIG_EVENT_LABEL[ev.kind]}</span>
          <span className="at">{ev.at}</span>
          <span className="sev" data-sev={ev.severity} aria-hidden>
            {ev.severity === "pos" ? "↑" : ev.severity === "neg" ? "↓" : "·"}
          </span>
        </div>
        <div className="ch-tl-title">{ev.title}</div>
        <div className="ch-tl-detail">{ev.detail}</div>
        <div className="ch-tl-source">
          <span className="ic" aria-hidden>◊</span>
          {ev.source.url ? (
            <a href={ev.source.url} target="_blank" rel="noreferrer">
              {ev.source.label}
            </a>
          ) : (
            <span>{ev.source.label}</span>
          )}
        </div>
      </div>
    </li>
  );
}

function CandidateCard({
  rank,
  c,
  onSelect,
}: {
  rank: number;
  c: Candidate;
  onSelect?: (id: string) => void;
}) {
  const simPct = Math.round(c.similarity * 100);
  const hasRisk = c.riskTags.length > 0;
  /* F-042 · click → drawer · 仅当 onSelect 传了才作 button (a11y) */
  const clickable = typeof onSelect === "function";
  return (
    <li
      className="ch-cd-card"
      data-risk={hasRisk ? "yes" : "no"}
      data-testid="channel-candidate-card"
      data-cand-id={c.id}
      data-clickable={clickable ? "yes" : "no"}
      onClick={clickable ? () => onSelect!(c.id) : undefined}
      onKeyDown={
        clickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect!(c.id);
              }
            }
          : undefined
      }
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      aria-label={clickable ? `查看 ${c.name} 详情` : undefined}
      style={clickable ? { cursor: "pointer" } : undefined}
    >
      <header className="ch-cd-head">
        <div className="ch-cd-rank">#{rank}</div>
        <div className="ch-cd-title">
          <h5 className="ch-cd-name">{c.name}</h5>
          <div className="ch-cd-meta">
            {c.industry} · {c.geo} · {c.scale}
          </div>
        </div>
        <div className="ch-cd-sim">
          <div className="ch-cd-sim-pct">{simPct}%</div>
          <div className="ch-cd-sim-bar" aria-hidden>
            <div className="ch-cd-sim-fill" style={{ width: `${simPct}%` }} />
          </div>
          <div className="ch-cd-sim-lbl">相似度</div>
        </div>
      </header>
      <div className="ch-cd-body">
        <div className="ch-cd-sigs">
          <span className="lbl">命中信号</span>
          {c.signals.map((s) => (
            <span key={s} className="ch-cd-sig">
              {s}
            </span>
          ))}
        </div>
        {hasRisk && (
          <div className="ch-cd-risk">
            <span className="lbl">风险提示</span>
            {c.riskTags.map((r) => (
              <span key={r} className="ch-cd-risk-tag">
                {r}
              </span>
            ))}
          </div>
        )}
        <div className="ch-cd-prod">
          <span className="lbl">建议产品</span>
          {c.products.map((p) => (
            <span key={p} className="ch-cd-prod-tag">
              {p}
            </span>
          ))}
        </div>
        {c.note && <div className="ch-cd-note">{c.note}</div>}
      </div>
    </li>
  );
}

/* ── F-042 · candidate detail drawer (master plan §B.4 + §B.4b + §B.4c) ─────
   ESC 关 · backdrop click 关
   4 区:
     header  - 候选 name / similarity / industry / geo / scale
     body 1  - radar 8 维 (该候选 vs P50 · 复用 sessionData.radar) + 该候选 signal timeline
     body 2  - B.4b 匹配维度明细 chip 列表 (vs IdealProfile · 含命中证据 signal/KB ref)
     body 3  - B.4c Top3 产品推荐 + 切入话术
   ────────────────────────────────────────────────────────────────────── */

function CandidateDetailDrawer({
  candidate,
  sessionData,
  onClose,
}: {
  candidate: Candidate | null;
  sessionData: ChannelSession;
  onClose: () => void;
}) {
  if (!candidate) return null;
  const simPct = Math.round(candidate.similarity * 100);
  const matchDims: MatchDimension[] = candidate.match_dimensions ?? [];
  const products: ProductRec[] = candidate.product_recommendations ?? [];
  const pitches: PitchScript[] = candidate.pitch_scripts ?? [];
  const events: SignalEvent[] = candidate.timeline ?? [];
  /* PM 2026-05-07 ALL IN step 2.1 · 字段级溯源 (codex R1 第 4 项 + PM 第 3 条硬规)
     候选企业的所有 evidence source · 用户点 hint URL 跳源验证. backend dataSources camelCase 透前端 */
  const evidenceSources: { label: string; hint: string }[] =
    (candidate as { dataSources?: { label: string; hint: string }[] }).dataSources ?? [];
  return (
    <div
      className="ch-drawer-backdrop"
      data-testid="channel-candidate-drawer-backdrop"
      onClick={onClose}
    >
      <aside
        className="ch-drawer"
        data-testid="channel-candidate-drawer"
        data-cand-id={candidate.id}
        role="dialog"
        aria-modal="true"
        aria-label={`${candidate.name} 详情`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <header className="ch-drawer-head">
          <div className="ch-drawer-head-left">
            <div className="ch-drawer-eyebrow">CANDIDATE · 详情</div>
            <h3
              className="ch-drawer-title"
              data-testid="channel-candidate-drawer-name"
            >
              {candidate.name}
            </h3>
            <div className="ch-drawer-sub">
              {candidate.industry} · {candidate.geo} · {candidate.scale}
            </div>
          </div>
          <div className="ch-drawer-head-right">
            <div className="ch-drawer-sim">
              <span className="num">{simPct}%</span>
              <span className="lbl">相似度</span>
            </div>
            <button
              type="button"
              className="ch-drawer-close"
              data-testid="channel-candidate-drawer-close"
              onClick={onClose}
              aria-label="关闭详情"
            >
              <span aria-hidden>×</span>
            </button>
          </div>
        </header>

        <div className="ch-drawer-body">
          {/* Region 1 · radar 8 维 + 候选 signal timeline */}
          <section className="ch-drawer-sec ch-drawer-sec--radar">
            <h4 className="ch-drawer-sec-title">
              <span className="anchor">§一</span>
              <span>评分雷达 + 信号时间线</span>
            </h4>
            <div className="ch-drawer-radar-wrap">
              {/* PM 2026-05-07 ALL IN step 2.4a · 候选自己的 8 维 (sse_extras.build_radar_8axis)
                  · fallback sessionData.radar (旧 mock 路径) · 切候选时雷达数据真变 */}
              <RadarView
                radar={
                  candidateRadarToDimensions(
                    (candidate as { radar_8axis?: Record<string, number> }).radar_8axis,
                  ) ?? sessionData.radar
                }
              />
            </div>
            <div className="ch-drawer-tl">
              <div className="ch-drawer-tl-head">
                信号时间线 · 共 {events.length} 条
              </div>
              {events.length === 0 ? (
                <div className="ch-drawer-tl-empty">
                  <span className="ic" aria-hidden>◌</span>
                  <span>该候选暂无信号 · 将在下轮扫描后补全</span>
                </div>
              ) : (
                <ol className="ch-drawer-tl-list">
                  {events.map((ev) => (
                    <TimelineEvent key={ev.id} ev={ev} />
                  ))}
                </ol>
              )}
            </div>
          </section>

          {/* PM 2026-05-07 ALL IN step 2.1 · 字段级溯源 evidence section
             codex R1 第 4 项 + PM 第 3 条硬规 · 用户点 source URL 跳源验证 · 强制可追溯 */}
          {evidenceSources.length > 0 && (
            <section
              className="ch-drawer-sec ch-drawer-sec--evidence"
              data-testid="channel-candidate-evidence-section"
            >
              <h4 className="ch-drawer-sec-title">
                <span className="anchor">§证</span>
                <span>数据来源 · 字段级溯源 ({evidenceSources.length} 条)</span>
              </h4>
              <ul
                style={{
                  listStyle: "none",
                  padding: 0,
                  margin: 0,
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                }}
              >
                {evidenceSources.map((src, i) => (
                  <li
                    key={`${src.label}-${i}`}
                    data-testid="candidate-evidence-row"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: "8px 12px",
                      borderRadius: 8,
                      background: "color-mix(in srgb, var(--ink-14) 30%, transparent)",
                      border: "1px solid var(--ink-14)",
                    }}
                  >
                    <span
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 11,
                        padding: "2px 8px",
                        borderRadius: 999,
                        background: "var(--accent)",
                        color: "var(--chalk)",
                        fontWeight: 600,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {src.label}
                    </span>
                    {src.hint ? (
                      <a
                        href={src.hint}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          fontFamily: "var(--mono)",
                          fontSize: 12,
                          color: "var(--accent)",
                          textDecoration: "underline",
                          wordBreak: "break-all",
                          flex: 1,
                        }}
                      >
                        {src.hint}
                      </a>
                    ) : (
                      <span
                        style={{
                          fontFamily: "var(--cjk)",
                          fontSize: 12,
                          color: "var(--ink-48)",
                          fontStyle: "italic",
                        }}
                      >
                        无可点 URL · 内部数据源
                      </span>
                    )}
                  </li>
                ))}
              </ul>
              <div
                style={{
                  marginTop: 10,
                  padding: "6px 10px",
                  fontSize: 11,
                  color: "var(--ink-48)",
                  fontFamily: "var(--cjk)",
                  background: "color-mix(in srgb, var(--accent) 8%, transparent)",
                  borderLeft: "2px solid var(--accent)",
                  borderRadius: 4,
                }}
              >
                所有 evidence 可追溯 · 客户经理点 URL 验证 · 后续 step 加 4 Tier 权重 + 时效衰减 + 单源准确率反馈
              </div>
            </section>
          )}

          {/* Region 2 · B.4b 匹配维度明细 (chip 列表 vs IdealProfile) */}
          <section className="ch-drawer-sec ch-drawer-sec--match">
            <h4 className="ch-drawer-sec-title">
              <span className="anchor">§二</span>
              <span>匹配维度明细 · 为什么像</span>
            </h4>
            {matchDims.length === 0 ? (
              <div className="ch-drawer-empty">
                <span>暂无匹配维度数据</span>
              </div>
            ) : (
              <ul className="ch-drawer-md-list">
                {matchDims.map((m) => (
                  <li
                    key={m.id}
                    className="ch-drawer-md-chip"
                    data-testid="candidate-match-dim-chip"
                    data-md-id={m.id}
                    data-score={m.score}
                  >
                    <div className="ch-drawer-md-row">
                      <span className="dim">{m.dim_name}</span>
                      <span className="score">{m.score}</span>
                    </div>
                    <div className="ch-drawer-md-display">{m.display}</div>
                    <div className="ch-drawer-md-evi">
                      <span className="ic" aria-hidden>◊</span>
                      证据 · {m.hit_evidence}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Region 3 · B.4c Top3 产品推荐 + 切入话术 */}
          <section className="ch-drawer-sec ch-drawer-sec--product">
            <h4 className="ch-drawer-sec-title">
              <span className="anchor">§三</span>
              <span>Top3 产品推荐</span>
            </h4>
            {products.length === 0 ? (
              <div className="ch-drawer-empty">
                <span>暂无产品推荐数据</span>
              </div>
            ) : (
              <div className="ch-drawer-prod-grid">
                {products.slice(0, 3).map((p) => (
                  <article
                    key={p.id}
                    className="ch-drawer-prod-card"
                    data-testid="candidate-product-card"
                    data-product-id={p.id}
                    data-fit-score={p.fit_score}
                  >
                    <header className="ch-drawer-prod-head">
                      <div className="ch-drawer-prod-name">
                        {p.product_name}
                      </div>
                      <div className="ch-drawer-prod-fit">
                        <span className="num">{p.fit_score}</span>
                        <span className="lbl">适配</span>
                      </div>
                    </header>
                    <div className="ch-drawer-prod-intro">{p.intro}</div>
                    <dl className="ch-drawer-prod-meta">
                      {p.amount_range && (
                        <div>
                          <dt>额度</dt>
                          <dd>{p.amount_range}</dd>
                        </div>
                      )}
                      {p.rate_band && (
                        <div>
                          <dt>利率</dt>
                          <dd>{p.rate_band}</dd>
                        </div>
                      )}
                    </dl>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="ch-drawer-sec ch-drawer-sec--pitch">
            <h4 className="ch-drawer-sec-title">
              <span className="anchor">§四</span>
              <span>切入话术 · 打开电话即用</span>
            </h4>
            {pitches.length === 0 ? (
              <div className="ch-drawer-empty">
                <span>暂无话术数据</span>
              </div>
            ) : (
              <ol className="ch-drawer-pitch-list">
                {pitches.map((p) => (
                  <li
                    key={p.id}
                    className="ch-drawer-pitch-item"
                    data-testid="candidate-pitch-script"
                    data-pitch-id={p.id}
                  >
                    <div className="ch-drawer-pitch-head">
                      <span className="who">致 {p.customer_name_placeholder}</span>
                      {p.product_ref && (
                        <span className="ref">关联 · {p.product_ref}</span>
                      )}
                    </div>
                    <div className="ch-drawer-pitch-text">{p.script_text}</div>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      </aside>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────
   F-044 · master plan §B.6 · 3 类 KB upload UI (单文件 multipart upload)
   3 dropzone: 客户名录 / 政策 / 行业指引
   POST /api/channel/upload_kb · 返 kb_id + summary_text
   customer_list 上传完成 → 父级 useEffect 触发 IdealProfile 自动抽取 (B.6b)
   ────────────────────────────────────────────────────────────────────── */

const KB_TYPE_META: Record<
  KbType,
  { label: string; desc: string; accept: string; testid: string; ic: string }
> = {
  customer_list: {
    label: "客户名录",
    desc: "xlsx / csv · 银行已成交客户基础特征",
    accept: ".xlsx,.xls,.csv",
    testid: "kb-dropzone-customer-list",
    ic: "👥",
  },
  policy: {
    label: "政策文件",
    desc: "docx / pdf · 银保监 / 央行新政",
    accept: ".docx,.pdf",
    testid: "kb-dropzone-policy",
    ic: "📋",
  },
  industry_guide: {
    label: "行业指引",
    desc: "docx / pdf · 行业研究报告 / 准入标准",
    accept: ".docx,.pdf",
    testid: "kb-dropzone-industry-guide",
    ic: "📚",
  },
};

const KB_TYPE_ORDER: KbType[] = ["customer_list", "policy", "industry_guide"];

function KbUploadStrip({
  kbIds,
  kbStatus,
  kbSummaries,
  kbErrors,
  onUpload,
}: {
  kbIds: Record<KbType, string | null>;
  kbStatus: Record<KbType, KbUploadStatus>;
  kbSummaries: Record<KbType, KbUploadResult | null>;
  kbErrors: Record<KbType, string>;
  onUpload: (type: KbType, file: File) => void;
}) {
  return (
    <section
      className="ch-kb-strip"
      data-testid="kb-upload-strip"
      aria-label="知识库上传区"
    >
      <header className="ch-kb-strip-head">
        <div>
          <div className="rpt-panel-eyebrow">KB · 知识库上传</div>
          <h3 className="rpt-panel-title">
            上传 3 类 KB · 抽 12 维理想客户画像 · 再扫
          </h3>
        </div>
        <span className="rpt-panel-meta">客户名录必传 · 政策 / 行业可选</span>
      </header>
      <div className="ch-kb-strip-grid">
        {KB_TYPE_ORDER.map((t) => (
          <KbDropzone
            key={t}
            type={t}
            kbId={kbIds[t]}
            status={kbStatus[t]}
            summary={kbSummaries[t]}
            error={kbErrors[t]}
            onUpload={onUpload}
          />
        ))}
      </div>
    </section>
  );
}

function KbDropzone({
  type,
  kbId,
  status,
  summary,
  error,
  onUpload,
}: {
  type: KbType;
  kbId: string | null;
  status: KbUploadStatus;
  summary: KbUploadResult | null;
  error: string;
  onUpload: (type: KbType, file: File) => void;
}) {
  const meta = KB_TYPE_META[type];
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  function pick(file: File | null | undefined) {
    if (!file) return;
    onUpload(type, file);
  }

  function handlePick(e: ChangeEvent<HTMLInputElement>) {
    pick(e.target.files?.[0]);
    /* reset input · 让用户能上传同一 file 重复 */
    if (e.target) e.target.value = "";
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    pick(e.dataTransfer.files?.[0]);
  }

  function handleDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    if (!dragOver) setDragOver(true);
  }

  function handleDragLeave(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
  }

  const hasUpload = kbId !== null && status === "success";
  const isUploading = status === "uploading";
  const isError = status === "error";

  return (
    <article
      className="ch-kb-zone"
      data-testid={meta.testid}
      data-status={status}
      data-has-upload={hasUpload ? "yes" : "no"}
      data-drag-over={dragOver ? "yes" : "no"}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="ch-kb-zone-head">
        <span className="ic" aria-hidden>
          {meta.ic}
        </span>
        <div className="ch-kb-zone-title-wrap">
          <h4 className="ch-kb-zone-title">{meta.label}</h4>
          <div className="ch-kb-zone-desc">{meta.desc}</div>
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={meta.accept}
        className="ch-kb-zone-input"
        data-testid={`${meta.testid}-input`}
        onChange={handlePick}
        disabled={isUploading}
      />
      <div className="ch-kb-zone-action">
        <button
          type="button"
          className="ch-kb-zone-btn"
          data-testid={`${meta.testid}-btn`}
          onClick={() => inputRef.current?.click()}
          disabled={isUploading}
        >
          {isUploading
            ? `上传中…`
            : hasUpload
            ? `重新上传`
            : `选择文件`}
        </button>
        <span className="ch-kb-zone-hint">或拖拽文件到此区</span>
      </div>
      {hasUpload && summary && (
        <div className="ch-kb-zone-summary" data-testid={`${meta.testid}-summary`}>
          <div className="row">
            <span className="lbl">已上传 · ID</span>
            <span className="kb-id">{summary.kb_id.slice(0, 8)}…</span>
          </div>
          <div className="filename">{summary.source_filename}</div>
          <div className="summary-text">{summary.summary_text}</div>
        </div>
      )}
      {/* B-banner · KB 上传错误统一上抛到 workspace 顶部 banner · 此 zone 内 inline error 已移除 */}
    </article>
  );
}

/* ──────────────────────────────────────────────────────────────────────
   F-045 · master plan §B.6b · IdealProfile 12 维画像卡 + "开始扫描" CTA
   消费 /api/channel/profile 返回的 IdealProfile12 + reasoning_text + confidence
   12 chip 展示 + 用户 confirm "开始扫描" 才走 /api/channel/run
   ────────────────────────────────────────────────────────────────────── */

const PROFILE_FIELDS_LIST: Array<{ key: keyof IdealProfile12; label: string }> = [
  { key: "industry_focus", label: "行业聚焦" },
  { key: "scale_preference", label: "规模偏好" },
  { key: "geo_coverage", label: "地域覆盖" },
  { key: "customer_type", label: "客户类型" },
  { key: "product_keywords", label: "产品关键词" },
  { key: "growth_signals", label: "增长信号" },
  { key: "risk_signals", label: "风险信号" },
];

const PROFILE_FIELDS_STR: Array<{ key: keyof IdealProfile12; label: string }> = [
  { key: "stage", label: "发展阶段" },
  { key: "capital_relation", label: "资本关系" },
  { key: "business_size", label: "业务规模" },
  { key: "employee_size", label: "员工规模" },
  { key: "value_chain_position", label: "价值链位置" },
];

function idealProfileToQuery(profile: IdealProfileResponse | null): string {
  if (!profile) return "";
  const p = profile.ideal_profile;
  const parts: string[] = [];
  if (p.industry_focus.length) parts.push(`行业 ${p.industry_focus.slice(0, 3).join(" / ")}`);
  if (p.geo_coverage.length) parts.push(`地域 ${p.geo_coverage.slice(0, 3).join(" / ")}`);
  if (p.scale_preference.length)
    parts.push(`规模 ${p.scale_preference.slice(0, 2).join(" / ")}`);
  if (p.stage) parts.push(`阶段 ${p.stage}`);
  if (p.product_keywords.length)
    parts.push(`产品 ${p.product_keywords.slice(0, 3).join(" / ")}`);
  if (p.growth_signals.length)
    parts.push(`增长信号 ${p.growth_signals.slice(0, 2).join(" / ")}`);
  return parts.length
    ? `按理想画像 look-alike 找企业 · ${parts.join(" · ")}`
    : "按理想客户画像 look-alike 找企业";
}

function IdealProfileCard({
  profile,
  loading,
  error,
  onStartScan,
}: {
  profile: IdealProfileResponse | null;
  loading: boolean;
  error: string;
  onStartScan: () => void;
}) {
  return (
    <section
      className="ch-profile-card"
      data-testid="ideal-profile-card"
      data-loading={loading ? "yes" : "no"}
      aria-label="理想客户画像 12 维"
    >
      <header className="ch-profile-head">
        <div>
          <div className="rpt-panel-eyebrow">PROFILE · 理想客户画像</div>
          <h3 className="rpt-panel-title">
            12 维 IdealProfile · LLM 抽取
            {profile && (
              <span className="ch-profile-conf">
                置信 {Math.round(profile.confidence_score * 100)}%
              </span>
            )}
          </h3>
        </div>
        {profile && !loading && !error && (
          <button
            type="button"
            className="ch-profile-cta"
            data-testid="start-scan-cta"
            onClick={onStartScan}
          >
            <span>开始扫描</span>
            <span className="kbd" aria-hidden>
              ↩
            </span>
          </button>
        )}
      </header>

      {loading && (
        <div
          className="ch-profile-loading"
          data-testid="ideal-profile-loading"
          role="status"
        >
          <span className="ic" aria-hidden>
            ◌
          </span>
          <span>LLM 解析中… 12 维画像抽取约 8-15s</span>
        </div>
      )}

      {error && !loading && (
        <div className="ch-profile-error" role="alert" data-testid="ideal-profile-error">
          <span className="ic" aria-hidden>
            ⚠
          </span>
          <span>画像抽取失败 · {error}</span>
        </div>
      )}

      {profile && !loading && (
        <>
          <div className="ch-profile-grid">
            {PROFILE_FIELDS_LIST.map((f) => {
              const val = profile.ideal_profile[f.key] as string[];
              return (
                <div
                  key={f.key}
                  className="ch-profile-row ch-profile-row--list"
                  data-field={f.key}
                >
                  <div className="ch-profile-row-lbl">{f.label}</div>
                  <div className="ch-profile-row-chips">
                    {val.length === 0 ? (
                      <span className="ch-profile-empty-chip">未识别</span>
                    ) : (
                      val.map((v, i) => (
                        <span
                          key={`${f.key}-${i}`}
                          className="ch-profile-chip"
                          data-testid="ideal-profile-chip"
                          data-field={f.key}
                        >
                          {v}
                        </span>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
            {PROFILE_FIELDS_STR.map((f) => {
              const val = profile.ideal_profile[f.key] as string;
              return (
                <div
                  key={f.key}
                  className="ch-profile-row ch-profile-row--str"
                  data-field={f.key}
                >
                  <div className="ch-profile-row-lbl">{f.label}</div>
                  <div className="ch-profile-row-chips">
                    {val ? (
                      <span
                        className="ch-profile-chip ch-profile-chip--str"
                        data-testid="ideal-profile-chip"
                        data-field={f.key}
                      >
                        {val}
                      </span>
                    ) : (
                      <span className="ch-profile-empty-chip">未识别</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          {profile.reasoning_text && (
            <div
              className="ch-profile-reasoning"
              data-testid="ideal-profile-reasoning"
            >
              <div className="ch-profile-reasoning-lbl">解析说明</div>
              <p className="ch-profile-reasoning-text">{profile.reasoning_text}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
