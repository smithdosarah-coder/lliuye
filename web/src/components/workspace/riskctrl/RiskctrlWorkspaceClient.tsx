"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Play,
  Code2,
  Download,
  RotateCcw,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  CheckCircle2,
  Target,
  Pencil,
} from "lucide-react";

import { Button, SegmentedControl } from "@/components/ui/Button";
import { Card, Stat } from "@/components/viz/Card";
import { PipelineRail } from "@/components/viz/PipelineRail";
import { FileDrop, KBBadge } from "@/components/ui/FileDrop";

/**
 * Agent2 · 风控策略运营
 *
 * 解决什么问题：
 *   策略运营日常痛点 —— 坏账波动 / 新政策 / 客群漂移 → 需要调整策略 →
 *   但调整后能否上生产，要经过严格回测证明"不会变坏"。
 *   本页解决的就是「回测 + 生产化决策」这一个环节。
 *
 * 输入（左侧两张卡）：
 *   1. 基线策略：生产当前在用的规则集（默认生产活版本，可上传历史版本替换）
 *   2. 候选策略：待验证的新规则集（可上传 DSL、可选已有草稿、可进入内置编辑器）
 *   3. 样本池：用于回测的历史申请样本（默认过去 6 月全量，可上传自定义切片）
 *
 * 产出（主面板）：
 *   1. 业务影响摘要：推荐结论 + 折算业务指标 + 灰度建议
 *   2. 技术指标对比：AUC/KS/PSI、通过率、批准率、坏账率
 *   3. 规则对照：DSL diff / 各规则命中率
 *   4. 混淆矩阵对比
 */

const STAGES = [
  { key: "load", label: "加载策略与样本" },
  { key: "apply", label: "规则执行" },
  { key: "metric", label: "指标计算" },
  { key: "compare", label: "新旧对比" },
  { key: "report", label: "回测报告" },
];

const POLICIES = {
  v2024_q4: {
    version: "V2024.Q4",
    label: "现行策略",
    rules: [
      { id: "R01", text: "申请人年龄 ∈ [23, 60]", hit_rate: 98.7 },
      { id: "R02", text: "征信近 6 个月逾期次数 ≤ 1", hit_rate: 94.2 },
      { id: "R03", text: "月收入 ≥ 6000 且收入证明齐备", hit_rate: 88.6 },
      { id: "R04", text: "负债收入比 DTI < 0.55", hit_rate: 92.1 },
      { id: "R05", text: "当前持有信用卡不超过 8 张", hit_rate: 96.4 },
      { id: "R06", text: "查询次数（近 3 月）≤ 6", hit_rate: 91.3 },
    ],
    metrics: {
      auc: 0.734,
      ks: 0.352,
      psi: 0.042,
      pass_rate: 0.612,
      approval_rate: 0.438,
      bad_rate: 0.031,
    },
  },
  v2025_q1_new: {
    version: "V2025.Q1 (候选)",
    label: "候选策略",
    rules: [
      { id: "R01", text: "申请人年龄 ∈ [22, 62]", hit_rate: 99.1 },
      { id: "R02", text: "征信近 12 个月逾期次数 ≤ 1", hit_rate: 92.8 },
      { id: "R03", text: "月收入 ≥ 5000 且多源验证一致", hit_rate: 89.9 },
      { id: "R04", text: "负债收入比 DTI < 0.60", hit_rate: 94.6 },
      { id: "R05", text: "当前持有信用卡不超过 10 张", hit_rate: 97.8 },
      { id: "R06", text: "查询次数（近 6 月）≤ 10", hit_rate: 93.5 },
      { id: "R07", text: "公积金连续缴纳 ≥ 12 月 OR 社保连续 ≥ 18 月", hit_rate: 76.3 },
    ],
    metrics: {
      auc: 0.762,
      ks: 0.386,
      psi: 0.039,
      pass_rate: 0.653,
      approval_rate: 0.482,
      bad_rate: 0.024,
    },
  },
};

const CONFUSION = {
  current: { tp: 412, fp: 48, tn: 463, fn: 77 },
  candidate: { tp: 447, fp: 38, tn: 473, fn: 42 },
};

type Phase = "idle" | "running" | "done";
type CandSource = "draft" | "upload" | "edit";
type SampleSource = "default" | "upload";

export function RiskctrlWorkspaceClient() {
  const [candSource, setCandSource] = useState<CandSource>("draft");
  const [sampleSource, setSampleSource] = useState<SampleSource>("default");
  const [view, setView] = useState<"dsl" | "chart">("dsl");
  const [phase, setPhase] = useState<Phase>("idle");
  const [active, setActive] = useState<string>();
  const [done, setDone] = useState<Set<string>>(new Set());

  const run = async () => {
    setPhase("running");
    setDone(new Set());
    for (const s of STAGES) {
      setActive(s.key);
      await new Promise((r) => setTimeout(r, 700));
      setDone((prev) => new Set(prev).add(s.key));
    }
    setActive(undefined);
    setPhase("done");
  };
  const reset = () => {
    setPhase("idle");
    setDone(new Set());
  };

  const baseline = POLICIES.v2024_q4;
  const candidate = POLICIES.v2025_q1_new;

  return (
    <div className="grid grid-cols-12 gap-6">
      <aside className="col-span-4 space-y-5">
        <Card eyebrow="BASELINE" title="基线策略">
          <div className="flex items-center gap-3 px-3 py-2.5 border border-[var(--color-line-strong)] bg-[var(--color-paper-sunken)]">
            <span className="text-[10px] font-tabular tracking-wider px-1.5 py-0.5 border border-[var(--color-sage)] text-[var(--color-sage)]">
              LIVE
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-[13px] text-[var(--color-ink)]">
                {baseline.version}
              </div>
              <div className="text-[10px] font-tabular text-[var(--color-ink-muted)]">
                生产环境当前版本 · {baseline.rules.length} 条规则
              </div>
            </div>
          </div>
          <div className="mt-3">
            <FileDrop
              label="替换为历史版本对比"
              hint="可选 · 上传其他 DSL 版本作为基线"
              accept=".json,.yaml,.dsl,.txt"
            />
          </div>
        </Card>

        <Card
          eyebrow="CANDIDATE"
          title="候选策略"
          action={
            <SegmentedControl
              options={[
                { value: "draft", label: "已有" },
                { value: "upload", label: "上传" },
                { value: "edit", label: "编辑" },
              ]}
              value={candSource}
              onChange={(v) => setCandSource(v as CandSource)}
            />
          }
        >
          {candSource === "draft" && (
            <>
              <div className="space-y-2">
                {[
                  { v: "V2025.Q1", tag: "当前", desc: "引入公积金/社保复核" },
                  { v: "V2025.Q1-B", tag: "草稿", desc: "放宽 DTI 阈值" },
                  { v: "V2024.Q3-rollback", tag: "历史", desc: "回滚到去年 Q3" },
                ].map((p, i) => (
                  <button
                    key={p.v}
                    className={`w-full text-left px-3 py-2 border transition-all ${
                      i === 0
                        ? "border-[var(--color-brass)] bg-[var(--color-overlay)]"
                        : "border-[var(--color-line)] hover:border-[var(--color-ink-muted)]"
                    }`}
                  >
                    <div className="flex items-baseline gap-2">
                      <span className="font-tabular text-[12px] text-[var(--color-ink)]">
                        {p.v}
                      </span>
                      <span className="text-[9px] font-tabular tracking-wider text-[var(--color-brass)] uppercase">
                        {p.tag}
                      </span>
                    </div>
                    <div className="text-[11px] text-[var(--color-ink-muted)]">
                      {p.desc}
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}
          {candSource === "upload" && (
            <FileDrop
              label="上传候选策略 DSL"
              hint="JSON / YAML / 自定义 DSL"
              accept=".json,.yaml,.dsl,.txt"
            />
          )}
          {candSource === "edit" && (
            <div>
              <div className="flex items-center gap-2 text-[11px] text-[var(--color-ink-muted)] mb-2">
                <Pencil size={12} className="text-[var(--color-brass)]" /> 内置编辑器
              </div>
              <textarea
                defaultValue={`strategy v2025_q1 {\n  R01: age ∈ [22, 62]\n  R02: overdue_12m ≤ 1\n  R03: income ≥ 5000 and multi_source_ok\n  R04: DTI < 0.60\n  R05: credit_cards ≤ 10\n  R06: inquiry_6m ≤ 10\n  R07: (gjj ≥ 12m) OR (sb ≥ 18m)\n}`}
                rows={9}
                spellCheck={false}
                className="w-full p-3 text-[11px] font-tabular bg-[var(--color-paper-sunken)] border border-[var(--color-line-strong)] focus:outline-none focus:border-[var(--color-ink)] text-[var(--color-ink)] leading-relaxed"
              />
            </div>
          )}
        </Card>

        <Card
          eyebrow="SAMPLE POOL"
          title="回测样本"
          action={
            <SegmentedControl
              options={[
                { value: "default", label: "默认" },
                { value: "upload", label: "上传" },
              ]}
              value={sampleSource}
              onChange={(v) => setSampleSource(v as SampleSource)}
            />
          }
        >
          {sampleSource === "default" ? (
            <KBBadge label="历史申请全量（2024.10 – 2025.03）" count={10000} />
          ) : (
            <FileDrop
              label="上传申请样本"
              hint="CSV / Excel · 含 label 列（0/1）"
              accept=".csv,.xlsx"
            />
          )}
          <div className="mt-3 text-[11px] text-[var(--color-ink-muted)] leading-relaxed">
            样本要求：含标签（已观察到表现窗的 good/bad），建议 ≥ 3000 条。
          </div>
          <Button
            onClick={run}
            disabled={phase === "running"}
            className="w-full mt-4"
          >
            <Play size={14} />
            {phase === "running" ? "回测中…" : "启动回测"}
          </Button>
        </Card>

        <Card eyebrow="PIPELINE" title="回测流程">
          <PipelineRail stages={STAGES} active={active} done={done} />
        </Card>
      </aside>

      <section className="col-span-8 space-y-5">
        {phase !== "idle" && (
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={reset}>
              <RotateCcw size={14} /> 重置
            </Button>
            {phase === "done" && (
              <Button>
                <Download size={14} /> 导出回测报告
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
              className="space-y-5"
            >
              <BusinessImpact
                baseline={baseline.metrics}
                candidate={candidate.metrics}
              />
              <MetricsComparison
                baseline={baseline.metrics}
                candidate={candidate.metrics}
              />
              <Card
                eyebrow="RULES"
                title="规则 DSL 对照"
                action={
                  <SegmentedControl
                    options={[
                      { value: "dsl", label: "DSL" },
                      { value: "chart", label: "命中率" },
                    ]}
                    value={view}
                    onChange={(v) => setView(v as "dsl" | "chart")}
                  />
                }
              >
                {view === "dsl" ? (
                  <DslDiff a={baseline.rules} b={candidate.rules} />
                ) : (
                  <HitRates rules={candidate.rules} />
                )}
              </Card>
              <ConfusionCompare />
            </motion.div>
          ) : (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <Card className="min-h-[320px] flex items-center justify-center">
                <div className="text-center py-10 max-w-[440px]">
                  <div className="text-[10px] font-tabular tracking-[0.25em] text-[var(--color-brass)] uppercase">
                    {phase === "running" ? "BACKTESTING" : "AWAITING"}
                  </div>
                  <p className="mt-4 font-display text-[22px] text-[var(--color-ink)]">
                    {phase === "running" ? "正在回测…" : "待启动回测"}
                  </p>
                  <p className="mt-3 text-[13px] text-[var(--color-ink-muted)] leading-relaxed">
                    策略变更需要「用历史数据证明不会变坏」才能上线。
                    <br />
                    左侧配置 <span className="text-[var(--color-ink)]">基线</span> ·
                    <span className="text-[var(--color-ink)]"> 候选</span> ·
                    <span className="text-[var(--color-ink)]"> 样本</span>
                    ，运行后产出：
                  </p>
                  <ul className="mt-3 space-y-1.5 text-left inline-block">
                    {[
                      "① 上线建议：采纳 / 灰度 / 拒绝",
                      "② 业务影响：月增批准、利息收入、坏账节约",
                      "③ 技术指标：AUC / KS / PSI / 通过率",
                      "④ 规则对照：DSL diff + 各规则命中率",
                    ].map((t) => (
                      <li
                        key={t}
                        className="text-[12px] text-[var(--color-ink-soft)] flex gap-2"
                      >
                        <ArrowRight
                          size={11}
                          className="mt-1 shrink-0 text-[var(--color-brass)]"
                        />
                        {t}
                      </li>
                    ))}
                  </ul>
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </section>
    </div>
  );
}

function BusinessImpact({
  baseline,
  candidate,
}: {
  baseline: typeof POLICIES.v2024_q4.metrics;
  candidate: typeof POLICIES.v2024_q4.metrics;
}) {
  const MONTHLY_APPLY = 10000;
  const AVG_AMOUNT_WAN = 8;
  const AVG_INTEREST_YUAN = 5800;
  const BAD_LOSS_RATE = 0.6;

  const approveDelta = candidate.approval_rate - baseline.approval_rate;
  const badDelta = candidate.bad_rate - baseline.bad_rate;

  const extraApprovalsMonth = Math.round(MONTHLY_APPLY * approveDelta);
  const extraLoanBalanceYi =
    (extraApprovalsMonth * AVG_AMOUNT_WAN * 12) / 10000;
  const extraIncomeMonthWan = Math.round(
    (extraApprovalsMonth * AVG_INTEREST_YUAN) / 10000
  );
  const badSavingMonthWan = Math.round(
    MONTHLY_APPLY *
      candidate.approval_rate *
      AVG_AMOUNT_WAN *
      Math.abs(badDelta) *
      BAD_LOSS_RATE
  );

  const verdict =
    badDelta < 0 && approveDelta > 0
      ? { label: "建议采纳", tone: "sage", reason: "通过率提升同时坏账率下降，风险收益双赢" }
      : badDelta < 0
      ? { label: "建议采纳", tone: "sage", reason: "坏账率显著下降" }
      : approveDelta > 0
      ? { label: "需进一步评估", tone: "brass", reason: "通过率提升但坏账同步上升" }
      : { label: "不建议采纳", tone: "ember", reason: "关键指标未见改善" };

  const toneCls =
    verdict.tone === "sage"
      ? "text-[var(--color-sage)]"
      : verdict.tone === "brass"
      ? "text-[var(--color-brass)]"
      : "text-[var(--color-ember)]";
  const tonerBorder =
    verdict.tone === "sage"
      ? "border-[var(--color-sage)]"
      : verdict.tone === "brass"
      ? "border-[var(--color-brass)]"
      : "border-[var(--color-ember)]";

  return (
    <section className="bg-[var(--color-paper-raised)] border border-[var(--color-line)] overflow-hidden">
      <header className="flex items-center justify-between px-6 pt-5 pb-3 border-b border-[var(--color-line)]">
        <div>
          <div className="text-[10px] font-tabular tracking-[0.25em] text-[var(--color-brass)] uppercase">
            BUSINESS IMPACT
          </div>
          <div className="mt-1 font-display text-[18px] text-[var(--color-ink)]">
            策略切换的业务价值
          </div>
        </div>
        <div
          className={`px-3 py-1 border uppercase tracking-[0.2em] text-[11px] font-tabular ${tonerBorder} ${toneCls}`}
        >
          <CheckCircle2 size={12} className="inline mr-1.5" />
          {verdict.label}
        </div>
      </header>

      <div className="p-6 grid grid-cols-12 gap-6">
        <div className="col-span-5 border-r border-[var(--color-line)] pr-6">
          <div className={`text-[11px] uppercase font-tabular tracking-[0.2em] mb-2 ${toneCls}`}>
            <Target size={11} className="inline mr-1" /> 推荐结论
          </div>
          <p className="font-display text-[18px] text-[var(--color-ink)] leading-snug">
            {verdict.reason}
          </p>
          <ul className="mt-4 space-y-2">
            <li className="flex gap-2 text-[12px] text-[var(--color-ink-soft)]">
              <ArrowRight size={12} className="mt-1 shrink-0 text-[var(--color-brass)]" />
              主要变化：规则集扩展至 7 条（新增 R07 公积金/社保复核）
            </li>
            <li className="flex gap-2 text-[12px] text-[var(--color-ink-soft)]">
              <ArrowRight size={12} className="mt-1 shrink-0 text-[var(--color-brass)]" />
              关键改进：AUC +3.8%、坏账率 −22.6%、通过率 +6.7%
            </li>
            <li className="flex gap-2 text-[12px] text-[var(--color-ink-soft)]">
              <ArrowRight size={12} className="mt-1 shrink-0 text-[var(--color-brass)]" />
              下一步：先 10% 灰度 2 周 → 观察 PSI 稳定性 → 全量上线
            </li>
          </ul>
        </div>

        <div className="col-span-7">
          <div className="text-[10px] uppercase font-tabular tracking-[0.2em] text-[var(--color-ink-muted)] mb-3">
            折算月度业务量（假设：月申请 1 万笔，户均 8 万）
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-5">
            <ImpactRow
              label="月新增批准"
              value={`${extraApprovalsMonth > 0 ? "+" : ""}${extraApprovalsMonth}`}
              unit="笔"
              tone={extraApprovalsMonth >= 0 ? "sage" : "ember"}
            />
            <ImpactRow
              label="年化新增余额"
              value={`${extraLoanBalanceYi > 0 ? "+" : ""}${extraLoanBalanceYi.toFixed(2)}`}
              unit="亿元"
              tone={extraLoanBalanceYi >= 0 ? "sage" : "ember"}
            />
            <ImpactRow
              label="月新增利息收入"
              value={`≈ ${extraIncomeMonthWan > 0 ? "+" : ""}${extraIncomeMonthWan}`}
              unit="万元"
              tone={extraIncomeMonthWan >= 0 ? "sage" : "ember"}
            />
            <ImpactRow
              label="月坏账节约"
              value={`≈ ${badSavingMonthWan}`}
              unit="万元"
              tone="sage"
            />
          </div>
          <div className="mt-5 pt-4 border-t border-[var(--color-line)] grid grid-cols-3 gap-3 text-[11px] font-tabular">
            <DeltaRow label="通过率" a={baseline.pass_rate} b={candidate.pass_rate} fmt={(v: number) => (v * 100).toFixed(1) + "%"} better="up" />
            <DeltaRow label="批准率" a={baseline.approval_rate} b={candidate.approval_rate} fmt={(v: number) => (v * 100).toFixed(1) + "%"} better="up" />
            <DeltaRow label="坏账率" a={baseline.bad_rate} b={candidate.bad_rate} fmt={(v: number) => (v * 100).toFixed(2) + "%"} better="down" />
          </div>
        </div>
      </div>
    </section>
  );
}

function ImpactRow({
  label,
  value,
  unit,
  tone,
}: {
  label: string;
  value: string;
  unit: string;
  tone: "sage" | "ember" | "brass";
}) {
  const toneCls = {
    sage: "text-[var(--color-sage)]",
    brass: "text-[var(--color-brass)]",
    ember: "text-[var(--color-ember)]",
  }[tone];
  return (
    <div>
      <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--color-ink-muted)] uppercase">
        {label}
      </div>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span className={`font-display font-tabular text-[26px] leading-none ${toneCls}`}>
          {value}
        </span>
        <span className="text-[11px] text-[var(--color-ink-muted)] font-tabular">
          {unit}
        </span>
      </div>
    </div>
  );
}

function DeltaRow({
  label,
  a,
  b,
  fmt,
  better,
}: {
  label: string;
  a: number;
  b: number;
  fmt: (v: number) => string;
  better: "up" | "down";
}) {
  const improved = better === "up" ? b > a : b < a;
  const tone = improved ? "text-[var(--color-sage)]" : "text-[var(--color-ember)]";
  const Icon = improved ? TrendingUp : TrendingDown;
  return (
    <div>
      <span className="text-[var(--color-ink-muted)]">{label}</span>
      <span className="ml-2">{fmt(a)}</span>
      <ArrowRight size={9} className="inline mx-1.5 text-[var(--color-ink-muted)]" />
      <span className="text-[var(--color-ink)]">{fmt(b)}</span>
      <Icon size={10} className={`inline ml-1 ${tone}`} />
    </div>
  );
}

function MetricsComparison({
  baseline,
  candidate,
}: {
  baseline: typeof POLICIES.v2024_q4.metrics;
  candidate: typeof POLICIES.v2024_q4.metrics;
}) {
  const rows = [
    { label: "AUC", b: baseline.auc, c: candidate.auc, fmt: (v: number) => v.toFixed(3), better: "up" as const },
    { label: "KS", b: baseline.ks, c: candidate.ks, fmt: (v: number) => v.toFixed(3), better: "up" as const },
    { label: "PSI", b: baseline.psi, c: candidate.psi, fmt: (v: number) => v.toFixed(3), better: "down" as const },
    { label: "通过率", b: baseline.pass_rate, c: candidate.pass_rate, fmt: (v: number) => (v * 100).toFixed(1) + "%", better: "up" as const },
    { label: "批准率", b: baseline.approval_rate, c: candidate.approval_rate, fmt: (v: number) => (v * 100).toFixed(1) + "%", better: "up" as const },
    { label: "坏账率", b: baseline.bad_rate, c: candidate.bad_rate, fmt: (v: number) => (v * 100).toFixed(2) + "%", better: "down" as const },
  ];
  return (
    <section className="bg-[var(--color-paper-raised)] border border-[var(--color-line)]">
      <header className="flex items-center justify-between px-6 pt-5 pb-3 border-b border-[var(--color-line)]">
        <div>
          <div className="text-[10px] font-tabular tracking-[0.25em] text-[var(--color-brass)] uppercase">
            BACKTEST METRICS
          </div>
          <div className="mt-1 font-display text-[18px] text-[var(--color-ink)]">
            指标对比
          </div>
        </div>
        <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--color-ink-muted)] uppercase">
          基线 → 候选
        </div>
      </header>
      <div className="p-6 grid grid-cols-3 gap-x-8 gap-y-5">
        {rows.map((r) => {
          const delta = r.c - r.b;
          const deltaPct = ((delta / r.b) * 100).toFixed(1);
          const improved = r.better === "up" ? delta > 0 : delta < 0;
          const tone = improved ? "text-[var(--color-sage)]" : "text-[var(--color-ember)]";
          const Icon = improved ? TrendingUp : TrendingDown;
          return (
            <div key={r.label}>
              <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--color-ink-muted)] uppercase">
                {r.label}
              </div>
              <div className="mt-1.5 flex items-baseline gap-3">
                <span className="font-tabular text-[13px] text-[var(--color-ink-muted)] line-through">
                  {r.fmt(r.b)}
                </span>
                <ArrowRight size={11} className="text-[var(--color-ink-muted)]" />
                <span className="font-display font-tabular text-[24px] text-[var(--color-ink)] leading-none">
                  {r.fmt(r.c)}
                </span>
              </div>
              <div className={`mt-1.5 flex items-center gap-1 text-[11px] font-tabular ${tone}`}>
                <Icon size={11} />
                {delta > 0 ? "+" : ""}
                {deltaPct}%
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function DslDiff({
  a,
  b,
}: {
  a: Array<{ id: string; text: string }>;
  b: Array<{ id: string; text: string }>;
}) {
  return (
    <div className="font-tabular text-[12px] leading-relaxed space-y-3">
      <div>
        <div className="text-[10px] tracking-[0.2em] text-[var(--color-ink-muted)] uppercase mb-2 flex items-center gap-2">
          <Code2 size={12} /> POLICY DSL
        </div>
        <pre className="bg-[var(--color-paper-sunken)] border-l-2 border-[var(--color-brass)] p-4 overflow-x-auto text-[var(--color-ink)]">
          <code>
            {"/* 候选策略 " + POLICIES.v2025_q1_new.version + " */\n"}
            {"strategy " + POLICIES.v2025_q1_new.version.toLowerCase().replace(/[^\w]/g, "_") + " {\n"}
            {b
              .map((r) => {
                const prev = a.find((x) => x.id.startsWith(r.id.split(" ")[0]));
                const changed = prev && prev.text !== r.text;
                const neu = !prev;
                const prefix = neu ? "+ " : changed ? "~ " : "  ";
                return `  ${prefix}${r.id.padEnd(10)} : ${r.text}`;
              })
              .join("\n")}
            {"\n}"}
          </code>
        </pre>
        <div className="mt-3 flex gap-6 text-[11px] text-[var(--color-ink-muted)]">
          <span>
            <span className="text-[var(--color-sage)]">+</span> 新增
          </span>
          <span>
            <span className="text-[var(--color-brass)]">~</span> 阈值调整
          </span>
          <span>  未变更</span>
        </div>
      </div>
    </div>
  );
}

function HitRates({ rules }: { rules: Array<{ id: string; text: string; hit_rate: number }> }) {
  return (
    <div className="space-y-2">
      {rules.map((r) => (
        <div key={r.id} className="grid grid-cols-12 gap-3 items-center text-[12px]">
          <div className="col-span-2 font-tabular text-[var(--color-brass)]">{r.id}</div>
          <div className="col-span-6 text-[var(--color-ink)] truncate">{r.text}</div>
          <div className="col-span-3">
            <div className="h-1 bg-[var(--color-line)]">
              <div
                className="h-full bg-[var(--color-ink)]"
                style={{ width: `${r.hit_rate}%` }}
              />
            </div>
          </div>
          <div className="col-span-1 text-right font-tabular text-[var(--color-ink-muted)]">
            {r.hit_rate.toFixed(1)}
          </div>
        </div>
      ))}
    </div>
  );
}

function ConfusionCompare() {
  return (
    <Card eyebrow="CONFUSION" title="混淆矩阵对比">
      <div className="grid grid-cols-2 gap-8">
        <ConfusionBlock label="基线" data={CONFUSION.current} />
        <ConfusionBlock label="候选" data={CONFUSION.candidate} highlight />
      </div>
    </Card>
  );
}

function ConfusionBlock({
  label,
  data,
  highlight,
}: {
  label: string;
  data: typeof CONFUSION.current;
  highlight?: boolean;
}) {
  const total = data.tp + data.fp + data.tn + data.fn;
  const precision = (data.tp / (data.tp + data.fp)) * 100;
  const recall = (data.tp / (data.tp + data.fn)) * 100;
  return (
    <div>
      <div className="flex items-baseline justify-between mb-3">
        <div className="font-display text-[14px] text-[var(--color-ink)]">{label}</div>
        <div className="text-[10px] font-tabular text-[var(--color-ink-muted)]">
          n = {total}
        </div>
      </div>
      <div className="grid grid-cols-2 border border-[var(--color-line-strong)]">
        <Cell v={data.tp} label="TP" highlight={highlight} />
        <Cell v={data.fp} label="FP" />
        <Cell v={data.fn} label="FN" />
        <Cell v={data.tn} label="TN" highlight={highlight} />
      </div>
      <div className="mt-3 flex gap-6 text-[11px] font-tabular">
        <span>
          <span className="text-[var(--color-ink-muted)]">P:</span> {precision.toFixed(1)}%
        </span>
        <span>
          <span className="text-[var(--color-ink-muted)]">R:</span> {recall.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}

function Cell({
  v,
  label,
  highlight,
}: {
  v: number;
  label: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`p-3 border-r border-b border-[var(--color-line-strong)] last:border-r-0 ${
        highlight ? "bg-[var(--color-overlay)]" : ""
      }`}
    >
      <div className="text-[9px] font-tabular tracking-wider text-[var(--color-ink-muted)]">
        {label}
      </div>
      <div className="mt-0.5 font-display font-tabular text-[22px] text-[var(--color-ink)] leading-none">
        {v}
      </div>
    </div>
  );
}
