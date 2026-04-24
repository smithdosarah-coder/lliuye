"use client";

/**
 * /archive/riskctrl · Agent2 风控 (Forge) workspace · 三栏对话式
 * 2026-04-21 H2 · canon 横向迁移
 *
 * 左 Query / Rules / Recent · 中 Conversation + Composer · 右 DSL 树 / KS 双线 / Sample bar
 *
 * 继承 canon A 章 · Agent tint: --t-riskctrl (绛紫)
 * 业务：策略经理协同 AI 写 DSL → 回测 KS/通过率/坏账 → 调参 → 送审
 */

import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ChangeEvent } from "react";
import { EvidenceProvider, EvidenceTrail } from "@/components/evidence";
import { RISKCTRL_EVIDENCE } from "@/components/evidence/fixtures";
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";
import { ScanCTA } from "@/components/shared/ScanCTA";
import { CustomerSelector } from "@/components/shared/CustomerSelector";
import { PanelPinHandle } from "@/components/shell/PanelPinHandle";
import {
  RISKCTRL_GLOBAL_STATS,
  RISKCTRL_SESSION,
  type ConversationMessage,
  type DslNode,
  type RiskctrlRecentSession,
  type RuleRef,
  type SampleBar,
} from "@/lib/mock/agent-riskctrl-session";

const AGENT_KEY = "riskctrl";
const AGENT_HREF = "/archive/riskctrl";
const AGENT_ACCENT = "--t-riskctrl";

function truncate(s: string, n: number): string {
  const flat = s.replace(/\s+/g, " ").trim();
  return flat.length > n ? `${flat.slice(0, n - 1)}…` : flat;
}

function msgPinProps(msg: ConversationMessage, speaker: string) {
  return {
    id: `riskctrl:msg:${msg.id}`,
    title: truncate(msg.content, 42),
    subtitle: `${speaker} · ${msg.at}`,
    accentVar: AGENT_ACCENT,
    agentKey: AGENT_KEY,
    href: AGENT_HREF,
    fullText: msg.content,
  };
}

export default function RiskctrlWorkspace() {
  /* 2026-04-23 · demo 初始态 · 未扫描时数据模糊 · ScanCTA onDone 解锁 */
  const [scanned, setScanned] = useState(false);
  return (
    <EvidenceProvider
      items={RISKCTRL_EVIDENCE.items}
      unfilledFields={RISKCTRL_EVIDENCE.unfilledFields}
    >
      <div data-view="archive-riskctrl" data-scanned={scanned ? "yes" : "no"}>
        <RiskHero />
        <RiskIndicatorRow />
        <div className="rpt-body">
          <aside className="rpt-side">
            <QueryPanel />
            <RulesPanel />
            <RecentPanel />
          </aside>
          <main className="rpt-main">
            <ScanCTA
              label="样本回测"
              tone="riskctrl"
              onDone={() => setScanned(true)}
              steps={[
                { label: "装载 DSL 规则 · 3 条件", pct: 18 },
                { label: "采样 · 50K 近 30 日样本", pct: 42 },
                { label: "计算 KS / 通过率", pct: 68 },
                { label: "AB 对比 · 现行版", pct: 88 },
                { label: "生成回测报告 · 完成", pct: 100 },
              ]}
            />
            <ConversationPanel>
              <RiskComposer />
            </ConversationPanel>
          </main>
          <aside className="rpt-aux">
            <RiskOutputPanel />
          </aside>
        </div>
        <EvidenceTrail agentTone="riskctrl" />
      </div>
    </EvidenceProvider>
  );
}

/* ── Hero ────────────────────────────────────────────── */

function RiskHero() {
  const s = RISKCTRL_SESSION;
  return (
    <header className="rpt-hero">
      <div className="rpt-hero-left">
        <div className="rpt-hero-badge" aria-hidden>⌘</div>
        <div>
          <div className="rpt-hero-code">AGENT · 02 · FORGE</div>
          <h1 className="rpt-hero-title">
            风控 <em>Forge.</em>
          </h1>
          {/* 2026-04-23 · 业务逻辑: riskctrl 是策略回测 · 输入是策略诉求 + 样本库 ·
              不针对单客户 · 触发"样本回测" · CustomerSelector 不适用 */}
          <div className="rpt-hero-sub">
            {s.objective} · {s.stage} · KS {s.ks.ksPeak.toFixed(2)} / 通过 {s.ks.passRate}%
          </div>
        </div>
      </div>
      <div className="rpt-hero-stats">
        <Stat label="本周处理" value={RISKCTRL_GLOBAL_STATS.weeklyProcessed} />
        <Stat label="KS 均值" value={RISKCTRL_GLOBAL_STATS.ksAvg} />
        <Stat label="平均时长" value={RISKCTRL_GLOBAL_STATS.avgDuration} />
      </div>
    </header>
  );
}

/* ── v2 Hero · KS / AUC / 通过率 三大指标卡 ──────────── */

function RiskIndicatorRow() {
  const s = RISKCTRL_SESSION;
  const { ksPeak, auc, passRate, badRate } = s.ks;
  const samples = s.samples;
  const pass = samples.find((x) => x.key === "pass");
  const block = samples.find((x) => x.key === "block");
  const review = samples.find((x) => x.key === "review");

  const cards = [
    {
      key: "ks",
      code: "KS",
      label: "KS 峰值",
      value: ksPeak.toFixed(3),
      pct: Math.round(ksPeak * 100),
      caption: `峰值 bin @ 分位 0.${Math.round(ksPeak * 10)}`,
      detail: ksPeak >= 0.4 ? "绿区 · 区分度佳" : ksPeak >= 0.3 ? "关注区" : "红区 · 区分不足",
      tone: ksPeak >= 0.4 ? "good" : ksPeak >= 0.3 ? "warn" : "bad",
    },
    {
      key: "auc",
      code: "AUC",
      label: "AUC 面积",
      value: auc.toFixed(3),
      pct: Math.round(auc * 100),
      caption: `ROC 曲线下面积`,
      detail: auc >= 0.75 ? "绿区 · 模型稳" : auc >= 0.65 ? "关注区" : "红区",
      tone: auc >= 0.75 ? "good" : auc >= 0.65 ? "warn" : "bad",
    },
    {
      key: "pass",
      code: "PASS",
      label: "通过率",
      value: `${passRate.toFixed(1)}%`,
      pct: Math.round(passRate),
      caption: `坏账率 ${badRate.toFixed(1)}%`,
      detail: `拒绝 ${block?.pct ?? 0}% · 复核 ${review?.pct ?? 0}%`,
      tone: passRate >= 30 && badRate <= 3 ? "good" : badRate > 5 ? "bad" : "warn",
    },
  ] as const;

  return (
    <section className="rpt-panel riskctrl-row" aria-label="KS AUC 通过率 指标行">
      <PanelPinHandle
        id="riskctrl:indicators"
        title="KS × AUC × 通过率"
        subtitle={`KS ${ksPeak.toFixed(3)} · 通过 ${passRate}%`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb="三大核心指标 + 样本分档"
      />
      <div className="riskctrl-row-head">
        <span className="eyebrow">METRICS · KS × AUC × 通过率</span>
        <span className="meta">
          样本 <b>{samples.reduce((a, b) => a + b.count, 0).toLocaleString()}</b> 条 ·
          当前策略 <b>{s.currentRule.name} {s.currentRule.version}</b>
        </span>
      </div>
      <ol className="riskctrl-row-list">
        {cards.map((c) => (
          <li key={c.key} className="riskctrl-row-card" data-tone={c.tone}>
            <div className="riskctrl-row-head-card">
              <span className="code">{c.code}</span>
              <span className="tone-dot" aria-hidden />
            </div>
            <div className="riskctrl-row-val">
              <span className="num">{c.value}</span>
            </div>
            <div className="riskctrl-row-lbl">{c.label}</div>
            <div className="riskctrl-row-bar" aria-hidden>
              <div className="riskctrl-row-fill" style={{ width: `${Math.min(c.pct, 100)}%` }} />
            </div>
            <div className="riskctrl-row-caption">{c.caption}</div>
            <div className="riskctrl-row-detail">{c.detail}</div>
          </li>
        ))}
        {pass && (
          <li className="riskctrl-row-dist" aria-label="样本分档">
            <div className="riskctrl-row-head-card">
              <span className="code">DIST</span>
            </div>
            <div className="riskctrl-dist-bar" aria-hidden>
              {samples.map((sb) => (
                <span
                  key={sb.key}
                  className="seg"
                  data-k={sb.key}
                  style={{ width: `${sb.pct}%` }}
                  title={`${sb.label} ${sb.count.toLocaleString()} · ${sb.pct}% · 坏账 ${sb.badRate}%`}
                />
              ))}
            </div>
            <ul className="riskctrl-dist-legend">
              {samples.map((sb) => (
                <li key={sb.key} data-k={sb.key}>
                  <span className="swatch" aria-hidden />
                  <span className="lbl">{sb.label}</span>
                  <span className="p">{sb.pct}%</span>
                </li>
              ))}
            </ul>
            <div className="riskctrl-row-detail">
              坏账率 · 通 {pass.badRate}% / 核 {review?.badRate ?? "—"}% / 拒 {block?.badRate ?? "—"}%
            </div>
          </li>
        )}
      </ol>
    </section>
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

/* ── 左栏 · Query 策略目标 ──────────────────────────── */

function QueryPanel() {
  const q = RISKCTRL_SESSION.query;
  return (
    <section className="rpt-panel rpt-panel--tpl">
      <PanelPinHandle
        id="riskctrl:query"
        title={`策略目标 · ${q.objective}`}
        subtitle={`更新 ${q.updated}`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb="session 起点 + 目标边界"
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">QUERY · 策略目标</div>
          <h3 className="rpt-panel-title">{q.objective}</h3>
        </div>
        <span className="rpt-panel-meta">{q.updated}</span>
      </div>
      <div className="rpt-panel-body rc-q-body">
        <dl className="rc-q-meta">
          <div>
            <dt>样本</dt>
            <dd>{q.sampleLabel}</dd>
          </div>
          <div>
            <dt>规模</dt>
            <dd>
              {q.sampleSize.toLocaleString()} 笔 · {q.windowLabel}
            </dd>
          </div>
        </dl>
        <div className="rc-q-targets">
          <div className="rc-q-targets-lbl">目标指标</div>
          <div className="rc-q-target">
            <span className="k">KS ≥</span>
            <span className="v">{q.targetKS.toFixed(2)}</span>
          </div>
          <div className="rc-q-target">
            <span className="k">通过率</span>
            <span className="v">
              {(q.targetPassRange[0] * 100).toFixed(0)}% - {(q.targetPassRange[1] * 100).toFixed(0)}%
            </span>
          </div>
          <div className="rc-q-target">
            <span className="k">坏账率 ≤</span>
            <span className="v">{(q.targetBadRate * 100).toFixed(1)}%</span>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ── 左栏 · Rules 规则库 ───────────────────────────── */

const RULE_STATUS_LABEL: Record<RuleRef["status"], string> = {
  active: "在线",
  draft: "草稿",
  retired: "下线",
};

function RulesPanel() {
  const rules = RISKCTRL_SESSION.rules;
  const current = RISKCTRL_SESSION.currentRule;
  const active = rules.filter((r) => r.status === "active").length;
  return (
    <section className="rpt-panel rpt-panel--mat">
      <PanelPinHandle
        id="riskctrl:rules"
        title={`规则库 · ${current.version}`}
        subtitle="DSL 规则 + 版本"
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb="当前策略 + 可切历史版本"
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">RULES · 规则库</div>
          <h3 className="rpt-panel-title">
            {active} 在线 · {rules.length} 总
          </h3>
        </div>
        <span className="rpt-panel-meta">{current.version}</span>
      </div>
      <div className="rpt-panel-body rc-rule-body">
        {rules.map((r) => (
          <article
            key={r.id}
            className="rc-rule-card"
            data-status={r.status}
            data-current={r.id === current.id ? "yes" : "no"}
          >
            <header className="rc-rule-head">
              <span className="rc-rule-code">{r.code}</span>
              <span className="rc-rule-status" data-s={r.status}>
                {RULE_STATUS_LABEL[r.status]}
              </span>
            </header>
            <div className="rc-rule-name">{r.label}</div>
            <div className="rc-rule-meta">
              <span>{r.version}</span>
              {r.hit > 0 && <span>· {r.hit.toLocaleString()} 命中</span>}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

/* ── 左栏 · Recent ────────────────────────────────── */

function RecentPanel() {
  const recent = RISKCTRL_SESSION.recentSessions;
  return (
    <section className="rpt-panel rpt-panel--tl">
      <PanelPinHandle
        id="riskctrl:recent"
        title={`近期策略 · ${recent.length} 条`}
        subtitle="跨 session"
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={recent[0]?.objective ?? ""}
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">RECENT · 近期策略</div>
          <h3 className="rpt-panel-title">{recent.length} 条</h3>
        </div>
        <select
          className="rpt-tl-switch"
          aria-label="切换 session"
          defaultValue={RISKCTRL_SESSION.id}
        >
          {recent.map((r) => (
            <option key={r.id} value={r.id}>
              {r.objective}
            </option>
          ))}
        </select>
      </div>
      <div className="rpt-panel-body rpt-tl-body">
        <ol className="rc-rc-list">
          {recent.map((r) => (
            <RecentRow key={r.id} row={r} />
          ))}
        </ol>
      </div>
    </section>
  );
}

function RecentRow({ row }: { row: RiskctrlRecentSession }) {
  const statusLabel =
    row.status === "done" ? "完成" : row.status === "backtesting" ? "回测中" : "草稿";
  return (
    <li className="rc-rc-row" data-status={row.status}>
      <span className="rpt-tl-bar" aria-hidden />
      <div className="rpt-tl-row">
        <span className="rpt-tl-kind">{statusLabel}</span>
        <span className="rpt-tl-at">{row.updated}</span>
      </div>
      <div className="rpt-tl-label">{row.objective}</div>
      <div className="rc-rc-ks">
        <span className="k">KS</span>
        <span className="v">{row.ks.toFixed(2)}</span>
      </div>
    </li>
  );
}

/* ── 中栏 · Conversation / Composer（复用 canon 模式） ── */

function ConversationPanel({ children }: { children?: React.ReactNode }) {
  const msgs = RISKCTRL_SESSION.conversation;
  const s = RISKCTRL_SESSION;
  return (
    <section className="rpt-panel rpt-panel--conv rpt-panel--conv-docked">
      <PanelPinHandle
        id="riskctrl:conversation"
        title="策略对话协作"
        subtitle={`${msgs.length} 条 · FORGE 推理`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb="AI 协助调 DSL + 回测 + 送审"
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">CONVERSATION · 对话协作</div>
          <h3 className="rpt-panel-title">
            {s.objective} · {msgs.length} 条
          </h3>
        </div>
        <span className="rpt-panel-meta">
          KS {s.ks.ksPeak.toFixed(2)} · 阻断 {s.qcCounts.block}
        </span>
      </div>
      <div className="rpt-panel-body rpt-conv-body">
        <ol className="rpt-conv-list">
          {msgs.map((m) => (
            <ConversationItem key={m.id} msg={m} />
          ))}
        </ol>
      </div>
      {children}
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
      <MessagePinHandle {...msgPinProps(msg, "系统")} />
      <span className="rpt-msg-sys-chip">
        <span aria-hidden>◎</span> {msg.content}
      </span>
      <span className="rpt-msg-at">{msg.at}</span>
    </li>
  );
}

function AiQuestionMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--ai rpt-msg--ask">
      <MessagePinHandle {...msgPinProps(msg, "AI · 问")} />
      <div className="rpt-msg-avatar" aria-hidden>⌘</div>
      <div className="rpt-msg-body">
        <div className="rpt-msg-meta">
          <span className="rpt-msg-who">AI · Forge</span>
          {msg.fieldRef && <span className="rpt-msg-fieldref">{msg.fieldRef}</span>}
          <span className="rpt-msg-at">{msg.at}</span>
        </div>
        <div className="rpt-msg-card rpt-msg-card--ask">
          <span className="rpt-msg-card-ic" aria-hidden>?</span>
          <span className="rpt-msg-card-text">{msg.content}</span>
        </div>
      </div>
    </li>
  );
}

function AiResponseMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--ai">
      <MessagePinHandle {...msgPinProps(msg, "AI · Forge")} />
      <div className="rpt-msg-avatar" aria-hidden>⌘</div>
      <div className="rpt-msg-body">
        <div className="rpt-msg-meta">
          <span className="rpt-msg-who">AI · Forge</span>
          {msg.fieldRef && <span className="rpt-msg-fieldref">{msg.fieldRef}</span>}
          <span className="rpt-msg-at">{msg.at}</span>
        </div>
        <div className="rpt-msg-card">
          <div className="rpt-msg-card-text">{msg.content}</div>
          {msg.sectionDiff && (
            <div className="rpt-msg-diff">
              <div className="rpt-msg-diff-lbl">更新 {msg.sectionDiff.sectionAnchor}</div>
              <div className="rpt-msg-diff-after">{msg.sectionDiff.after}</div>
            </div>
          )}
        </div>
      </div>
    </li>
  );
}

function AiThinkingMsg({ msg }: { msg: ConversationMessage }) {
  const [open, setOpen] = useState(false);
  const steps = msg.thinking?.steps ?? [];
  return (
    <li className="rpt-msg rpt-msg--ai rpt-msg--thinking">
      <MessagePinHandle {...msgPinProps(msg, "AI · thinking")} />
      <div className="rpt-msg-avatar rpt-msg-avatar--thinking" aria-hidden>⌘</div>
      <div className="rpt-msg-body">
        <div className="rpt-msg-meta">
          <span className="rpt-msg-who">AI · thinking</span>
          <span className="rpt-msg-at">{msg.at}</span>
        </div>
        <button
          type="button"
          className="rpt-msg-think"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <span className="rpt-msg-think-text">{msg.content}</span>
          <span className="rpt-msg-think-caret" aria-hidden>
            {open ? "▾" : "▸"}
          </span>
        </button>
        {open && steps.length > 0 && (
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
      </div>
    </li>
  );
}

function UserReplyMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--user">
      <MessagePinHandle {...msgPinProps(msg, "策略经理")} />
      <div className="rpt-msg-body rpt-msg-body--user">
        <div className="rpt-msg-meta rpt-msg-meta--user">
          <span className="rpt-msg-at">{msg.at}</span>
          <span className="rpt-msg-who">策略经理 · 李敏</span>
        </div>
        <div className="rpt-msg-card rpt-msg-card--user">{msg.content}</div>
      </div>
      <div className="rpt-msg-avatar rpt-msg-avatar--user" aria-hidden>李</div>
    </li>
  );
}

function UserCommandMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--user rpt-msg--cmd">
      <MessagePinHandle {...msgPinProps(msg, "策略经理 · 指令")} />
      <div className="rpt-msg-body rpt-msg-body--user">
        <div className="rpt-msg-meta rpt-msg-meta--user">
          <span className="rpt-msg-at">{msg.at}</span>
          <span className="rpt-msg-who">策略经理 · /command</span>
        </div>
        <div className="rpt-msg-card rpt-msg-card--cmd">
          <code>{msg.content}</code>
        </div>
      </div>
      <div className="rpt-msg-avatar rpt-msg-avatar--user" aria-hidden>李</div>
    </li>
  );
}

/* ── 中栏 · Composer ────────────────────────────────── */

type ComposerHint = "idle" | "slash" | "mention" | "field";

function RiskComposer() {
  const [value, setValue] = useState("");
  const [hint, setHint] = useState<ComposerHint>("idle");
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 180) + "px";
  }, [value]);

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
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
    else if (last === "#") setHint("field");
    else setHint("idle");
  }

  function submit() {
    if (!value.trim()) return;
    setValue("");
    setHint("idle");
  }

  const ruleCount = RISKCTRL_SESSION.rules.length;

  return (
    <div className="rpt-composer-slot rpt-composer" data-hint={hint}>
      <div className="rpt-composer-bar">
        <textarea
          ref={taRef}
          className="rpt-composer-ta"
          placeholder="提问或下指令 · 输入 / 触发命令 · @ 引用规则 · # 字段"
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
          <kbd>⌘↩</kbd>
        </button>
      </div>
      <div className="rpt-composer-hints">
        <span className="rpt-composer-hint" data-active={hint === "slash"}>
          <kbd>/</kbd> 指令 · lock / rerun / compare
        </span>
        <span className="rpt-composer-hint" data-active={hint === "mention"}>
          <kbd>@</kbd> 规则 · {ruleCount} 条
        </span>
        <span className="rpt-composer-hint" data-active={hint === "field"}>
          <kbd>#</kbd> 字段 · age / score / …
        </span>
      </div>
    </div>
  );
}

/* ── 右栏 · DSL / KS / Sample ─────────────────────────── */

const OUTPUT_ACTIONS = [
  { key: "export", glyph: "⇩", label: "送审", title: "生成送审包 (DSL+回测+对比)" },
  { key: "compare", glyph: "⇄", label: "对比", title: "对比 v1.4 / v1.5 双栏视图" },
  { key: "deploy", glyph: "↑", label: "上线", title: "审批后一键上线" },
  { key: "rerun", glyph: "⟳", label: "重跑", title: "调参后重新回测" },
] as const;

function RiskOutputPanel() {
  const s = RISKCTRL_SESSION;
  const [tab, setTab] = useState<"dsl" | "ks" | "sample">("dsl");
  return (
    <section className="rpt-panel rpt-panel--preview">
      <PanelPinHandle
        id="riskctrl:output"
        title="策略输出看板"
        subtitle="DSL / KS 曲线 / 样本分布"
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb="DSL v1.5-d3 + 回测结果"
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">OUTPUT · DSL v1.5-d3</div>
          <h3 className="rpt-panel-title">
            KS {s.ks.ksPeak.toFixed(2)} · 通过 {s.ks.passRate}%
          </h3>
        </div>
        <div className="rpt-panel-meta">
          <span className="rpt-pv-pct">AUC {s.ks.auc.toFixed(3)}</span>
        </div>
      </div>

      <div className="rpt-pv-toolbar" role="toolbar">
        {OUTPUT_ACTIONS.map((a) => (
          <button key={a.key} type="button" className="rpt-pv-btn" title={a.title}>
            <span className="ic" aria-hidden>{a.glyph}</span>
            <span>{a.label}</span>
          </button>
        ))}
      </div>

      <nav className="rpt-pv-toc rc-out-tabs" aria-label="输出切换">
        <button type="button" className={tab === "dsl" ? "on" : undefined} onClick={() => setTab("dsl")}>
          <span className="a">§一</span>
          <span className="t">DSL 规则树</span>
        </button>
        <button type="button" className={tab === "ks" ? "on" : undefined} onClick={() => setTab("ks")}>
          <span className="a">§二</span>
          <span className="t">KS 双线</span>
        </button>
        <button type="button" className={tab === "sample" ? "on" : undefined} onClick={() => setTab("sample")}>
          <span className="a">§三</span>
          <span className="t">样本分布</span>
        </button>
      </nav>

      <div className="rpt-pv-paper-wrap">
        <article className="rpt-pv-paper rc-out-paper">
          <div className="rpt-pv-paper-head">
            <div className="doc-title">策略 v1.5-d3 · 回测稿</div>
            <div className="doc-sub">
              样本 {s.query.sampleSize.toLocaleString()} · 窗口 {s.query.windowLabel}
            </div>
          </div>
          {tab === "dsl" && <DslView node={s.dsl} />}
          {tab === "ks" && <KSView ks={s.ks} targetKS={s.query.targetKS} />}
          {tab === "sample" && <SampleView samples={s.samples} />}
          <div className="rpt-pv-paper-foot">
            — 以上为 AI 初版策略稿 · 未经风险总监审批不得上线 —
          </div>
        </article>
      </div>

      <footer className="rpt-pv-status">
        <span className="pg">视图 {tab === "dsl" ? "1/3" : tab === "ks" ? "2/3" : "3/3"}</span>
        <span className="sep">·</span>
        <span className="cov">
          通过段坏账 <b>{s.ks.badRate}%</b>
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

function DslView({ node }: { node: DslNode }) {
  return (
    <section className="rc-dsl-sec">
      <header className="rc-out-sec-head">
        <h4 className="rc-out-sec-title">
          <span className="rpt-pv-anchor">§一</span>
          <span>DSL 规则树 · 3 层决策</span>
        </h4>
        <div className="rc-dsl-legend">
          <span className="lg" data-op="IF">IF</span>
          <span className="lg" data-op="AND">AND</span>
          <span className="lg" data-op="OR">OR</span>
          <span className="lg" data-op="THEN">THEN</span>
        </div>
      </header>
      <div className="rc-dsl-tree">
        <DslNodeView node={node} depth={0} />
      </div>
    </section>
  );
}

function DslNodeView({ node, depth }: { node: DslNode; depth: number }) {
  const isAction = node.op === "THEN";
  return (
    <div className="rc-dsl-node" data-op={node.op} data-depth={depth}>
      <div className="rc-dsl-row">
        <span className="rc-dsl-op" data-op={node.op}>
          {node.op}
        </span>
        {node.field && <span className="rc-dsl-field">{node.field}</span>}
        {node.expr && <code className="rc-dsl-expr">{node.expr}</code>}
        {isAction && node.action && (
          <span className="rc-dsl-action" data-action={node.action}>
            {node.action === "pass" ? "通过" : node.action === "block" ? "拒绝" : "复核"}
          </span>
        )}
        {node.reason && <span className="rc-dsl-reason">{node.reason}</span>}
      </div>
      {node.children && node.children.length > 0 && (
        <div className="rc-dsl-children">
          {node.children.map((c) => (
            <DslNodeView key={c.id} node={c} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function KSView({
  ks,
  targetKS,
}: {
  ks: { ksPeak: number; auc: number; passRate: number; badRate: number; points: { bin: number; tpr: number; fpr: number; ks: number }[] };
  targetKS: number;
}) {
  const data = ks.points.map((p) => ({
    bin: `P${p.bin * 10}`,
    TPR: Math.round(p.tpr * 100),
    FPR: Math.round(p.fpr * 100),
    KS: Math.round(p.ks * 100),
  }));
  return (
    <section className="rc-ks-sec">
      <header className="rc-out-sec-head">
        <h4 className="rc-out-sec-title">
          <span className="rpt-pv-anchor">§二</span>
          <span>KS 双线 · 10 分位</span>
        </h4>
        <div className="rc-ks-kpi">
          <span>
            KS peak <b>{ks.ksPeak.toFixed(2)}</b>
          </span>
          <span className="sep">·</span>
          <span>
            目标 <b>{targetKS.toFixed(2)}</b>{" "}
            <em className="ok">(达成)</em>
          </span>
        </div>
      </header>
      <div className="rc-ks-chart">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ink-14)" />
            <XAxis dataKey="bin" tick={{ fill: "var(--ink-60)", fontSize: 10 }} />
            <YAxis tick={{ fill: "var(--ink-60)", fontSize: 10 }} domain={[0, 100]} />
            <Tooltip
              contentStyle={{
                background: "var(--chalk)",
                border: "1px solid var(--ink-14)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="TPR"
              stroke="var(--agent)"
              strokeWidth={2}
              dot={{ r: 2.5, fill: "var(--agent)" }}
              name="TPR · 好客户累计"
            />
            <Line
              type="monotone"
              dataKey="FPR"
              stroke="var(--t-alert, #C85A3C)"
              strokeWidth={2}
              dot={{ r: 2.5, fill: "var(--t-alert, #C85A3C)" }}
              name="FPR · 坏客户累计"
            />
            <Line
              type="monotone"
              dataKey="KS"
              stroke="var(--t-compli, #4A7A5E)"
              strokeWidth={1.4}
              strokeDasharray="4 3"
              dot={false}
              name="KS · 差值"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="rc-ks-legend">
        <span><span className="sw" data-k="tpr" /> TPR (好客户累计)</span>
        <span><span className="sw" data-k="fpr" /> FPR (坏客户累计)</span>
        <span><span className="sw" data-k="ks" /> KS (TPR - FPR)</span>
      </div>
    </section>
  );
}

function SampleView({ samples }: { samples: SampleBar[] }) {
  const total = samples.reduce((a, b) => a + b.count, 0);
  return (
    <section className="rc-sp-sec">
      <header className="rc-out-sec-head">
        <h4 className="rc-out-sec-title">
          <span className="rpt-pv-anchor">§三</span>
          <span>样本分布 · 12,400 笔</span>
        </h4>
        <div className="rc-sp-meta">
          总 <b>{total.toLocaleString()}</b>
        </div>
      </header>
      <ul className="rc-sp-list">
        {samples.map((s) => (
          <li key={s.key} className="rc-sp-row" data-k={s.key}>
            <div className="rc-sp-head">
              <span className="rc-sp-lbl">{s.label}</span>
              <span className="rc-sp-count">{s.count.toLocaleString()}</span>
              <span className="rc-sp-pct">{s.pct.toFixed(1)}%</span>
              <span className="rc-sp-bad">
                坏账 <b>{s.badRate.toFixed(1)}%</b>
              </span>
            </div>
            <div className="rc-sp-bar" aria-hidden>
              <div className="rc-sp-bar-fill" style={{ width: `${s.pct}%` }} />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
