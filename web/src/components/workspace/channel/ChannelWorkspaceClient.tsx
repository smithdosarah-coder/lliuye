"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Play,
  MapPin,
  Factory,
  RotateCcw,
  Download,
  ChevronDown,
  Link2,
  CheckCircle2,
  XCircle,
  Briefcase,
  Users,
  Building2,
  Phone,
  ExternalLink,
  Zap,
} from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card, Stat } from "@/components/viz/Card";
import { PipelineRail } from "@/components/viz/PipelineRail";
import { ChatTagInput, type Tag } from "@/components/ui/ChatTagInput";
import { KBBadge } from "@/components/ui/FileDrop";
import { streamChannelSearch } from "@/lib/api";
import type {
  ChannelCandidate,
  ChannelMetrics,
  SignalItem,
  MatchTag,
} from "@/lib/channel-types";

const STAGES = [
  { key: "parse", label: "意图解析" },
  { key: "signal_scan", label: "信号扫描（5路并行）" },
  { key: "aggregate", label: "实体聚合去重" },
  { key: "enrich", label: "工商补全 + 产品匹配" },
  { key: "pitch", label: "切入话术生成" },
  { key: "rank", label: "信号密度排序" },
];

const PRESET_PROMPTS = [
  "想找浙江的新能源汽车精密零部件企业，年营收 1-3 亿，最好有专精特新资质",
  "SaaS 赛道 B 轮左右的工业软件企业，团队来自大厂，有融资事件",
  "长三角建材批发年营收 5000 万到 1 亿，近两年回款稳定",
];

const SIGNAL_EMOJI: Record<string, string> = {
  bidding: "\uD83D\uDD25",   // fire
  recognition: "\uD83C\uDFC6", // trophy
  tech: "\uD83D\uDD27",      // wrench
  growth: "\uD83D\uDCC8",    // chart up
  award: "\u2B50",            // star
};

const SIGNAL_LABEL: Record<string, string> = {
  bidding: "中标",
  recognition: "认可",
  tech: "技术",
  growth: "扩产",
  award: "获奖",
};

/** 演示用：把自由文本拆成结构化标签。 */
async function mockParse(text: string): Promise<Tag[]> {
  await new Promise((r) => setTimeout(r, 600));
  const tags: Tag[] = [];
  const push = (c: string, v: string) => tags.push({ category: c, value: v });

  const region = text.match(/(浙江|江苏|广东|上海|北京|深圳|杭州|苏州|宁波|长三角|珠三角)/);
  if (region) push("区域", region[1]);
  const ind = text.match(/(新能源汽车|精密零部件|零部件|SaaS|工业软件|建材批发|批发|互联网|科技|AI|装备制造|机械)/);
  if (ind) push("行业", ind[1]);
  const scale = text.match(/年营收\s*([\d\.]+\s*[-到至–]\s*[\d\.]+\s*[亿万]|[\d\.]+\s*[亿万])/);
  if (scale) push("规模", "营收 " + scale[1]);
  if (/专精特新/.test(text)) push("资质", "专精特新");
  if (/小巨人/.test(text)) push("资质", "小巨人");
  if (/高新技术|高企/.test(text)) push("资质", "高新技术");
  const round = text.match(/([ABCD]\s*轮|Pre-[ABC]|种子轮|天使轮)/i);
  if (round) push("融资阶段", round[1].replace(/\s+/g, "").toUpperCase());
  if (/回款稳定/.test(text)) push("经营特征", "回款稳定");
  if (/扩产|扩张/.test(text)) push("经营特征", "扩产期");
  if (/出口/.test(text)) push("经营特征", "出口导向");
  if (/融资/.test(text)) push("经营特征", "近期融资事件");
  if (tags.length === 0) push("关键词", text.slice(0, 20));
  return tags;
}

type Phase = "idle" | "running" | "done";

export function ChannelWorkspaceClient() {
  const [text, setText] = useState("");
  const [, setTags] = useState<Tag[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [active, setActive] = useState<string>();
  const [done, setDone] = useState<Set<string>>(new Set());
  const [candidates, setCandidates] = useState<ChannelCandidate[]>([]);
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
    <div data-theme="ink" className="page-photo-bg-css relative">
      <div className="relative z-[1] space-y-6">
        <div className="grid grid-cols-12 gap-6">
          <aside className="col-span-4 space-y-6">
            <Card eyebrow="TARGET PROFILE" title="目标客户画像">
              <ChatTagInput
                placeholder={"用一两句话描述你想找的客户画像...\n（行业、区域、规模、资质、阶段都可以）"}
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
                {phase === "running" ? "信号扫描中..." : "启动信号搜索"}
              </Button>
            </Card>

            <Card eyebrow="SIGNAL SOURCES" title="信号数据源">
              <div className="space-y-2.5">
                <KBBadge label="招投标平台" count={0} />
                <KBBadge label="政府公示（专精特新/高企）" count={0} />
                <KBBadge label="专利数据库" count={0} />
                <KBBadge label="财经媒体（扩产/投资）" count={0} />
                <KBBadge label="评优公示" count={0} />
              </div>
              <div className="mt-3 text-[11px] text-[var(--ink-48)] leading-relaxed">
                5 路并行搜索 · 企查查工商补全 · LLM 信号抽取
              </div>
            </Card>

            <Card eyebrow="PIPELINE" title="搜索流程">
              <PipelineRail stages={STAGES} active={active} done={done} />
            </Card>
          </aside>

          <section className="col-span-8 space-y-6">
            {phase !== "idle" && (
              <div className="flex justify-end gap-2">
                <Button variant="secondary" onClick={reset}>
                  <RotateCcw size={14} /> 重置
                </Button>
                {phase === "done" && (
                  <Button>
                    <Download size={14} /> 导出候选池
                  </Button>
                )}
              </div>
            )}
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
                        <div className="text-[10px] font-tabular tracking-[0.25em] text-[var(--accent)] uppercase">
                          EMPTY
                        </div>
                        <p className="mt-3 font-display text-[18px] text-[var(--ink)]">
                          未捕获有效信号
                        </p>
                        <p className="mt-2 text-[12px] text-[var(--ink-48)]">
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
                      <div className="text-[10px] font-tabular tracking-[0.25em] text-[var(--accent)] uppercase">
                        {phase === "running" ? "SCANNING SIGNALS" : "AWAITING"}
                      </div>
                      <p className="mt-4 font-display text-[22px] text-[var(--ink)]">
                        {phase === "running" ? "5 路信号搜索中" : "待描述目标客户画像"}
                      </p>
                      <p className="mt-2 text-[13px] text-[var(--ink-48)]">
                        描述行业+区域 → 5 路信号搜索 → 公司从信号中浮出
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
            <span className="text-[10px] font-tabular text-[var(--ink-48)] tracking-[0.2em] uppercase">
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
  const m = metrics ?? { signalTotal: 0, companiesFound: 0, final: 0 };
  const sourceBadge =
    dataSource === "tavily"
      ? { text: "TAVILY LIVE", tone: "text-[var(--safe)] border-[var(--safe)]" }
      : dataSource === "mock_fallback"
      ? { text: "MOCK FALLBACK", tone: "text-[var(--accent)] border-[var(--accent)]" }
      : { text: "UNKNOWN", tone: "text-[var(--ink-48)] border-[var(--ink-14)]" };
  return (
    <section className="bg-[var(--g1)] border border-[var(--ink-14)] p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-tabular tracking-[0.25em] text-[var(--accent)] uppercase">
            信号搜索结果 · Signal Metrics
          </span>
        </div>
        <span className="ink-source-badge" title="本次搜索的数据源">
          {sourceBadge.text}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-6">
        <Stat label="信号总数" value={m.signalTotal} hint="5路搜索汇总" />
        <Stat label="发现企业" value={m.companiesFound} hint="信号聚合去重" />
        <Stat label="最终推荐" value={m.final} hint="信号密度排序" />
      </div>
    </section>
  );
}

function CandidateList({ cands }: { cands: ChannelCandidate[] }) {
  const [expanded, setExpanded] = useState<number | null>(0);
  return (
    <Card
      eyebrow="SIGNAL CANDIDATES"
      title={`信号候选 · ${cands.length} 家`}
      action={
        <span className="text-[10px] font-tabular tracking-wider text-[var(--ink-48)]">
          按信号密度排序 · 点击展开详情
        </span>
      }
    >
      <div className="space-y-4">
        {cands.map((c, i) => (
          <SignalCandidateCard
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

function SignalCandidateCard({
  c,
  rank,
  isExpanded,
  onToggle,
}: {
  c: ChannelCandidate;
  rank: number;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="border-b border-[var(--ink-14)] last:border-0 pb-4 last:pb-0">
      <button
        type="button"
        onClick={onToggle}
        className="w-full text-left"
      >
        {/* Row 1: Rank + Name + Signal Count */}
        <div className="flex items-baseline gap-3">
          <span className="font-display text-[26px] leading-none text-[var(--accent)] font-tabular">
            {String(rank).padStart(2, "0")}
          </span>
          <h4 className="font-display text-[17px] text-[var(--ink)] leading-tight hover:text-[var(--accent)] transition-colors">
            {c.name}
          </h4>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-tabular border border-[var(--accent)] text-[var(--accent)]">
            <Zap size={10} /> 信号 {c.signalCount} 条
          </span>
          <ChevronDown
            size={14}
            className={`ml-auto text-[var(--ink-48)] transition-transform ${
              isExpanded ? "rotate-180" : ""
            }`}
          />
        </div>

        {/* Row 2: Basic info line */}
        <div className="mt-1.5 ml-[38px] flex items-center gap-4 text-[11px] font-tabular text-[var(--ink-48)]">
          {c.industry && c.industry !== "未获取" && (
            <span className="inline-flex items-center gap-1"><Factory size={11} /> {c.industry}</span>
          )}
          {c.region && c.region !== "未获取" && (
            <span className="inline-flex items-center gap-1"><MapPin size={11} /> {c.region}</span>
          )}
          {c.founded && c.founded !== "未获取" && (
            <span>{c.founded}年</span>
          )}
          {c.employees > 0 && (
            <span className="inline-flex items-center gap-1"><Users size={11} /> {c.employees}人</span>
          )}
        </div>

        {/* Row 3: Match tags */}
        {c.matchTags && c.matchTags.length > 0 && (
          <div className="mt-2 ml-[38px] flex flex-wrap gap-1.5">
            {c.matchTags.map((tag, i) => (
              <MatchTagBadge key={i} tag={tag} />
            ))}
          </div>
        )}

        {/* Row 4: Signal timeline (compact) */}
        <div className="mt-3 ml-[38px] space-y-1.5">
          {c.signals.slice(0, 4).map((sig, i) => (
            <SignalRow key={i} signal={sig} />
          ))}
          {c.signals.length > 4 && (
            <div className="text-[11px] text-[var(--ink-48)] font-tabular">
              +{c.signals.length - 4} 条更多信号
            </div>
          )}
        </div>

        {/* Row 5: Products + Pitch */}
        {c.recommendedProducts && c.recommendedProducts.length > 0 && (
          <div className="mt-3 ml-[38px] flex items-start gap-2">
            <Briefcase size={12} className="text-[var(--accent)] mt-0.5 shrink-0" />
            <span className="text-[12px] text-[var(--ink)] font-medium">
              {c.recommendedProducts.join(" + ")}
            </span>
          </div>
        )}
        {c.pitch && (
          <div className="mt-1.5 ml-[38px] flex items-start gap-2">
            <Phone size={12} className="text-[var(--safe)] mt-0.5 shrink-0" />
            <span className="text-[12px] text-[var(--ink-80)] italic leading-relaxed">
              &ldquo;{c.pitch}&rdquo;
            </span>
          </div>
        )}

        {/* Row 6: Data sources count */}
        <div className="mt-2 ml-[38px] flex items-center gap-1.5 text-[11px] font-tabular text-[var(--ink-48)]">
          <Link2 size={10} />
          <span>{c.dataSources?.length || 0} 个数据来源</span>
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
            <ExpandedSignalDetail c={c} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function MatchTagBadge({ tag }: { tag: MatchTag }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-[2px] text-[10px] font-tabular border ${
        tag.matched
          ? "border-[var(--safe)] text-[var(--safe)]"
          : "border-[var(--ink-14)] text-[var(--ink-48)]"
      }`}
      title={tag.detail}
    >
      {tag.matched ? <CheckCircle2 size={10} /> : <XCircle size={10} />}
      {tag.label}
    </span>
  );
}

function SignalRow({ signal }: { signal: SignalItem }) {
  const emoji = SIGNAL_EMOJI[signal.type] || "\u26A1";
  const label = SIGNAL_LABEL[signal.type] || signal.type;
  return (
    <div className="flex items-baseline gap-2 text-[12px]">
      <span className="shrink-0 w-[18px] text-center">{emoji}</span>
      <span className="text-[var(--accent)] font-tabular shrink-0 w-[32px]">{label}</span>
      <span className="text-[var(--ink)]">{signal.title}</span>
      {signal.date && (
        <span className="text-[var(--ink-48)] font-tabular text-[10px] shrink-0">
          ({signal.date})
        </span>
      )}
    </div>
  );
}

function ExpandedSignalDetail({ c }: { c: ChannelCandidate }) {
  return (
    <div className="mt-5 ml-[38px] pl-5 border-l-2 border-[var(--accent)] space-y-6 pb-2">
      {/* 基础工商信息 */}
      <div>
        <SectionLabel icon={Building2} text="企业基础信息（企查查补全）" />
        <div className="mt-2 grid grid-cols-3 gap-x-5 gap-y-2 text-[12px]">
          <Field label="统一社会信用代码" value={c.uscc} mono />
          <Field label="注册资本" value={c.registeredCapital} />
          <Field label="成立时间" value={c.founded} />
          <Field label="法定代表人" value={c.legalRep} />
          <Field label="员工规模" value={c.employees > 0 ? `${c.employees} 人` : "未获取"} />
          <Field label="所属行业" value={c.industry} />
        </div>
        {c.mainBusiness && c.mainBusiness !== "未获取" && (
          <div className="mt-2 text-[12px] text-[var(--ink-80)] leading-relaxed">
            <span className="text-[var(--ink-48)]">主营：</span>
            {c.mainBusiness}
          </div>
        )}
      </div>

      {/* 完整信号时间线 */}
      <div>
        <SectionLabel icon={Zap} text={`全部信号 · ${c.signals.length} 条`} />
        <div className="mt-2 space-y-3">
          {c.signals.map((sig, i) => (
            <div key={i} className="grid grid-cols-12 gap-3 text-[12px]">
              <div className="col-span-1 text-center text-[16px]">
                {SIGNAL_EMOJI[sig.type] || "\u26A1"}
              </div>
              <div className="col-span-11">
                <div className="flex items-baseline gap-2">
                  <span className="text-[var(--accent)] font-tabular text-[10px] uppercase">
                    {SIGNAL_LABEL[sig.type] || sig.type}
                  </span>
                  {sig.date && (
                    <span className="text-[var(--ink-48)] font-tabular text-[10px]">
                      {sig.date}
                    </span>
                  )}
                </div>
                <div className="text-[var(--ink)] font-medium leading-snug">{sig.title}</div>
                {sig.detail && (
                  <div className="mt-0.5 text-[var(--ink-80)] leading-relaxed">{sig.detail}</div>
                )}
                <div className="mt-1 flex items-center gap-2 text-[10px] font-tabular text-[var(--ink-48)]">
                  <span>{sig.source}</span>
                  {sig.url && (
                    <a
                      href={sig.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-0.5 hover:text-[var(--accent)] transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <ExternalLink size={9} /> 原文
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 产品推荐 + 话术 */}
      <div>
        <SectionLabel icon={Briefcase} text="营销建议" />
        {c.recommendedProducts && c.recommendedProducts.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {c.recommendedProducts.map((prod, i) => (
              <span
                key={i}
                className="px-2 py-1 text-[11px] font-tabular border border-[var(--accent)] text-[var(--accent)] bg-[var(--accent)]/5"
              >
                {prod}
              </span>
            ))}
          </div>
        )}
        {c.pitch && (
          <div className="mt-3 p-3 bg-[var(--g0)] border border-[var(--ink-14)] text-[12px] text-[var(--ink)] leading-relaxed italic">
            <Phone size={12} className="inline text-[var(--safe)] mr-1.5" />
            {c.pitch}
          </div>
        )}
      </div>

      {/* 数据来源清单 */}
      {c.dataSources && c.dataSources.length > 0 && (
        <div>
          <SectionLabel icon={Link2} text="数据来源清单" />
          <div className="mt-2 grid grid-cols-1 gap-y-1.5">
            {c.dataSources.map((ds, i) => (
              <div key={i} className="text-[11px] font-tabular flex items-center gap-1.5">
                <span className="text-[var(--accent)]">{ds.label}</span>
                {ds.hint && (
                  <>
                    <span className="text-[var(--ink-48)]">·</span>
                    {ds.hint.startsWith("http") ? (
                      <a
                        href={ds.hint}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--ink-80)] hover:text-[var(--accent)] inline-flex items-center gap-0.5"
                      >
                        <ExternalLink size={9} /> 查看
                      </a>
                    ) : (
                      <span className="text-[var(--ink-80)]">{ds.hint}</span>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
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
  // --color-ember → #c8463a (semantic danger; kept literal across themes)
  const color =
    tone === "ember" ? "text-[#c8463a]" : "text-[var(--accent)]";
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
      <div className="text-[10px] font-tabular tracking-wider text-[var(--ink-48)] uppercase mb-0.5">
        {label}
      </div>
      <div
        className={`text-[var(--ink)] ${
          mono ? "font-tabular text-[11px]" : "text-[12px]"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
