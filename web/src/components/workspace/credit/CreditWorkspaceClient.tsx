"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Play, AlertTriangle, FileText, RotateCcw } from "lucide-react";

import { Button, SegmentedControl } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { Card, Stat } from "@/components/viz/Card";
import { PipelineRail } from "@/components/viz/PipelineRail";
import { ScoreBar } from "@/components/viz/ScoreBar";
import { ScoreRadar } from "@/components/viz/ScoreRadar";
import { VerdictBadge, VerdictRibbon } from "@/components/viz/VerdictBadge";
import { ChatTagInput, type Tag } from "@/components/ui/ChatTagInput";
import { FileDrop } from "@/components/ui/FileDrop";

import { fetchPresets, streamDecision } from "@/lib/api";
import { fetchMockJson } from "@/lib/fallback";
import { useHeaderSlot } from "@/lib/header-slot";
import {
  CORP_STAGES,
  SME_STAGES,
  RETAIL_STAGES,
  INITIAL_STATE,
  stageOf,
  toBackendSegment,
  type DecisionState,
  type Segment,
  type ScoringPayload,
  type DecisionAdvice,
  type CaseMatch,
  type Profile,
} from "@/lib/credit-types";
import { formatWan } from "@/lib/utils";

// 候选客户下拉标签 —— 来自 Agent6 的企业画像产出
const PRESET_NAMES: Record<string, string> = {
  // 对公
  dingsheng_trade: "鼎盛商贸有限公司 · 建材批发 · 流贷 500 万",
  ruiheng_precision: "瑞恒精密制造 · 装备制造 · 购建生产线 800 万",
  zhongrui_network: "福建中锐网络科技 · 互联网科创 · 流贷 300 万",
  // 普惠（小微 / 个体工商户 / 自雇经营）
  zhangsan_restaurant: "张某 · 个体餐饮业主 · 经营贷 50 万（自雇 3 年）",
  // 对私（纯个人消费贷 / 工薪）
  lisi_education: "李某 · 教培行业工薪 · 装修消费贷 20 万",
  wangwu_decoration: "王某 · 个体装修 · 材料周转 15 万（收入波动）",
};

// 前端 segment → 允许的 preset 白名单
const PRESET_BUCKETS: Record<Segment, string[]> = {
  corporate: ["dingsheng_trade", "ruiheng_precision", "zhongrui_network"],
  sme: ["zhangsan_restaurant"],
  retail: ["lisi_education", "wangwu_decoration"],
};

// 单户授信口径（万元）—— 超出时截断并标注
const AMOUNT_CAP_WAN: Partial<Record<Segment, number>> = {
  sme: 1000,
  retail: 100,
};

const CAP_NOTE: Partial<Record<Segment, string>> = {
  sme: "小微普惠口径：单户 ≤ 1000 万",
  retail: "个人消费贷口径：单户 ≤ 100 万",
};

const SEGMENT_META: Record<
  Segment,
  { title: string; label: string; scoringTitle: string; description: string }
> = {
  corporate: {
    title: "对公",
    label: "对公授信",
    scoringTitle: "四维风险画像",
    description: "面向中大型企业：财务 / 行业 / 经营 / 担保四维评分 + 红线 + 同业案例。",
  },
  sme: {
    title: "普惠",
    label: "普惠小微",
    scoringTitle: "小微画像（含 FICO）",
    description: "面向小微企业、个体工商户、自雇经营：经营流水 + 征信 + 稳定性；单户授信 ≤ 1000 万。",
  },
  retail: {
    title: "对私",
    label: "个人消费贷",
    scoringTitle: "零售评分卡（FICO）",
    description: "面向个人工薪 / 消费客户：还款能力 / 意愿 / 稳定性 / 担保；单户 ≤ 100 万。",
  },
};

type InputMode = "report" | "upload" | "chat";

const QUICK_EVAL_PROMPTS: Record<Segment, string[]> = {
  corporate: [
    "某建材批发企业，年营收 8000 万，负债率 72%，主要客户集中度高，申请流贷 500 万",
    "装备制造，年营收 2.4 亿，经营稳健，专精特新小巨人，申请 1000 万并购贷",
    "互联网 SaaS 企业，B 轮后，年营收 8000 万，尚未盈利，申请 800 万过桥",
  ],
  sme: [
    "个体餐饮店 3 年，月流水 18 万，老板夫妻经营，申请经营贷 50 万",
    "社区便利店，店主自雇 6 年，月流水 12 万，申请普惠小微 30 万",
    "小微服装加工厂，5 个工人，年营收 400 万，申请流贷 80 万",
  ],
  retail: [
    "35 岁公司职员，月收入 1.8 万，信用卡 4 张无逾期，申请消费贷 30 万",
    "28 岁公务员，月收入 1.2 万，首次申贷，申请装修贷 15 万",
    "52 岁事业单位退休，月退休金 6500，申请消费贷 10 万",
  ],
};

async function mockParseProfile(text: string): Promise<Tag[]> {
  await new Promise((r) => setTimeout(r, 500));
  const tags: Tag[] = [];
  const push = (c: string, v: string) => tags.push({ category: c, value: v });
  const rev = text.match(/年营收\s*([\d\.]+\s*[亿万])/);
  if (rev) push("营收", rev[1]);
  const debt = text.match(/负债率\s*([\d\.]+)\s*%/);
  if (debt) push("负债率", debt[1] + "%");
  const amt = text.match(/申请[\u4e00-\u9fa5a-zA-Z]*\s*([\d\.]+\s*万)/);
  if (amt) push("申请额度", amt[1]);
  if (/专精特新/.test(text)) push("资质", "专精特新");
  if (/小巨人/.test(text)) push("资质", "小巨人");
  const age = text.match(/(\d+)\s*岁/);
  if (age) push("年龄", age[1]);
  const income = text.match(/月(收入|流水|退休金)\s*([\d\.]+\s*[万千])/);
  if (income) push("月" + income[1], income[2]);
  if (/无逾期/.test(text)) push("征信", "无逾期");
  if (/未盈利/.test(text)) push("盈利", "未盈利");
  if (/过桥/.test(text)) push("用途", "过桥");
  if (/消费贷/.test(text)) push("产品", "消费贷");
  if (/经营贷/.test(text)) push("产品", "经营贷");
  if (/流贷/.test(text)) push("产品", "流动资金贷款");
  if (/并购贷/.test(text)) push("产品", "并购贷");
  if (tags.length === 0) push("描述", text.slice(0, 20));
  return tags;
}

export function CreditWorkspaceClient() {
  const [segment, setSegment] = useState<Segment>("corporate");
  const [presets, setPresets] = useState<string[]>([]);
  const [preset, setPreset] = useState<string>("");
  const [mode, setMode] = useState<InputMode>("report");
  const [, setQuickTags] = useState<Tag[]>([]);
  const [state, setState] = useState<DecisionState>(INITIAL_STATE);
  const headerSlot = useHeaderSlot();

  // A-015: push SEGMENT_META description into /archive/credit lede on segment switch
  useEffect(() => {
    headerSlot?.setDescription(SEGMENT_META[segment].description);
    return () => headerSlot?.setDescription(null);
  }, [segment, headerSlot]);
  // 跨 Agent 预填来源标记(用于顶部「数据来自报告助手」小标签)
  const [handoffSource, setHandoffSource] = useState<null | {
    company: string;
    source: "session" | "preset";
  }>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [fellBack, setFellBack] = useState<boolean>(false);

  // 跨 Agent 预填 — 挂载时消费 sessionStorage.enterprise_profile + URL ?preset=
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const rawPreset = params.get("preset") || "";

    // W1 扩展:?preset=corporate|retail 仅作 segment 切换, 不作 preset_name
    if (rawPreset === "corporate" || rawPreset === "retail") {
      setSegment(rawPreset);
      return; // 由 segment useEffect 自动选第一个 preset
    }
    if (rawPreset === "sme" || rawPreset === "inclusive") {
      setSegment("sme");
      return;
    }
    const presetParam = rawPreset;

    const applyProfile = (prof: Record<string, unknown>, source: "session" | "preset") => {
      const name = (prof.company_name as string) || (prof.subject_name as string) || "";
      if (!name) return;
      // 按 business_line / industry 推断 segment
      const bizLine = prof.business_line as string | undefined;
      let seg: Segment = "corporate";
      if (bizLine === "inclusive") seg = "sme";
      else if (bizLine === "corporate") seg = "corporate";
      // 预置:industry 含"零售/消费/个人"→retail(演示当前 profile 没这么细,保守不改)
      setSegment(seg);

      // presetParam 优先,否则用 profile_id
      const pid = (prof.profile_id as string) || presetParam || "";
      if (pid) setPreset(pid);

      // 把画像直接塞进 state.profile,ProfileSummary 立即渲染
      setState((s) => ({
        ...s,
        profile: prof as unknown as Profile,
      }));
      setHandoffSource({ company: name, source });
    };

    // 1. 先读 sessionStorage
    try {
      const raw = sessionStorage.getItem("enterprise_profile");
      if (raw) {
        const prof = JSON.parse(raw);
        if (prof && typeof prof === "object") {
          applyProfile(prof, "session");
          return;
        }
      }
    } catch {
      /* sessionStorage 不可用或 JSON 坏了,忽略 */
    }

    // 2. 如 sessionStorage 无,但 URL 带 preset → 回退 fetch 后端 preset
    if (presetParam) {
      fetch(`/api/report/preset/${encodeURIComponent(presetParam)}`, {
        cache: "no-store",
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((j) => {
          const prof = j?.enterprise_profile;
          if (prof) applyProfile(prof, "preset");
        })
        .catch(() => {
          /* 后端不可用就算了,用户还能自己选 */
        });
    }
  }, []);

  // Load presets when segment changes — fetch from backend then filter to bucket
  useEffect(() => {
    fetchPresets(toBackendSegment(segment))
      .then((ps) => {
        const bucket = new Set(PRESET_BUCKETS[segment]);
        const filtered = ps.filter((p) => bucket.has(p));
        setPresets(filtered);
        setPreset(filtered[0] ?? "");
      })
      .catch((err) => {
        console.error(err);
        setPresets([]);
        setPreset("");
      });
  }, [segment]);

  const stages =
    segment === "corporate"
      ? CORP_STAGES
      : segment === "sme"
      ? SME_STAGES
      : RETAIL_STAGES;

  // 降级:把 mock fixture 的 run_mock_events 按 streamDecision 回调形式回放
  const replayMockDecision = async () => {
    const path =
      segment === "corporate"
        ? "/mock/credit_decision_corporate.json"
        : "/mock/credit_decision_retail.json";
    // sme 没有单独 fixture — 先复用 retail(都是小额/零售口径) 保演示不炸
    const realPath =
      segment === "sme" ? "/mock/credit_decision_retail.json" : path;
    const j = await fetchMockJson<{
      run_mock_events: Array<Record<string, unknown>>;
    }>(realPath);
    setFellBack(true);
    for (const ev of j.run_mock_events) {
      await new Promise((r) => setTimeout(r, 280));
      const evt = ev as {
        event: string;
        stage?: string;
        status?: string;
        payload?: unknown;
        profile?: unknown;
      };
      setState((prev) => {
        const next = { ...prev, doneStages: new Set(prev.doneStages) };
        if (evt.event === "profile_loaded") {
          next.profile = evt.profile as Profile;
        } else if (evt.event === "stage" && evt.stage) {
          // fixture stage 使用 {status: running|done} pattern
          const stageKey = evt.stage;
          const payload = evt.payload as { status?: string } | undefined;
          if (payload?.status === "running") {
            next.activeStage = stageKey;
            next.stageHistory = [...prev.stageHistory, stageKey];
          } else if (payload?.status === "done") {
            const base = stageOf(stageKey);
            if (base) next.doneStages.add(base);
            if (base === "scoring")
              next.scoring = evt.payload as ScoringPayload;
            if (base === "case")
              next.cases = (evt.payload as { cases?: CaseMatch[] })?.cases ?? (evt.payload as CaseMatch[]);
            if (base === "advising")
              next.advice = evt.payload as DecisionAdvice;
            next.activeStage = undefined;
          }
        } else if (evt.event === "done") {
          next.phase = "done";
          next.activeStage = undefined;
        }
        return next;
      });
    }
    setState((s) => ({ ...s, phase: "done" }));
  };

  const runDecision = async () => {
    if (!preset) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setFellBack(false);

    setState({
      ...INITIAL_STATE,
      doneStages: new Set(),
      phase: "running",
    });

    let primed = false;
    const timeoutId = setTimeout(() => {
      if (!primed) ctrl.abort();
    }, 2000);

    try {
      await streamDecision(
        { segment: toBackendSegment(segment), preset_name: preset },
        (evt) => {
          primed = true;
          clearTimeout(timeoutId);
          setState((prev) => {
            const next = { ...prev };
            next.doneStages = new Set(prev.doneStages);

            if (evt.event === "profile_loaded") {
              next.profile = evt.profile as Profile;
              return next;
            }
            if (evt.event === "stage" && evt.stage) {
              const base = stageOf(evt.stage);
              if (evt.stage.endsWith("_done")) {
                if (base) next.doneStages.add(base);
                if (base === "scoring")
                  next.scoring = evt.payload as ScoringPayload;
                if (base === "case")
                  next.cases = evt.payload as CaseMatch[];
                if (base === "advising")
                  next.advice = evt.payload as DecisionAdvice;
                next.activeStage = undefined;
              } else if (evt.stage === "all_done") {
                // finalize
              } else {
                next.activeStage = evt.stage;
                next.stageHistory = [...prev.stageHistory, evt.stage];
              }
              return next;
            }
            if (evt.event === "done") {
              next.phase = "done";
              next.activeStage = undefined;
              return next;
            }
            if (evt.event === "error") {
              next.phase = "error";
              next.error = evt.message ?? "未知错误";
              return next;
            }
            return next;
          });
        },
        ctrl.signal
      );
      clearTimeout(timeoutId);
      setState((s) => ({ ...s, phase: s.phase === "error" ? "error" : "done" }));
    } catch (e) {
      clearTimeout(timeoutId);
      if ((e as Error).name === "AbortError") {
        // 只有在从未收到 event 时才视为后端不可达
        if (!primed) {
          try {
            await replayMockDecision();
            return;
          } catch (mockErr) {
            console.error("mock fallback failed", mockErr);
          }
        }
        return;
      }
      if (!primed) {
        try {
          await replayMockDecision();
          return;
        } catch {
          /* fall through to error */
        }
      }
      setState((s) => ({ ...s, phase: "error", error: String(e) }));
    }
  };

  const reset = () => {
    abortRef.current?.abort();
    setState(INITIAL_STATE);
  };

  const presetOptions = presets.map((p) => ({
    value: p,
    label: PRESET_NAMES[p] ?? p,
  }));

  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Left panel */}
      <aside className="col-span-4 space-y-5">
        <Card
          eyebrow="INPUT"
          title="输入来源"
          action={
            <SegmentedControl
              options={[
                { value: "report", label: "已生成" },
                { value: "upload", label: "上传" },
                { value: "chat", label: "快速" },
              ]}
              value={mode}
              onChange={(v) => setMode(v as InputMode)}
            />
          }
        >
          {mode === "report" && (
            <>
              <div className="text-[11px] text-[var(--ink-48)] mb-2 leading-relaxed">
                消费 Agent6（信贷报告助手）已产出的企业画像 / 客户画像。
              </div>
              <Select
                value={preset}
                onChange={setPreset}
                options={presetOptions}
              />
              <div className="mt-4 flex gap-2">
                <Button
                  onClick={runDecision}
                  disabled={!preset || state.phase === "running"}
                  className="flex-1"
                >
                  <Play size={14} />
                  {state.phase === "running" ? "运行中…" : "运行决策"}
                </Button>
                {state.phase !== "idle" && (
                  <Button variant="secondary" onClick={reset}>
                    <RotateCcw size={14} />
                  </Button>
                )}
              </div>
            </>
          )}

          {mode === "upload" && (
            <>
              <FileDrop
                label="上传信贷报告 / 客户材料包"
                hint="支持 PDF · Word · 财报 · 征信"
                accept=".pdf,.doc,.docx,.xlsx"
              />
              <Button
                disabled={state.phase === "running"}
                className="w-full mt-5"
                onClick={() => {
                  if (presets[0]) {
                    setPreset(presets[0]);
                    setTimeout(runDecision, 100);
                  }
                }}
              >
                <Play size={14} /> 解析并运行
              </Button>
              <div className="mt-2 text-[10px] text-[var(--ink-48)] font-tabular">
                DEMO 模式：上传后复用已解析样本走通决策流水线。
              </div>
            </>
          )}

          {mode === "chat" && (
            <>
              <ChatTagInput
                placeholder="一句话描述客户基本情况与授信诉求…"
                presetPrompts={QUICK_EVAL_PROMPTS[segment]}
                parseFn={mockParseProfile}
                onTagsChange={setQuickTags}
                busy={state.phase === "running"}
              />
              <Button
                disabled={state.phase === "running"}
                className="w-full mt-5"
                onClick={() => {
                  if (presets[0]) {
                    setPreset(presets[0]);
                    setTimeout(runDecision, 100);
                  }
                }}
              >
                <Play size={14} /> 运行快速评估
              </Button>
              <div className="mt-2 text-[10px] text-[var(--ink-48)] font-tabular">
                DEMO 模式：以对话画像模拟快速初筛，后端复用默认样本。
              </div>
            </>
          )}

          {state.profile && mode === "report" && (
            <ProfileSummary profile={state.profile} segment={segment} />
          )}
        </Card>

        <Card eyebrow="PIPELINE" title="流水线">
          <PipelineRail
            stages={stages}
            active={state.activeStage}
            done={state.doneStages}
            error={state.phase === "error"}
          />
          {state.phase === "error" && (
            // --color-ember → #c8463a (semantic danger; kept literal across themes)
            <div className="mt-4 text-[12px] text-[#c8463a] font-tabular border-l-2 border-[#c8463a] pl-3">
              {state.error}
            </div>
          )}
        </Card>
      </aside>

      {/* Main panel */}
      <section className="col-span-8 space-y-5">
        {/* Segment switcher + handoff banner (moved from page header) */}
        <div className="flex items-center justify-end gap-3 flex-wrap">
          {fellBack && (
            <span
              className="inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-tabular tracking-wider uppercase border border-[#c8463a] text-[#c8463a]"
              title="后端 2s 未响应，已切换到本地 mock fixture"
            >
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#c8463a]" />
              降级模式 · MOCK
            </span>
          )}
          {handoffSource && (
            <button
              onClick={() => setHandoffSource(null)}
              title="点击关闭此提示"
              className="inline-flex items-center gap-2 px-3 py-1.5 border border-[var(--accent)] bg-[rgba(167,120,47,0.06)] text-[11px] font-tabular tracking-wider text-[var(--ink-80)] hover:bg-[rgba(167,120,47,0.12)] transition-colors"
            >
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
              <span>
                数据来自
                {handoffSource.source === "session" ? "报告助手" : "预置画像"} · {handoffSource.company}
              </span>
              <span className="ml-1 opacity-60">✕</span>
            </button>
          )}
          <SegmentedControl
            options={[
              { value: "corporate", label: "对公" },
              { value: "sme", label: "普惠" },
              { value: "retail", label: "对私" },
            ]}
            value={segment}
            onChange={(v) => {
              setSegment(v as Segment);
              setState(INITIAL_STATE);
            }}
          />
        </div>

        <AnimatePresence mode="wait">
          {state.advice ? (
            <motion.div
              key="verdict"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
            >
              <VerdictHero advice={state.advice} segment={segment} />
            </motion.div>
          ) : (
            <motion.div
              key="placeholder"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <PlaceholderHero phase={state.phase} />
            </motion.div>
          )}
        </AnimatePresence>

        {state.scoring && segment === "corporate" && (
          <CorpScoringPanel scoring={state.scoring} />
        )}
        {state.scoring && segment !== "corporate" && (
          <RetailScoringPanel
            scoring={state.scoring}
            title={SEGMENT_META[segment].scoringTitle}
          />
        )}

        {state.advice && state.advice.red_line_hits?.length > 0 && (
          <RedLinePanel advice={state.advice} />
        )}

        {state.cases && state.cases.length > 0 && (
          <CasesPanel cases={state.cases} />
        )}
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ProfileSummary({
  profile,
  segment,
}: {
  profile: Profile;
  segment: Segment;
}) {
  const name = profile.company_name ?? profile.subject_name ?? "—";
  const req = profile.request ?? {};
  // 对公画像金额单位为「万」；对私/普惠单位为「元」
  const amountWan =
    typeof req.amount === "number"
      ? segment === "corporate"
        ? req.amount
        : req.amount / 10000
      : undefined;
  return (
    <div className="mt-5 pt-4 border-t border-[var(--ink-14)]">
      <div className="font-display text-[15px] text-[var(--ink)]">{name}</div>
      {profile.industry && (
        <div className="mt-0.5 text-[11px] text-[var(--ink-48)]">
          {profile.industry}
          {profile.region && <span className="mx-1.5 opacity-50">·</span>}
          {profile.region}
        </div>
      )}
      <div className="mt-3 grid grid-cols-3 gap-2 font-tabular text-[11px]">
        <div>
          <div className="text-[var(--ink-48)] mb-0.5">申请额度</div>
          <div className="text-[var(--ink)] text-[13px]">
            {amountWan !== undefined
              ? `${amountWan.toLocaleString("zh-CN", { maximumFractionDigits: 1 })} 万`
              : "—"}
          </div>
        </div>
        <div>
          <div className="text-[var(--ink-48)] mb-0.5">期限</div>
          <div className="text-[var(--ink)] text-[13px]">
            {req.term_months ? `${req.term_months} 月` : "—"}
          </div>
        </div>
        <div>
          <div className="text-[var(--ink-48)] mb-0.5">用途</div>
          <div className="text-[var(--ink)] text-[13px] truncate">
            {req.purpose ?? "—"}
          </div>
        </div>
      </div>
    </div>
  );
}

function PlaceholderHero({ phase }: { phase: DecisionState["phase"] }) {
  return (
    <Card className="min-h-[260px] flex items-center justify-center">
      <div className="text-center py-16">
        <VerdictRibbon label={phase === "running" ? "WORKING" : "AWAITING"} />
        <p className="mt-4 font-display text-[22px] text-[var(--ink)]">
          {phase === "running" ? "流水线运行中" : "待运行决策"}
        </p>
        <p className="mt-2 text-[13px] text-[var(--ink-48)]">
          {phase === "running"
            ? "特征抽取 → 评分 → 红线 → 案例 → 决策整合"
            : "选择场景后点击「运行决策」"}
        </p>
      </div>
    </Card>
  );
}

function VerdictHero({
  advice,
  segment,
}: {
  advice: DecisionAdvice;
  segment: Segment;
}) {
  const amountMethods = advice.amount_methods ?? {};
  // --color-ember → #c8463a (semantic danger; kept literal across themes)
  const decisionTone =
    advice.decision === "批准"
      ? "text-[var(--safe)]"
      : advice.decision === "有条件批准"
      ? "text-[var(--accent)]"
      : "text-[#c8463a]";

  // 按业务口径截断额度（万元）
  const rawAmount = advice.approved_amount;
  const cap = AMOUNT_CAP_WAN[segment];
  const capped = cap !== undefined && rawAmount > cap ? cap : rawAmount;
  const wasCapped = cap !== undefined && rawAmount > cap;
  const amountHint = wasCapped
    ? `模型建议 ${rawAmount.toLocaleString()} 万，已按${CAP_NOTE[segment]}截断`
    : CAP_NOTE[segment];

  return (
    <section className="bg-[var(--g1)] border border-[var(--ink-14)] overflow-hidden">
      {/* Top ribbon */}
      <div className="flex items-center justify-between px-6 pt-5 pb-3 border-b border-[var(--ink-14)]">
        <div>
          <div className="text-[10px] font-tabular tracking-[0.25em] text-[var(--accent)] uppercase">
            DECISION
          </div>
          <div className="mt-1 font-display text-[18px] text-[var(--ink)]">
            {advice.subject_name}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--ink-48)] uppercase">
            decision id
          </div>
          <div className="mt-0.5 font-tabular text-[12px] text-[var(--ink-80)]">
            {advice.advice_id}
          </div>
        </div>
      </div>

      <div className="p-6 grid grid-cols-12 gap-6">
        <div className="col-span-5">
          <VerdictBadge decision={advice.decision} grade={advice.risk_grade} />
          <div className="mt-5 text-[13px] leading-relaxed text-[var(--ink-80)] max-w-[360px]">
            {advice.decision_reason || "—"}
          </div>
          <div className="mt-5 grid grid-cols-2 gap-4">
            <div>
              <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--ink-48)] uppercase">
                综合评分
              </div>
              <div className={`mt-1 font-display text-[38px] leading-none ${decisionTone}`}>
                {advice.composite_score}
              </div>
              <div className="mt-0.5 text-[11px] text-[var(--ink-48)] font-tabular">
                / 100
              </div>
            </div>
            <div>
              <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--ink-48)] uppercase">
                红线命中
              </div>
              <div className="mt-1 font-display text-[38px] leading-none text-[var(--ink)]">
                {advice.red_line_hits?.length ?? 0}
              </div>
              <div className="mt-0.5 text-[11px] text-[var(--ink-48)] font-tabular">
                条
              </div>
            </div>
          </div>
        </div>

        <div className="col-span-7 border-l border-[var(--ink-14)] pl-6">
          <div className="grid grid-cols-3 gap-5">
            <Stat
              label="建议额度"
              value={capped > 0 ? formatWan(capped * 1e4) : "0"}
              unit={capped > 0 ? "" : "万元"}
              hint={amountHint}
            />
            <Stat
              label="期限"
              value={advice.approved_term_months || "—"}
              unit={advice.approved_term_months ? "个月" : ""}
            />
            <Stat
              label="利率"
              value={
                advice.interest_rate > 0
                  ? (advice.interest_rate * 100).toFixed(2)
                  : "—"
              }
              unit={advice.interest_rate > 0 ? "%" : ""}
              hint={advice.rate_benchmark || undefined}
            />
          </div>

          {Object.keys(amountMethods).length > 0 && (
            <div className="mt-5 pt-4 border-t border-[var(--ink-14)]">
              <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--ink-48)] uppercase mb-2">
                额度三估算
              </div>
              <div className="space-y-2">
                {Object.entries(amountMethods).map(([k, v]) => (
                  <AmountMethodRow key={k} method={k} value={v} />
                ))}
              </div>
            </div>
          )}

          {advice.conditions?.length > 0 && (
            <div className="mt-5 pt-4 border-t border-[var(--ink-14)]">
              <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--accent)] uppercase mb-2">
                批准条件
              </div>
              <ul className="space-y-1.5">
                {advice.conditions.map((c, i) => (
                  <li
                    key={i}
                    className="text-[12px] text-[var(--ink-80)] leading-relaxed flex gap-2"
                  >
                    <ArrowRight
                      size={12}
                      className="mt-1 shrink-0 text-[var(--accent)]"
                    />
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function AmountMethodRow({ method, value }: { method: string; value: number }) {
  const label: Record<string, string> = {
    revenue_method: "营收法",
    netasset_method: "净资产法",
    cashflow_method: "现金流法",
    collateral_method: "抵押法",
    income_method: "收入法",
    dscr_method: "DSCR 法",
  };
  return (
    <div className="flex items-center justify-between text-[12px]">
      <span className="text-[var(--ink-48)]">{label[method] ?? method}</span>
      <span className="font-tabular text-[var(--ink)]">
        {value > 0 ? `${value.toFixed(0)} 万` : "—"}
      </span>
    </div>
  );
}

function CorpScoringPanel({ scoring }: { scoring: ScoringPayload }) {
  const radar = [
    { label: "财务", score: scoring.financial_score ?? 0 },
    { label: "行业", score: scoring.industry_score ?? 0 },
    { label: "经营", score: scoring.operational_score ?? 0 },
    { label: "担保", score: scoring.guarantee_score ?? 0 },
  ];
  const subs = scoring.sub_scores ?? {};

  return (
    <Card eyebrow="SCORING" title="四维风险画像">
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-6">
          <ScoreRadar data={radar} />
        </div>
        <div className="col-span-6 space-y-4">
          <div className="grid grid-cols-2 gap-x-6 gap-y-3">
            {radar.map((d) => (
              <ScoreBar key={d.label} label={d.label + "维"} value={d.score} />
            ))}
          </div>
          <div className="hr-fine" />
          <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--ink-48)] uppercase">
            细分指标
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 max-h-[200px] overflow-y-auto pr-2">
            {Object.entries(subs).flatMap(([dim, items]) =>
              Object.entries((items ?? {}) as Record<string, number>).map(([name, v]) => (
                <ScoreBar
                  key={`${dim}-${name}`}
                  label={name}
                  value={v as number}
                  size="sm"
                />
              ))
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

const RETAIL_SUB_LABELS: Record<string, string> = {
  // repayment_capacity
  monthly_income_stability: "月收入稳定性",
  dti_ratio: "负债收入比 (DTI)",
  avg_balance_6m: "近 6 月日均余额",
  monthly_income_level: "月收入水平",
  monthly_repay_capacity: "月还款能力",
  cash_surplus: "月现金结余",
  // repayment_willingness
  query_count_24m: "近 24 月查询次数",
  overdue_history: "历史逾期记录",
  cc_utilization: "信用卡使用率",
  credit_history_length: "征信历史长度",
  social_security_months: "社保连续月数",
  // stability
  years_in_job: "在职年限",
  years_at_address: "居住年限",
  marital_status: "婚姻状况",
  education: "学历",
  housing_type: "居住类型",
  age: "年龄",
  // collateral
  collateral_type: "担保物类型",
  ltv: "抵押率 (LTV)",
  title_verified: "权属核验",
  mortgage_count: "在押次数",
  valuation_source: "估值来源",
};

const RETAIL_CATEGORY_LABELS: Record<string, string> = {
  repayment_capacity: "还款能力",
  repayment_willingness: "还款意愿",
  stability: "稳定性",
  collateral: "担保",
};

function RetailScoringPanel({
  scoring,
  title = "零售评分卡（FICO）",
}: {
  scoring: ScoringPayload;
  title?: string;
}) {
  const cs = scoring.category_scores ?? {};
  const radar = [
    { label: "还款能力", score: cs.repayment_capacity ?? 0 },
    { label: "还款意愿", score: cs.repayment_willingness ?? 0 },
    { label: "稳定性", score: cs.stability ?? 0 },
    { label: "担保", score: cs.collateral ?? 0 },
  ];
  const fico = scoring.fico_score;
  const subs = (scoring.sub_scores ?? {}) as Record<string, Record<string, number>>;

  return (
    <Card
      eyebrow="SCORING"
      title={title}
      action={
        fico ? (
          <div className="text-right">
            <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--ink-48)] uppercase">
              FICO
            </div>
            <div className="font-display font-tabular text-[22px] text-[var(--accent)] leading-none">
              {fico}
            </div>
          </div>
        ) : undefined
      }
    >
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-6">
          <ScoreRadar data={radar} />
        </div>
        <div className="col-span-6 space-y-3">
          {radar.map((d) => (
            <ScoreBar key={d.label} label={d.label} value={d.score} />
          ))}
          {Object.keys(subs).length > 0 && (
            <>
              <div className="hr-fine mt-3" />
              <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--ink-48)] uppercase">
                细分指标 · FICO 300-850
              </div>
              <div className="space-y-3 max-h-[220px] overflow-y-auto pr-2">
                {Object.entries(subs).map(([dim, items]) => {
                  if (typeof items !== "object" || items === null) return null;
                  return (
                    <div key={dim}>
                      <div className="text-[10px] font-tabular text-[var(--accent)] tracking-[0.18em] uppercase mb-1.5">
                        {RETAIL_CATEGORY_LABELS[dim] ?? dim}
                      </div>
                      <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                        {Object.entries(items as Record<string, number>).map(
                          ([name, v]) => (
                            <ScoreBar
                              key={`${dim}-${name}`}
                              label={RETAIL_SUB_LABELS[name] ?? name}
                              value={typeof v === "number" ? v : 0}
                              max={850}
                              size="sm"
                            />
                          )
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </Card>
  );
}

function RedLinePanel({ advice }: { advice: DecisionAdvice }) {
  return (
    <Card
      eyebrow="RED LINES"
      title={`命中 ${advice.red_line_hits.length} 条风险线`}
    >
      <ul className="space-y-3">
        {advice.red_line_hits.map((hit, i) => (
          <li
            key={i}
            className="flex gap-3 pb-3 border-b border-[var(--ink-14)] last:border-0 last:pb-0"
          >
            {/* --color-ember → #c8463a (semantic danger; kept literal across themes) */}
            <AlertTriangle
              size={16}
              className={
                hit.is_hard
                  ? "text-[#c8463a] mt-0.5 shrink-0"
                  : "text-[var(--accent)] mt-0.5 shrink-0"
              }
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-3">
                <span className="font-display text-[14px] text-[var(--ink)]">
                  {hit.rule_name}
                </span>
                <span className="font-tabular text-[10px] tracking-wider text-[var(--ink-48)]">
                  {hit.rule_id}
                </span>
                {/* --color-ember → #c8463a (semantic danger; kept literal across themes) */}
                <span
                  className={`ml-auto text-[10px] font-tabular uppercase tracking-[0.2em] ${
                    hit.is_hard ? "text-[#c8463a]" : "text-[var(--accent)]"
                  }`}
                >
                  {hit.is_hard ? "HARD" : "SOFT"} · {hit.severity}
                </span>
              </div>
              <div className="mt-1 text-[12px] text-[var(--ink-80)] leading-relaxed">
                {hit.description}
              </div>
              {hit.threshold !== undefined && hit.actual_value !== undefined && (
                <div className="mt-1.5 flex items-center gap-4 text-[11px] font-tabular text-[var(--ink-48)]">
                  <span>阈值 {String(hit.threshold)}</span>
                  <span>·</span>
                  <span>实际 {String(hit.actual_value)}</span>
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function CasesPanel({ cases }: { cases: CaseMatch[] }) {
  return (
    <Card
      eyebrow="SIMILAR CASES"
      title="历史相似案例"
      action={
        <span className="text-[10px] font-tabular tracking-wider text-[var(--ink-48)]">
          {cases.length} 条
        </span>
      }
    >
      <div className="space-y-3">
        {cases.slice(0, 5).map((c, i) => (
          <div
            key={i}
            className="flex items-center gap-4 pb-3 border-b border-[var(--ink-14)] last:border-0 last:pb-0"
          >
            <FileText size={14} className="text-[var(--ink-48)] shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-[13px] text-[var(--ink)] truncate">
                {c.subject_name ?? c.case_id ?? "案例"}
              </div>
              <div className="text-[11px] text-[var(--ink-48)] font-tabular">
                {c.year && <span>{c.year} · </span>}
                {c.decision && <span>{c.decision}</span>}
                {c.outcome && <span> · {c.outcome}</span>}
              </div>
            </div>
            {typeof c.similarity === "number" && (
              <div className="text-right">
                <div className="text-[10px] font-tabular tracking-wider text-[var(--ink-48)]">
                  SIM
                </div>
                <div className="font-tabular text-[14px] text-[var(--accent)]">
                  {(c.similarity * 100).toFixed(0)}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
