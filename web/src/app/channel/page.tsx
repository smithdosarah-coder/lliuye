"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Play,
  MapPin,
  Factory,
  RotateCcw,
  Download,
  ArrowUpRight,
  ChevronDown,
  Calendar,
  Link2,
  AlertTriangle,
  CheckCircle2,
  Briefcase,
  TrendingUp,
  Users,
  Building2,
  FileSearch,
} from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card, Stat } from "@/components/viz/Card";
import { PipelineRail } from "@/components/viz/PipelineRail";
import { ChatTagInput, type Tag } from "@/components/ui/ChatTagInput";
import { KBBadge } from "@/components/ui/FileDrop";
import dynamic from "next/dynamic";
import { streamChannelSearch } from "@/lib/api";

// 3D hero — 仅在客户端渲染（WebGL 不在 SSR 跑）
const Hero3D = dynamic(() => import("@/components/brand/Hero3D"), {
  ssr: false,
  loading: () => <div className="absolute inset-0 bg-[#0c141d]" />,
});

// 大气 shader 背景 —— 全页 fixed，无色带，有水纹
const AtmosphericBg = dynamic(() => import("@/components/brand/AtmosphericBg"), {
  ssr: false,
  loading: () => <div className="fixed inset-0 bg-[#0a1220] pointer-events-none z-0" />,
});
import type {
  ChannelCandidate,
  ChannelMetrics,
  ChannelReasonDim,
} from "@/lib/channel-types";

const STAGES = [
  { key: "parse", label: "需求解析" },
  { key: "external", label: "外网相似企业搜索" },
  { key: "internal", label: "知识库候选召回" },
  { key: "cross", label: "双路交叉打分" },
  { key: "rank", label: "推荐排序与洞察" },
];

const PRESET_PROMPTS = [
  "想找浙江的新能源汽车精密零部件企业，年营收 1-3 亿，最好有专精特新资质",
  "SaaS 赛道 B 轮左右的工业软件企业，团队来自大厂，有融资事件",
  "长三角建材批发年营收 5000 万到 1 亿，近两年回款稳定",
];

/** 演示用：把自由文本拆成结构化标签。生产环境接 LLM，这里用正则粗粒度识别。 */
async function mockParse(text: string): Promise<Tag[]> {
  await new Promise((r) => setTimeout(r, 600));
  const tags: Tag[] = [];
  const push = (c: string, v: string) => tags.push({ category: c, value: v });

  // 区域
  const region = text.match(/(浙江|江苏|广东|上海|北京|深圳|杭州|苏州|宁波|长三角|珠三角)/);
  if (region) push("区域", region[1]);

  // 行业
  const ind = text.match(/(新能源汽车|精密零部件|零部件|SaaS|工业软件|建材批发|批发|互联网|科技|AI|装备制造|机械)/);
  if (ind) push("行业", ind[1]);

  // 规模
  const scale = text.match(/年营收\s*([\d\.]+\s*[-到至–]\s*[\d\.]+\s*[亿万]|[\d\.]+\s*[亿万])/);
  if (scale) push("规模", "营收 " + scale[1]);

  // 资质
  if (/专精特新/.test(text)) push("资质", "专精特新");
  if (/小巨人/.test(text)) push("资质", "小巨人");
  if (/高新技术|高企/.test(text)) push("资质", "高新技术");

  // 轮次
  const round = text.match(/([ABCD]\s*轮|Pre-[ABC]|种子轮|天使轮)/i);
  if (round) push("融资阶段", round[1].replace(/\s+/g, "").toUpperCase());

  // 自由关键词兜底
  if (/回款稳定/.test(text)) push("经营特征", "回款稳定");
  if (/扩产|扩张/.test(text)) push("经营特征", "扩产期");
  if (/出口/.test(text)) push("经营特征", "出口导向");
  if (/融资/.test(text)) push("经营特征", "近期融资事件");

  if (tags.length === 0) push("关键词", text.slice(0, 20));
  return tags;
}

// 类型从 @/lib/channel-types 导入，保持前后端契约单一来源。
// 兼容旧 UI 组件的命名别名：
type Candidate = ChannelCandidate;
type ReasonDim = ChannelReasonDim;


type Phase = "idle" | "running" | "done";

export default function ChannelPage() {
  const [text, setText] = useState("");
  const [, setTags] = useState<Tag[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [active, setActive] = useState<string>();
  const [done, setDone] = useState<Set<string>>(new Set());
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [metrics, setMetrics] = useState<ChannelMetrics | null>(null);
  const [dataSource, setDataSource] = useState<string>("");
  const [errMsg, setErrMsg] = useState<string>("");

  const run = async () => {
    setPhase("running");
    setDone(new Set());
    setCandidates([]);
    setMetrics(null);
    setDataSource("");
    setErrMsg("");
    try {
      for await (const evt of streamChannelSearch({ query: text, top_n: 8 })) {
        if (evt.event === "stage") {
          if (evt.status === "running") setActive(evt.stage);
          if (evt.status === "done") {
            setDone((prev) => new Set(prev).add(evt.stage));
          }
        } else if (evt.event === "done") {
          setCandidates(evt.candidates);
          setMetrics(evt.metrics);
          setDataSource(evt.data_source);
        } else if (evt.event === "error") {
          console.error("[channel]", evt.message);
          setErrMsg(evt.message);
        }
      }
    } catch (e) {
      console.error(e);
      setErrMsg((e as Error).message ?? String(e));
    } finally {
      setActive(undefined);
      setPhase("done");
    }
  };
  const reset = () => {
    setPhase("idle");
    setDone(new Set());
    setCandidates([]);
    setMetrics(null);
    setDataSource("");
    setErrMsg("");
  };

  return (
    <div data-theme="ink" className="min-h-screen relative">
      {/* 全页大气 shader 背景 —— 消色带 + 水纹 */}
      <AtmosphericBg />

      {/* CINEMATIC HERO —— 紧凑型 3D 场景，不霸屏 */}
      <section className="relative h-[44vh] min-h-[380px] w-full overflow-hidden z-[1]">
        {/* 3D 太阳系透明 Canvas 浮在 shader 底之上 */}
        <div className="absolute inset-0">
          <Hero3D />
        </div>
        {/* 底部柔光过渡 —— 与 shader 水面衔接，不需要硬色 */}
        <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-[#050a13]/60 to-transparent pointer-events-none" />

        {/* hero 文字 overlay */}
        <div className="relative z-10 h-full max-w-[1280px] mx-auto px-10 flex flex-col justify-center">
          <div className="text-[11px] font-tabular tracking-[0.3em] text-[var(--color-brass)] uppercase">
            A01 · Look-alike Prospecting
          </div>
          <h1 className="mt-3 font-display text-[54px] leading-[1] text-[var(--color-ink)] max-w-[620px]">
            全渠道获客
          </h1>
          <p className="mt-4 text-[14px] text-[var(--color-ink-soft)] max-w-[520px] leading-[1.65]">
            自然语言描述目标客户画像 · 外网真实搜索 × 内部库 look-alike 双路召回 · 全程证据链可追溯
          </p>
        </div>
      </section>

      <div className="relative z-[1] px-10 pt-4 pb-14 max-w-[1280px] mx-auto">
      <header className="flex items-start justify-between mb-10 relative">
        <div className="hidden">{/* hero 已迁到上方 3D 区，保留结构占位 */}</div>
        <div className="flex gap-2">
          {phase !== "idle" && (
            <Button variant="secondary" onClick={reset}>
              <RotateCcw size={14} /> 重置
            </Button>
          )}
          {phase === "done" && (
            <Button>
              <Download size={14} /> 导出候选池
            </Button>
          )}
        </div>
      </header>

      <div className="ink-brush-hr mb-9" aria-hidden />

      <div className="grid grid-cols-12 gap-8">
        <aside className="col-span-4 space-y-6">
          <Card eyebrow="TARGET PROFILE" title="目标客户画像">
            <ChatTagInput
              placeholder="用一两句话描述你想找的客户画像…&#10;（行业、区域、规模、资质、阶段都可以）"
              presetPrompts={PRESET_PROMPTS}
              parseFn={mockParse}
              onTagsChange={setTags}
              onTextChange={setText}
              busy={phase === "running"}
            />
            <Button
              onClick={run}
              disabled={!text.trim() || phase === "running"}
              className="w-full mt-5"
            >
              <Play size={14} />
              {phase === "running" ? "搜索中…" : "启动 Look-alike 搜索"}
            </Button>
          </Card>

          <Card eyebrow="DATA SOURCES" title="数据源">
            <div className="space-y-2.5">
              <KBBadge label="内部存量客户库" count={3218} />
              <KBBadge label="历史营销案例" count={146} />
              <KBBadge label="行业黄页" count={12860} />
            </div>
            <div className="mt-3 text-[11px] text-[var(--color-ink-muted)] leading-relaxed">
              外部数据源：天眼查 · 招投标 · 裁判文书 · 主流财经媒体
            </div>
          </Card>

          <Card eyebrow="PIPELINE" title="搜索流程">
            <PipelineRail stages={STAGES} active={active} done={done} />
          </Card>
        </aside>

        <section className="col-span-8 space-y-6">
          <AnimatePresence mode="wait">
            {phase === "done" ? (
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="space-y-6"
              >
                <MetricsCard metrics={metrics} dataSource={dataSource} />
                {candidates.length > 0 ? (
                  <CandidateList cands={candidates} />
                ) : (
                  <Card className="min-h-[160px] flex items-center justify-center">
                    <div className="text-center py-10">
                      <div className="text-[10px] font-tabular tracking-[0.25em] text-[var(--color-brass)] uppercase">
                        EMPTY
                      </div>
                      <p className="mt-3 font-display text-[18px] text-[var(--color-ink)]">
                        未召回有效候选
                      </p>
                      <p className="mt-2 text-[12px] text-[var(--color-ink-muted)]">
                        {errMsg
                          ? `后端错误：${errMsg}`
                          : "调整一下描述（更具体的行业/规模/区域）再试一次。"}
                      </p>
                    </div>
                  </Card>
                )}
              </motion.div>
            ) : (
              <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <Card className="min-h-[260px] flex items-center justify-center">
                  <div className="text-center py-16">
                    <div className="text-[10px] font-tabular tracking-[0.25em] text-[var(--color-brass)] uppercase">
                      {phase === "running" ? "CRAWLING" : "AWAITING"}
                    </div>
                    <p className="mt-4 font-display text-[22px] text-[var(--color-ink)]">
                      {phase === "running" ? "双路搜索中" : "待描述目标客户画像"}
                    </p>
                    <p className="mt-2 text-[13px] text-[var(--color-ink-muted)]">
                      输入自然语言 → 解析标签 → 外网 × 知识库双路召回
                    </p>
                  </div>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </section>
      </div>

      <footer className="mt-12 pt-6">
        <div className="ink-brush-hr mb-4" aria-hidden />
        <div className="flex items-center justify-between">
          <span className="ink-signature text-[12px]">
            乾策 · 众安信科 · 信贷 AI 智能体矩阵
          </span>
          <span className="text-[10px] font-tabular text-[var(--color-ink-muted)] tracking-[0.2em] uppercase">
            X-Nexus · 2026
          </span>
        </div>
      </footer>
      </div>
    </div>
  );
}

function MetricsCard({
  metrics,
  dataSource,
}: {
  metrics: ChannelMetrics | null;
  dataSource: string;
}) {
  const m = metrics ?? { external: 0, internal: 0, overlap: 0, final: 0 };
  const sourceBadge =
    dataSource === "tavily"
      ? { text: "TAVILY", tone: "text-[var(--color-sage)] border-[var(--color-sage)]" }
      : dataSource === "mock_fallback"
      ? { text: "MOCK FALLBACK", tone: "text-[var(--color-brass)] border-[var(--color-brass)]" }
      : { text: "UNKNOWN", tone: "text-[var(--color-ink-muted)] border-[var(--color-line)]" };
  return (
    <section className="bg-[var(--color-paper-raised)] border border-[var(--color-line)] p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-tabular tracking-[0.25em] text-[var(--color-brass)] uppercase">
            搜索结果 · Search Metrics
          </span>
        </div>
        <span className="ink-source-badge" title="本次搜索的数据源">
          {sourceBadge.text}
        </span>
      </div>
      <div className="grid grid-cols-4 gap-6">
      <Stat label="外网召回" value={m.external} hint="公开搜索" />
      <Stat label="知识库命中" value={m.internal} hint="内部库相似画像" />
      <Stat label="双路重合" value={m.overlap} hint="交叉验证通过" />
      <Stat label="最终推荐" value={m.final} hint="分数≥70" />
      </div>
    </section>
  );
}

function CandidateList({ cands }: { cands: Candidate[] }) {
  const [expanded, setExpanded] = useState<number | null>(0); // 默认展开第一个
  return (
    <Card
      eyebrow="CANDIDATES"
      title={`相似候选 · ${cands.length} 家`}
      action={
        <span className="text-[10px] font-tabular tracking-wider text-[var(--color-ink-muted)]">
          按匹配得分排序 · 点击卡片展开详情
        </span>
      }
    >
      <div className="space-y-4">
        {cands.map((c, i) => (
          <CandidateCard
            key={i}
            c={c}
            rank={i + 1}
            isExpanded={expanded === i}
            onToggle={() => setExpanded(expanded === i ? null : i)}
          />
        ))}
      </div>
    </Card>
  );
}

function CandidateCard({
  c,
  rank,
  isExpanded,
  onToggle,
}: {
  c: Candidate;
  rank: number;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const sourceBadge = {
    both: { label: "双路", cls: "ink-seal-mini ink-seal-vermilion" },
    external: { label: "外网", cls: "ink-seal-mini ink-seal-ink" },
    internal: { label: "内部", cls: "ink-seal-mini ink-seal-sage" },
  }[c.source];

  return (
    <div className="border-b border-[var(--color-line)] last:border-0 pb-4 last:pb-0">
      <button
        type="button"
        onClick={onToggle}
        className="w-full text-left grid grid-cols-12 gap-5 group"
      >
        <div className="col-span-1">
          <div className="font-display text-[26px] leading-none text-[var(--color-brass)] font-tabular">
            {String(rank).padStart(2, "0")}
          </div>
        </div>
        <div className="col-span-8">
          <div className="flex items-baseline gap-3 flex-wrap">
            <h4 className="font-display text-[17px] text-[var(--color-ink)] leading-tight group-hover:text-[var(--color-brass)] transition-colors">
              {c.name}
            </h4>
            <span className={sourceBadge.cls}>
              {sourceBadge.label}
            </span>
            <ChevronDown
              size={14}
              className={`text-[var(--color-ink-muted)] transition-transform ${
                isExpanded ? "rotate-180" : ""
              }`}
            />
          </div>
          <div className="mt-1.5 flex items-center gap-4 text-[11px] font-tabular text-[var(--color-ink-muted)]">
            <span className="inline-flex items-center gap-1">
              <Factory size={11} /> {c.industry}
            </span>
            <span className="inline-flex items-center gap-1">
              <MapPin size={11} /> {c.region}
            </span>
            <span className="inline-flex items-center gap-1">
              <Users size={11} /> {c.employees} 人
            </span>
            <span className="inline-flex items-center gap-1">
              <TrendingUp size={11} /> {c.revenueLatest}
            </span>
          </div>
          <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1">
            {c.reasons.map((r, i) => (
              <li
                key={i}
                className="text-[12px] text-[var(--color-ink-soft)] leading-relaxed flex gap-1.5 before:content-['·'] before:text-[var(--color-brass)]"
              >
                {r}
              </li>
            ))}
          </ul>
          <div className="mt-3 flex items-center gap-2 text-[12px]">
            <ArrowUpRight size={12} className="text-[var(--color-brass)]" />
            <span className="text-[var(--color-ink)]">{c.signal}</span>
          </div>
          {c.contact && (
            <div className="mt-1 text-[11px] text-[var(--color-ink-muted)] font-tabular">
              跟进：{c.contact}
            </div>
          )}
        </div>
        <div className="col-span-3 text-right">
          <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--color-ink-muted)] uppercase">
            match
          </div>
          <div className="mt-1 font-display text-[38px] leading-none text-[var(--color-ink)]">
            {c.score}
          </div>
          <div className="mt-1 text-[10px] text-[var(--color-ink-muted)] font-tabular">
            / 100
          </div>
          <div className="mt-3 w-full h-0.5 bg-[var(--color-line)]">
            <div
              className="h-full bg-[var(--color-brass)]"
              style={{ width: `${c.score}%` }}
            />
          </div>
        </div>
      </button>

      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            key="detail"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <ExpandedDetail c={c} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function ExpandedDetail({ c }: { c: Candidate }) {
  return (
    <div className="mt-5 ml-[calc(8.333%)] pl-5 border-l-2 border-[var(--color-brass)] space-y-6 pb-2">
      {/* 基础信息 */}
      <div>
        <SectionLabel icon={Building2} text="企业基础信息" />
        <div className="mt-2 grid grid-cols-3 gap-x-5 gap-y-2 text-[12px]">
          <Field label="统一社会信用代码" value={c.uscc} mono />
          <Field label="注册资本" value={c.registeredCapital} />
          <Field label="成立时间" value={c.founded} />
          <Field label="法定代表人" value={c.legalRep} />
          <Field label="员工规模" value={`${c.employees} 人`} />
          <Field label="纳税等级" value={c.taxRating ?? "—"} />
        </div>
        <div className="mt-2 text-[12px] text-[var(--color-ink-soft)] leading-relaxed">
          <span className="text-[var(--color-ink-muted)]">主营：</span>
          {c.mainBusiness}
        </div>
      </div>

      {/* 财务与经营 */}
      <div>
        <SectionLabel icon={TrendingUp} text="财务与经营" />
        <div className="mt-2 grid grid-cols-4 gap-x-5 gap-y-2 text-[12px]">
          <Field label="最新营收" value={c.revenueLatest} />
          <Field label="同比增长" value={c.revenueGrowth} />
          <Field label="净利率" value={c.netMargin ?? "—"} />
          <Field
            label="主要客户"
            value={c.mainCustomers.slice(0, 3).join(" / ")}
          />
        </div>
        {c.certifications.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {c.certifications.map((cert) => (
              <span
                key={cert}
                className="inline-flex items-center gap-1 px-1.5 py-[2px] text-[10px] font-tabular border border-[var(--color-sage)] text-[var(--color-sage)]"
              >
                <CheckCircle2 size={10} /> {cert}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 推荐维度详解 */}
      <div>
        <SectionLabel icon={FileSearch} text="推荐维度详解 · 每项均有证据出处" />
        <div className="mt-2 space-y-3">
          {c.reasonDims.map((dim) => (
            <ReasonDimRow key={dim.dim} dim={dim} />
          ))}
        </div>
      </div>

      {/* 近期动态 */}
      <div>
        <SectionLabel icon={Calendar} text="近期动态（时间线）" />
        <div className="mt-2 space-y-2">
          {c.events.map((e, i) => (
            <div key={i} className="grid grid-cols-12 gap-3 text-[12px]">
              <div className="col-span-2 font-tabular text-[var(--color-ink-muted)]">
                {e.date}
              </div>
              <div className="col-span-10">
                <div className="text-[var(--color-ink)]">{e.event}</div>
                <div className="mt-0.5 text-[10px] font-tabular text-[var(--color-ink-muted)] inline-flex items-center gap-1">
                  <Link2 size={9} /> {e.source}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 数据来源清单 */}
      <div>
        <SectionLabel icon={Link2} text="数据来源清单 · 可追溯" />
        <div className="mt-2 grid grid-cols-2 gap-x-5 gap-y-1.5">
          {c.dataSources.map((ds, i) => (
            <div key={i} className="text-[11px] font-tabular">
              <span className="text-[var(--color-brass)]">{ds.label}</span>
              <span className="mx-1.5 text-[var(--color-ink-muted)]">·</span>
              <span className="text-[var(--color-ink-soft)]">{ds.hint}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 风险提示 + 建议动作 */}
      <div className="grid grid-cols-2 gap-6 pt-2 border-t border-[var(--color-line)]">
        <div>
          <SectionLabel icon={AlertTriangle} text="风险提示" tone="ember" />
          <ul className="mt-2 space-y-1">
            {c.risks.map((r, i) => (
              <li
                key={i}
                className="text-[12px] text-[var(--color-ink-soft)] leading-relaxed flex gap-1.5 before:content-['!'] before:text-[var(--color-ember)] before:font-tabular"
              >
                {r}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <SectionLabel icon={Briefcase} text="建议下一步" />
          <p className="mt-2 text-[12px] text-[var(--color-ink)] leading-relaxed">
            {c.nextAction}
          </p>
        </div>
      </div>
    </div>
  );
}

function SectionLabel({
  icon: Icon,
  text,
  tone,
}: {
  icon: typeof Building2;
  text: string;
  tone?: "ember";
}) {
  const color =
    tone === "ember" ? "text-[var(--color-ember)]" : "text-[var(--color-brass)]";
  return (
    <div
      className={`text-[10px] font-tabular tracking-[0.2em] uppercase inline-flex items-center gap-1.5 ${color}`}
    >
      <Icon size={11} /> {text}
    </div>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="text-[10px] font-tabular tracking-wider text-[var(--color-ink-muted)] uppercase mb-0.5">
        {label}
      </div>
      <div
        className={`text-[var(--color-ink)] ${
          mono ? "font-tabular text-[11px]" : "text-[12px]"
        }`}
      >
        {value}
      </div>
    </div>
  );
}

function ReasonDimRow({ dim }: { dim: ReasonDim }) {
  const toneColor =
    dim.score >= 85
      ? "var(--color-sage)"
      : dim.score >= 70
      ? "var(--color-brass)"
      : "var(--color-ember)";
  return (
    <div className="grid grid-cols-12 gap-3">
      <div className="col-span-2">
        <div className="text-[11px] font-tabular text-[var(--color-ink-muted)]">
          {dim.dim}
        </div>
        <div className="mt-0.5 font-display text-[18px] leading-none" style={{ color: toneColor }}>
          {dim.score}
        </div>
        <div className="mt-1 w-full h-0.5 bg-[var(--color-line)]">
          <div className="h-full" style={{ width: `${dim.score}%`, background: toneColor }} />
        </div>
      </div>
      <div className="col-span-10">
        <div className="text-[12px] text-[var(--color-ink)] font-medium leading-snug">
          {dim.verdict}
        </div>
        <div className="mt-1 text-[12px] text-[var(--color-ink-soft)] leading-relaxed">
          {dim.evidence}
        </div>
        <div className="mt-1 text-[10px] font-tabular text-[var(--color-ink-muted)] inline-flex items-center gap-1">
          <Link2 size={9} /> 来源：{dim.source}
        </div>
      </div>
    </div>
  );
}
