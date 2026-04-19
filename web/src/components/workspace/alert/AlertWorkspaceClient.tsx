"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Play,
  RotateCcw,
  Download,
  AlertOctagon,
  AlertTriangle,
  Circle,
  ArrowRight,
  Activity as ActivityIcon,
} from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card, Stat } from "@/components/viz/Card";
import { PipelineRail } from "@/components/viz/PipelineRail";
import { FileDrop, KBBadge } from "@/components/ui/FileDrop";

const STAGES = [
  { key: "portfolio", label: "存量客户装载" },
  { key: "external", label: "外部舆情 / 司法扫描" },
  { key: "internal", label: "内部交易 / 行为扫描" },
  { key: "cross", label: "双路交叉命中" },
  { key: "rank", label: "信号分级与建议" },
];

type Signal = "red" | "yellow" | "green";

interface Customer {
  id: string;
  name: string;
  industry: string;
  region: string;
  signal: Signal;
  score: number;
  exposure: string;
  events: Array<{ time: string; source: "外部" | "内部"; text: string; kind: "ember" | "brass" | "sage" }>;
  advice: string[];
}

const CUSTOMERS: Customer[] = [
  {
    id: "A192",
    name: "鼎盛商贸",
    industry: "建材批发",
    region: "浙江 · 杭州",
    signal: "red",
    score: 82,
    exposure: "授信 500 万，在贷 380 万",
    events: [
      { time: "T-2d", source: "外部", text: "裁判文书网：被申请执行 230 万元（买卖合同纠纷）", kind: "ember" },
      { time: "T-5d", source: "内部", text: "结算账户日均余额环比 −68%", kind: "ember" },
      { time: "T-7d", source: "外部", text: "关联方「鼎润物流」新增 3 条失信信息", kind: "ember" },
      { time: "T-12d", source: "内部", text: "月度回款集中度从 45% 上升至 81%", kind: "brass" },
      { time: "T-20d", source: "外部", text: "天眼查：法人股权冻结记录新增", kind: "brass" },
    ],
    advice: [
      "48 小时内启动贷后走访",
      "冻结信用卡溢缴款划转权限",
      "提报风控审议，考虑触发提前收回条款",
    ],
  },
  {
    id: "A207",
    name: "瑞达贸易",
    industry: "日用品批发",
    region: "江苏 · 苏州",
    signal: "yellow",
    score: 58,
    exposure: "授信 300 万，在贷 210 万",
    events: [
      { time: "T-3d", source: "外部", text: "主要下游「XX 连锁」被曝门店收缩 30%", kind: "brass" },
      { time: "T-6d", source: "内部", text: "上游货款付款频次由每周 2 次下降为每周 1 次", kind: "brass" },
      { time: "T-18d", source: "外部", text: "行业快报：日用品批发毛利承压", kind: "sage" },
    ],
    advice: [
      "纳入月度关注客户名单",
      "请客户经理上门沟通了解经营状况",
      "下次续授信前重新评估行业敞口",
    ],
  },
  {
    id: "A233",
    name: "华成机电",
    industry: "机电零配件",
    region: "广东 · 东莞",
    signal: "yellow",
    score: 51,
    exposure: "授信 800 万，在贷 620 万",
    events: [
      { time: "T-4d", source: "内部", text: "保函到期未续，保证金账户低于阈值", kind: "brass" },
      { time: "T-10d", source: "外部", text: "招标系统：近 60 天无新中标记录（同期历史有 3 个）", kind: "brass" },
    ],
    advice: ["关注保证金补足", "核实下一季度订单可见度"],
  },
  {
    id: "A041",
    name: "振华精工",
    industry: "精密制造",
    region: "浙江 · 宁波",
    signal: "green",
    score: 22,
    exposure: "授信 1,200 万，在贷 680 万",
    events: [
      { time: "T-15d", source: "内部", text: "结算账户近 30 天正向净流入", kind: "sage" },
      { time: "T-25d", source: "外部", text: "新获国家级专精特新小巨人", kind: "sage" },
    ],
    advice: ["维持现状", "可推荐增额授信"],
  },
];

type Phase = "idle" | "running" | "done";

export function AlertWorkspaceClient() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [active, setActive] = useState<string>();
  const [done, setDone] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<Customer | null>(null);

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
    setSelected(CUSTOMERS[0]);
  };
  const reset = () => {
    setPhase("idle");
    setDone(new Set());
    setSelected(null);
  };

  const redCount = CUSTOMERS.filter((c) => c.signal === "red").length;
  const yellowCount = CUSTOMERS.filter((c) => c.signal === "yellow").length;
  const greenCount = CUSTOMERS.filter((c) => c.signal === "green").length;

  return (
    <div className="grid grid-cols-12 gap-6">
      <aside className="col-span-4 space-y-5">
        <Card eyebrow="SCOPE" title="扫描范围">
          <div className="space-y-2 text-[13px]">
            <Row k="存量客户" v="128 家" />
            <Row k="在贷余额" v="3.82 亿" />
            <Row k="上次扫描" v="T-24h" />
            <Row k="规则集" v="21 条（内外部各半）" />
          </div>
          <Button
            onClick={run}
            disabled={phase === "running"}
            className="w-full mt-5"
          >
            <Play size={14} />
            {phase === "running" ? "扫描中…" : "启动扫描"}
          </Button>
        </Card>

        <Card eyebrow="INPUT · RULES" title="预警规则集">
          <div className="space-y-2.5 mb-4">
            <KBBadge label="默认规则库" count={21} />
          </div>
          <FileDrop
            label="上传预警规则"
            hint="YAML / JSON · 覆盖默认规则集"
            accept=".yaml,.yml,.json"
            kind="kb"
          />
          <div className="mt-3 text-[11px] text-[var(--color-ink-muted)] leading-relaxed">
            外部规则：裁判文书 · 失信 · 税务 · 舆情
            <br />
            内部规则：账户流水 · 还款行为 · 关联交易
          </div>
        </Card>

        <Card eyebrow="INPUT · PORTFOLIO" title="存量客户库">
          <div className="space-y-2.5 mb-4">
            <KBBadge label="默认客户清单" count={128} />
            <KBBadge label="黑名单 / 关联图谱" count={4830} />
          </div>
          <FileDrop
            label="上传客户清单"
            hint="CSV / Excel · 含客户编号与敞口"
            accept=".csv,.xlsx"
            kind="kb"
          />
          <div className="mt-3 text-[11px] text-[var(--color-ink-muted)] leading-relaxed">
            本次扫描范围：在贷余额 3.82 亿，上次扫描 T-24h
          </div>
        </Card>

        <Card eyebrow="PIPELINE" title="扫描流程">
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
                <Download size={14} /> 导出预警清单
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
              <Dashboard red={redCount} yellow={yellowCount} green={greenCount} />
              <div className="grid grid-cols-12 gap-5">
                <div className="col-span-5">
                  <CustomerList
                    customers={CUSTOMERS}
                    selected={selected}
                    onSelect={setSelected}
                  />
                </div>
                <div className="col-span-7">
                  {selected && <DetailPanel c={selected} />}
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <Card className="min-h-[260px] flex items-center justify-center">
                <div className="text-center py-16">
                  <div className="text-[10px] font-tabular tracking-[0.25em] text-[var(--color-brass)] uppercase">
                    {phase === "running" ? "SCANNING" : "AWAITING"}
                  </div>
                  <p className="mt-4 font-display text-[22px] text-[var(--color-ink)]">
                    {phase === "running" ? "双路扫描中" : "待启动扫描"}
                  </p>
                  <p className="mt-2 text-[13px] text-[var(--color-ink-muted)]">
                    外部信号 × 内部信号 → 交叉命中 → 分级建议
                  </p>
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </section>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between border-b border-[var(--color-line)] py-1.5 last:border-0">
      <span className="text-[var(--color-ink-muted)]">{k}</span>
      <span className="font-tabular text-[var(--color-ink)]">{v}</span>
    </div>
  );
}

function Dashboard({
  red,
  yellow,
  green,
}: {
  red: number;
  yellow: number;
  green: number;
}) {
  return (
    <section className="bg-[var(--color-paper-raised)] border border-[var(--color-line)] p-6 grid grid-cols-4 gap-6 items-end">
      <SignalLamp color="ember" count={red} label="红灯" hint="需立即干预" />
      <SignalLamp color="brass" count={yellow} label="黄灯" hint="关注观察" />
      <SignalLamp color="sage" count={green} label="绿灯" hint="健康" />
      <Stat label="总客户" value={128} hint="本次扫描覆盖" />
    </section>
  );
}

function SignalLamp({
  color,
  count,
  label,
  hint,
}: {
  color: "ember" | "brass" | "sage";
  count: number;
  label: string;
  hint: string;
}) {
  const tones = {
    ember: "bg-[var(--color-ember)]",
    brass: "bg-[var(--color-brass)]",
    sage: "bg-[var(--color-sage)]",
  };
  return (
    <div className="flex items-center gap-4">
      <motion.div
        className={`w-6 h-6 rounded-full ${tones[color]}`}
        animate={
          color !== "sage"
            ? { opacity: [1, 0.45, 1], scale: [1, 1.08, 1] }
            : undefined
        }
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        style={{
          boxShadow:
            color === "ember"
              ? "0 0 22px rgba(200,70,58,0.45)"
              : color === "brass"
              ? "0 0 22px rgba(164,126,59,0.35)"
              : "0 0 16px rgba(107,133,120,0.3)",
        }}
      />
      <div>
        <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--color-ink-muted)] uppercase">
          {label}
        </div>
        <div className="mt-0.5 font-display font-tabular text-[30px] leading-none text-[var(--color-ink)]">
          {count}
        </div>
        <div className="mt-0.5 text-[11px] text-[var(--color-ink-muted)]">{hint}</div>
      </div>
    </div>
  );
}

function CustomerList({
  customers,
  selected,
  onSelect,
}: {
  customers: Customer[];
  selected: Customer | null;
  onSelect: (c: Customer) => void;
}) {
  return (
    <Card eyebrow="PORTFOLIO" title="客户清单">
      <div className="space-y-0">
        {customers.map((c) => {
          const isSel = selected?.id === c.id;
          const Icon =
            c.signal === "red" ? AlertOctagon : c.signal === "yellow" ? AlertTriangle : Circle;
          const tone = {
            red: "text-[var(--color-ember)]",
            yellow: "text-[var(--color-brass)]",
            green: "text-[var(--color-sage)]",
          }[c.signal];
          return (
            <button
              key={c.id}
              onClick={() => onSelect(c)}
              className={`w-full text-left px-3 py-3 border-b border-[var(--color-line)] last:border-0 transition-all ${
                isSel
                  ? "bg-[var(--color-overlay)] border-l-2 border-l-[var(--color-ink)]"
                  : "hover:bg-[var(--color-overlay)]"
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon size={16} className={tone} />
                <div className="flex-1 min-w-0">
                  <div className="font-display text-[14px] text-[var(--color-ink)]">
                    {c.name}
                  </div>
                  <div className="text-[10px] font-tabular text-[var(--color-ink-muted)]">
                    {c.id} · {c.industry} · {c.region}
                  </div>
                </div>
                <div className="text-right">
                  <div className={`font-tabular text-[16px] ${tone}`}>
                    {c.score}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </Card>
  );
}

function DetailPanel({ c }: { c: Customer }) {
  const tone = {
    red: "var(--color-ember)",
    yellow: "var(--color-brass)",
    green: "var(--color-sage)",
  }[c.signal];
  return (
    <Card
      eyebrow="SIGNAL DETAIL"
      title={c.name}
      action={
        <span
          className="px-2 py-0.5 text-[10px] font-tabular tracking-wider border uppercase"
          style={{ color: tone, borderColor: tone }}
        >
          {c.signal === "red" ? "RED" : c.signal === "yellow" ? "AMBER" : "GREEN"} ·{" "}
          {c.score}
        </span>
      }
    >
      <div className="mb-4 text-[12px] text-[var(--color-ink-muted)] font-tabular">
        {c.exposure}
      </div>

      <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--color-ink-muted)] uppercase mb-2 flex items-center gap-2">
        <ActivityIcon size={11} /> 信号时间线
      </div>
      <ol className="relative pl-5 space-y-3 mb-5">
        <div className="absolute left-[6px] top-1 bottom-1 w-px bg-[var(--color-line)]" />
        {c.events.map((e, i) => {
          const dotTone =
            e.kind === "ember"
              ? "bg-[var(--color-ember)]"
              : e.kind === "brass"
              ? "bg-[var(--color-brass)]"
              : "bg-[var(--color-sage)]";
          return (
            <li key={i} className="relative">
              <span
                className={`absolute -left-5 top-1.5 w-[9px] h-[9px] rounded-full ${dotTone}`}
              />
              <div className="flex items-baseline gap-2 text-[11px] font-tabular text-[var(--color-ink-muted)]">
                <span>{e.time}</span>
                <span className="opacity-50">·</span>
                <span>{e.source}</span>
              </div>
              <div className="text-[12px] text-[var(--color-ink)] leading-relaxed mt-0.5">
                {e.text}
              </div>
            </li>
          );
        })}
      </ol>

      <div className="pt-4 border-t border-[var(--color-line)]">
        <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--color-brass)] uppercase mb-2">
          处置建议
        </div>
        <ul className="space-y-1.5">
          {c.advice.map((a, i) => (
            <li
              key={i}
              className="text-[12px] text-[var(--color-ink-soft)] leading-relaxed flex gap-2"
            >
              <ArrowRight
                size={12}
                className="mt-1 shrink-0 text-[var(--color-brass)]"
              />
              {a}
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}
