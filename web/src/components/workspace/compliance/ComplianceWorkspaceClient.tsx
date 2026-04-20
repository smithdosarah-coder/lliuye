"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { fetchMockJson } from "@/lib/fallback";
import {
  Play,
  RotateCcw,
  Download,
  FileText,
  AlertOctagon,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  BookOpen,
} from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card, Stat } from "@/components/viz/Card";
import { PipelineRail } from "@/components/viz/PipelineRail";
import { FileDrop, KBBadge } from "@/components/ui/FileDrop";

const STAGES = [
  { key: "parse", label: "新政策解析" },
  { key: "clauses", label: "条款抽取" },
  { key: "match", label: "存量制度召回" },
  { key: "conflict", label: "冲突判定" },
  { key: "revise", label: "修订建议生成" },
];

const POLICIES = [
  {
    key: "bank_internet_loan",
    title: "《商业银行互联网贷款管理办法》2024 修订版",
    agency: "国家金融监督管理总局",
    effective: "2024-12-01",
    kind: "监管办法",
    highlights: [
      "强化合作机构管理：不得将授信审查、风险控制核心环节外包",
      "联合贷款出资比例不得低于 30%",
      "强化消费者权益保护：明示年化利率",
    ],
    scanned: 42,
    conflicts: [
      {
        severity: "hard",
        clause: "第二十条 合作机构管理",
        requirement:
          "商业银行不得将授信审查、风险控制等核心环节外包给合作机构",
        internal: "《互联网贷款合作业务管理办法 v2022》 § 5.3",
        current: "合作机构可承担初筛授信、反欺诈识别等前置风控工作",
        recommend:
          "删除「合作机构可承担初筛授信」条款，仅保留引流与获客协同；反欺诈部分需明确为「信息协同，最终决策由本行完成」",
      },
      {
        severity: "hard",
        clause: "第十六条 联合贷款",
        requirement: "单笔联合贷款中，商业银行出资比例不得低于 30%",
        internal: "《联合贷款合作规范 v2023》 § 3.2",
        current: "与某平台联合贷款，我行出资比例约定为 20%",
        recommend:
          "将与合作方的出资比例条款调整为不低于 30%，存量合同需在 6 个月内完成修订补签",
      },
      {
        severity: "soft",
        clause: "第二十八条 消费者权益保护",
        requirement: "在借款合同主要页面显著位置以年化利率形式展示",
        internal: "《个人贷款合同模板 v2024-01》第 3 条",
        current: "以日利率形式展示，附括号标注年化",
        recommend: "调整合同模板，在首页第一屏用加粗字体直接展示年化利率",
      },
      {
        severity: "soft",
        clause: "第三十二条 催收行为规范",
        requirement: "不得在借款人及担保人以外对第三人进行催收",
        internal: "《贷后管理操作手册 v2023》 § 7",
        current: "未明确禁止对通讯录联系人进行「告知式」催收",
        recommend: "新增明确条款：禁止任何形式的第三方联系，包括信息告知与情况询问",
      },
      {
        severity: "info",
        clause: "第四十条 数据留存",
        requirement: "相关业务数据应留存不少于五年",
        internal: "《数据治理制度 v2024》",
        current: "已要求留存 7 年",
        recommend: "符合要求，无需修订",
      },
    ],
  },
];

type Phase = "idle" | "running" | "done";

// Fixture shape: policies[] + scan_events[{event, policy_id, clause, severity, ...}]
interface FixturePolicy {
  policy_id: string;
  title: string;
  agency?: string;
  effective?: string;
  snippet?: string;
}
interface FixtureConflict {
  event: "conflict_found";
  policy_id: string;
  clause: string;
  severity: "red" | "yellow";
  requirement: string;
  internal_doc?: string;
  internal_current?: string;
  recommend?: string;
  evidence?: string;
}
interface FixtureScanDone {
  event: "scan_done";
  summary: {
    policies_scanned: number;
    conflicts_total: number;
    red_count: number;
    yellow_count: number;
  };
}
type FixtureEvent = FixtureConflict | FixtureScanDone | { event: string; [k: string]: unknown };
interface ComplianceFixture {
  policies: FixturePolicy[];
  scan_events: FixtureEvent[];
  generated_at?: string;
}

// Adapt fixture conflict (severity: red/yellow) to UI conflict (severity: hard/soft/info)
function adaptFixture(f: ComplianceFixture): typeof POLICIES[0] {
  const p = f.policies[0] ?? POLICIES[0];
  const conflicts: typeof POLICIES[0]["conflicts"] = [];
  let red = 0;
  let yellow = 0;
  for (const ev of f.scan_events) {
    if (ev.event !== "conflict_found") continue;
    const cf = ev as FixtureConflict;
    conflicts.push({
      severity: cf.severity === "red" ? "hard" : "soft",
      clause: cf.clause,
      requirement: cf.requirement,
      internal: cf.internal_doc ?? "—",
      current: cf.internal_current ?? "—",
      recommend: cf.recommend ?? "—",
    });
    if (cf.severity === "red") red++;
    else yellow++;
  }
  const scanDoneEv = f.scan_events.find((e) => e.event === "scan_done") as FixtureScanDone | undefined;
  return {
    key: p.policy_id ?? "mock_policy",
    title: p.title,
    agency: p.agency ?? "—",
    effective: p.effective ?? "—",
    kind: "监管办法",
    highlights: p.snippet ? p.snippet.split(/[；;]/).filter(Boolean).slice(0, 4) : POLICIES[0].highlights,
    scanned: scanDoneEv?.summary.policies_scanned ?? f.policies.length,
    conflicts,
    _summary: scanDoneEv?.summary ?? { red_count: red, yellow_count: yellow, conflicts_total: conflicts.length },
  } as typeof POLICIES[0];
}

export function ComplianceWorkspaceClient() {
  const [policy, setPolicy] = useState(POLICIES[0]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [active, setActive] = useState<string>();
  const [done, setDone] = useState<Set<string>>(new Set());
  const [source, setSource] = useState<"mock" | "inline">("inline");

  // Agent5 policy_scan 端点返回泛政务结果, 演示走静态 fixture
  useEffect(() => {
    fetchMockJson<ComplianceFixture>("/mock/compliance_policy_scan.json")
      .then((f) => {
        if (!f?.policies || f.policies.length === 0) return;
        setPolicy(adaptFixture(f));
        setSource("mock");
      })
      .catch(() => {
        /* keep inline POLICIES */
      });
  }, []);

  const run = async () => {
    setPhase("running");
    setDone(new Set());
    for (const s of STAGES) {
      setActive(s.key);
      await new Promise((r) => setTimeout(r, 750));
      setDone((prev) => new Set(prev).add(s.key));
    }
    setActive(undefined);
    setPhase("done");
  };
  const reset = () => {
    setPhase("idle");
    setDone(new Set());
  };

  const hard = policy.conflicts.filter((c) => c.severity === "hard").length;
  const soft = policy.conflicts.filter((c) => c.severity === "soft").length;
  const info = policy.conflicts.filter((c) => c.severity === "info").length;

  return (
    <div className="grid grid-cols-12 gap-6">
      <aside className="col-span-4 space-y-5">
        <Card eyebrow="INPUT · NEW POLICY" title="新政策（触发源）">
          <div className="flex items-start gap-3">
            <BookOpen
              size={18}
              className="text-[var(--accent)] mt-0.5 shrink-0"
            />
            <div>
              <div className="font-display text-[14px] text-[var(--ink)] leading-snug">
                {policy.title}
              </div>
              <div className="mt-1 text-[11px] font-tabular text-[var(--ink-48)]">
                {policy.agency} · {policy.effective}
              </div>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-[var(--ink-14)]">
            <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--ink-48)] uppercase mb-2">
              核心要点
            </div>
            <ul className="space-y-1.5">
              {policy.highlights.map((h, i) => (
                <li
                  key={i}
                  className="text-[12px] text-[var(--ink-80)] leading-relaxed flex gap-2"
                >
                  <ArrowRight
                    size={11}
                    className="mt-1 shrink-0 text-[var(--accent)]"
                  />
                  {h}
                </li>
              ))}
            </ul>
          </div>
          <div className="mt-4 pt-4 border-t border-[var(--ink-14)]">
            <FileDrop
              label="上传新政策文件"
              hint="PDF / Word · 监管办法 / 通知 / 意见"
              accept=".pdf,.doc,.docx"
            />
          </div>
          <div className="mt-3 text-[11px] text-[var(--ink-48)] leading-relaxed">
            新政策作为交叉比对的基准，用于扫描所有行内已有规则。
          </div>
        </Card>

        <Card eyebrow="INPUT · INTERNAL" title="行内已有规则（被扫描方）">
          <div className="space-y-2.5 mb-4">
            <KBBadge label="信贷业务制度" count={18} />
            <KBBadge label="合同 / 协议模板" count={12} />
            <KBBadge label="操作手册 / SOP" count={9} />
            <KBBadge label="合作机构管理" count={3} />
          </div>
          <FileDrop
            label="上传行内制度文件"
            hint="PDF / Word / Markdown · 并入本次扫描"
            accept=".pdf,.doc,.docx,.md"
            kind="kb"
          />
          <div className="mt-3 text-[11px] text-[var(--ink-48)] leading-relaxed">
            扫描机制：条款切片 → 向量召回 → LLM 冲突判定 → 分级修订建议。
          </div>
          <Button
            onClick={run}
            disabled={phase === "running"}
            className="w-full mt-5"
          >
            <Play size={14} />
            {phase === "running" ? "巡检中…" : "启动合规巡检"}
          </Button>
        </Card>

        <Card eyebrow="PIPELINE" title="巡检流程">
          <PipelineRail stages={STAGES} active={active} done={done} />
        </Card>
      </aside>

      <section className="col-span-8 space-y-5">
        <div className="flex justify-end gap-2">
          {source === "mock" && (
            <span
              className="inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-tabular tracking-wider uppercase border border-[#c8463a] text-[#c8463a]"
              title="Agent5 policy_scan 端点泛政务结果，演示使用 /mock/compliance_policy_scan.json"
            >
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#c8463a]" />
              降级模式 · STATIC
            </span>
          )}
          {phase !== "idle" && (
            <>
              <Button variant="secondary" onClick={reset}>
                <RotateCcw size={14} /> 重置
              </Button>
              {phase === "done" && (
                <Button>
                  <Download size={14} /> 导出修订清单
                </Button>
              )}
            </>
          )}
        </div>
        <AnimatePresence mode="wait">
          {phase === "done" ? (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="space-y-5"
            >
              <section className="bg-[var(--g1)] border border-[var(--ink-14)] p-6 grid grid-cols-4 gap-6">
                <Stat label="扫描制度" value={policy.scanned} hint="存量内部文件" />
                <Stat
                  label="硬性冲突"
                  value={hard}
                  hint="需立即修订"
                />
                <Stat
                  label="软性差异"
                  value={soft}
                  hint="建议修订"
                />
                <Stat
                  label="已符合"
                  value={info}
                  hint="满足新规要求"
                />
              </section>

              <Card
                eyebrow="CONFLICTS"
                title="冲突与修订建议"
                action={
                  <span className="text-[10px] font-tabular tracking-wider text-[var(--ink-48)]">
                    按严重程度排序
                  </span>
                }
              >
                <div className="space-y-5">
                  {policy.conflicts.map((c, i) => (
                    <ConflictItem key={i} c={c} />
                  ))}
                </div>
              </Card>
            </motion.div>
          ) : (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <Card className="min-h-[260px] flex items-center justify-center">
                <div className="text-center py-16">
                  <div className="text-[10px] font-tabular tracking-[0.25em] text-[var(--accent)] uppercase">
                    {phase === "running" ? "AUDITING" : "AWAITING"}
                  </div>
                  <p className="mt-4 font-display text-[22px] text-[var(--ink)]">
                    {phase === "running" ? "巡检进行中" : "待启动合规巡检"}
                  </p>
                  <p className="mt-2 text-[13px] text-[var(--ink-48)]">
                    解析 → 条款 → 召回 → 冲突 → 修订
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

function ConflictItem({
  c,
}: {
  c: {
    severity: string;
    clause: string;
    requirement: string;
    internal: string;
    current: string;
    recommend: string;
  };
}) {
  const meta = {
    // --color-ember → #c8463a (semantic danger; kept literal across themes)
    hard: {
      Icon: AlertOctagon,
      tone: "text-[#c8463a]",
      border: "border-[#c8463a]",
      label: "HARD",
    },
    soft: {
      Icon: AlertTriangle,
      tone: "text-[var(--accent)]",
      border: "border-[var(--accent)]",
      label: "SOFT",
    },
    info: {
      Icon: CheckCircle2,
      tone: "text-[var(--safe)]",
      border: "border-[var(--safe)]",
      label: "PASS",
    },
  }[c.severity]!;
  const Icon = meta.Icon;
  return (
    <div className={`border-l-2 ${meta.border} pl-5 pb-5 border-b border-b-[var(--ink-14)] last:border-b-0 last:pb-0`}>
      <div className="flex items-baseline gap-3 flex-wrap">
        <span className={`inline-flex items-center gap-1 text-[10px] font-tabular tracking-[0.2em] ${meta.tone}`}>
          <Icon size={11} /> {meta.label}
        </span>
        <span className="font-display text-[15px] text-[var(--ink)]">
          {c.clause}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-6">
        <div>
          <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--accent)] uppercase mb-1.5">
            新规要求
          </div>
          <p className="text-[12px] text-[var(--ink)] leading-relaxed">
            {c.requirement}
          </p>
        </div>
        <div>
          <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--ink-48)] uppercase mb-1.5 flex items-center gap-1">
            <FileText size={11} /> 内部制度
          </div>
          <p className="text-[11px] text-[var(--ink-48)] font-tabular mb-1">
            {c.internal}
          </p>
          <p className="text-[12px] text-[var(--ink-80)] leading-relaxed">
            {c.current}
          </p>
        </div>
      </div>

      {c.severity !== "info" && (
        <div className="mt-4 pt-3 border-t border-[var(--ink-14)]">
          {/* --color-ember → #c8463a (semantic danger; kept literal across themes) */}
          <div className="text-[10px] font-tabular tracking-[0.2em] text-[#c8463a] uppercase mb-1.5">
            修订建议
          </div>
          <p className="text-[12px] text-[var(--ink)] leading-relaxed">
            {c.recommend}
          </p>
        </div>
      )}
    </div>
  );
}
