"use client";

/**
 * /archive/alert · Agent 04 TOWER · 对话式贷中预警 workspace（canon 横向套 2026-04-21 H4）
 * 左：query + rules + pipeline + recent / 中：对话 + AlertComposer /
 * 右：分档分布 stacked · 30 天热力 · 触达率 三切换
 * 壳类：.v-archive--canon[data-agent="alert"] → --agent = var(--t-alert) 赭红
 */

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { ScanCTA } from "@/components/shared/ScanCTA";
import { CustomerSelector } from "@/components/shared/CustomerSelector";
import {
  ALERT_GLOBAL_STATS,
  ALERT_SESSION,
  type AlertPipelineStep,
  type AlertQuery,
  type AlertRecentSession,
  type AlertRule,
  type ConversationMessage,
  type HeatCell,
  type IndustryDistribution,
  type ReachRate,
  type TopCase,
} from "@/lib/mock/agent-alert-session";

type OutputTab = "dist" | "heat" | "reach";

export default function AlertWorkspace() {
  const session = ALERT_SESSION;
  const [tab, setTab] = useState<OutputTab>("dist");
  /* 2026-04-23 · demo 初始态 · 未扫描时数据模糊 · ScanCTA onDone 解锁 */
  const [scanned, setScanned] = useState(false);

  return (
    <div className="rpt-workspace" data-scanned={scanned ? "yes" : "no"}>
      <HeroSection
        weeklyProcessed={ALERT_GLOBAL_STATS.weeklyProcessed}
        redRate={ALERT_GLOBAL_STATS.redRate}
        avgDuration={ALERT_GLOBAL_STATS.avgDuration}
        objective={session.objective}
        stage={session.stage}
        updated={session.updated}
        totals={session.totals}
        qcCounts={session.qcCounts}
      />

      <TrafficLightWall
        totals={session.totals}
        rules={session.rules}
        reach={session.reach}
        topCases={session.topCases}
      />

      <div className="rpt-grid">
        <aside className="rpt-col rpt-col--left">
          <QueryPanel q={session.query} />
          <RulesPanel rules={session.rules} />
          <PipelinePanel steps={session.pipeline} />
          <RecentPanel recent={session.recentSessions} />
        </aside>

        <section className="rpt-col rpt-col--mid">
          <ScanCTA
            label="全客户巡检"
            tone="alert"
            onDone={() => setScanned(true)}
            steps={[
              { label: "加载在贷客户池", pct: 16 },
              { label: "外部扫描 · 政策 / 诉讼 / 舆情", pct: 40 },
              { label: "内部交易 · 账户流水异动", pct: 64 },
              { label: "双路交叉命中分级", pct: 86 },
              { label: "生成处置建议 · 完成", pct: 100 },
            ]}
          />
          <ConversationPanel msgs={session.conversation}>
            <AlertComposer />
          </ConversationPanel>
        </section>

        <section className="rpt-col rpt-col--right">
          <OutputPanel
            tab={tab}
            onTabChange={setTab}
            distribution={session.distribution}
            heat={session.heat}
            reach={session.reach}
            topCases={session.topCases}
            totals={session.totals}
          />
        </section>
      </div>
    </div>
  );
}

/* ────────────────────── HERO ────────────────────── */

function HeroSection(p: {
  weeklyProcessed: string;
  redRate: string;
  avgDuration: string;
  objective: string;
  stage: string;
  updated: string;
  totals: { red: number; yellow: number; green: number };
  qcCounts: { block: number; warn: number; info: number };
}) {
  return (
    <header className="rpt-hero">
      <div className="rpt-hero__eyebrow">
        <span className="rpt-hero__badge" aria-hidden>◉</span>
        <span>AGENT · 04 · TOWER</span>
        <span className="rpt-hero__sep">·</span>
        <span>贷中预警引擎</span>
      </div>
      {/* 2026-04-23 · 业务逻辑: alert 是在贷客户池批量扫描 · 不选单客户
          输入是知识库（规则库 / 外部信号源）· 触发"全客户巡检"即可 · CustomerSelector 不适用 */}
      <h1 className="rpt-hero__title">{p.objective}</h1>
      <p className="rpt-hero__sub">
        {p.stage} · 红 {p.totals.red} / 黄 {p.totals.yellow} / 绿 {p.totals.green} · {p.updated}
      </p>
      <dl className="rpt-hero__stats">
        <div className="rpt-hero__stat">
          <dt>本周已扫</dt>
          <dd>{p.weeklyProcessed}</dd>
        </div>
        <div className="rpt-hero__stat">
          <dt>红档占比</dt>
          <dd>{p.redRate}</dd>
        </div>
        <div className="rpt-hero__stat">
          <dt>平均耗时</dt>
          <dd>{p.avgDuration}</dd>
        </div>
        <div className="rpt-hero__stat">
          <dt>质检</dt>
          <dd className="rpt-hero__qc">
            <span className="rpt-hero__qc-chip" data-tone="block">{p.qcCounts.block}</span>
            <span className="rpt-hero__qc-chip" data-tone="warn">{p.qcCounts.warn}</span>
            <span className="rpt-hero__qc-chip" data-tone="info">{p.qcCounts.info}</span>
          </dd>
        </div>
      </dl>
    </header>
  );
}

/* ─────────────── v2 Hero · 红黄绿三灯状态墙 ─────────────── */

function TrafficLightWall(p: {
  totals: { red: number; yellow: number; green: number };
  rules: AlertRule[];
  reach: ReachRate[];
  topCases: TopCase[];
}) {
  const { red, yellow, green } = p.totals;
  const total = red + yellow + green;
  const redCases = p.topCases.filter((c) => c.tier === "red");

  const redReach = p.reach.find((r) => r.tier === "red");
  const ylReach = p.reach.find((r) => r.tier === "yellow");
  const greenReach = p.reach.find((r) => r.tier === "green");

  const activeRules = p.rules.filter((r) => r.enabled).length;

  const lights = [
    {
      tier: "red" as const,
      label: "红档 · 立即处置",
      count: red,
      pct: total ? Math.round((red / total) * 100) : 0,
      caption: redReach ? `触达 ${redReach.reached} / ${redReach.total}` : "—",
      detail: `TOP ${redCases.length} 单 · ${redCases[0]?.customer ?? "—"} ${redCases[0]?.amount ?? ""}`,
      animate: true,
    },
    {
      tier: "yellow" as const,
      label: "黄档 · 重点观察",
      count: yellow,
      pct: total ? Math.round((yellow / total) * 100) : 0,
      caption: ylReach ? `触达 ${ylReach.reached} / ${ylReach.total}` : "—",
      detail: `触达率 ${ylReach ? ylReach.reachedPct.toFixed(1) + "%" : "—"}`,
      animate: false,
    },
    {
      tier: "green" as const,
      label: "绿档 · 常规跟踪",
      count: green,
      pct: total ? Math.round((green / total) * 100) : 0,
      caption: greenReach ? `触达 ${greenReach.reached} / ${greenReach.total}` : "—",
      detail: `平稳 · 下轮扫描 T+7`,
      animate: false,
    },
  ];

  return (
    <section className="rpt-panel alert-wall" aria-label="红黄绿三灯状态墙">
      <div className="alert-wall-head">
        <span className="eyebrow">TRAFFIC · 红黄绿三灯 · 命中 {total.toLocaleString()} 户</span>
        <span className="meta">
          <b>{activeRules}</b> 条规则活跃 · 红档 TOP {redCases.length} 单待处置
        </span>
      </div>
      <ol className="alert-wall-list">
        {lights.map((l) => (
          <li key={l.tier} className="alert-wall-light" data-tier={l.tier} data-animate={l.animate}>
            <div className="alert-wall-bulb" aria-hidden>
              <span className="alert-wall-bulb-inner" />
              <span className="alert-wall-bulb-ring" />
            </div>
            <div className="alert-wall-body">
              <div className="alert-wall-row">
                <span className="lbl">{l.label}</span>
                <span className="pct">{l.pct}%</span>
              </div>
              <div className="alert-wall-count">
                <span className="num">{l.count}</span>
                <span className="unit">户</span>
              </div>
              <div className="alert-wall-bar" aria-hidden>
                <div className="alert-wall-fill" style={{ width: `${l.pct}%` }} />
              </div>
              <div className="alert-wall-caption">{l.caption}</div>
              <div className="alert-wall-detail">{l.detail}</div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

/* ────────────────────── LEFT ────────────────────── */

function QueryPanel({ q }: { q: AlertQuery }) {
  return (
    <div className="rpt-panel al-q">
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">扫描配置</div>
        <div className="rpt-panel__updated">更新 {q.updated}</div>
      </div>
      <div className="rpt-panel__body">
        <div className="al-q__obj">{q.objective}</div>
        <dl className="al-q__dl">
          <div className="al-q__row">
            <dt>客户池</dt>
            <dd>
              <span className="al-q__pool">{q.poolLabel}</span>
              <span className="al-q__count">{q.poolSize.toLocaleString()}</span>
            </dd>
          </div>
          <div className="al-q__row">
            <dt>时间窗</dt>
            <dd>{q.windowLabel}</dd>
          </div>
          <div className="al-q__row">
            <dt>规则版本</dt>
            <dd>
              <span className="al-q__ver">{q.ruleVersion}</span>
            </dd>
          </div>
          <div className="al-q__row">
            <dt>触发源</dt>
            <dd>{q.triggerSource}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}

function RulesPanel({ rules }: { rules: AlertRule[] }) {
  const enabled = rules.filter((r) => r.enabled).length;
  const totalHit = rules.reduce((s, r) => s + (r.enabled ? r.hit : 0), 0);
  return (
    <div className="rpt-panel al-rl">
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">规则</div>
        <div className="rpt-panel__counter">
          {enabled}/{rules.length} · 命中 {totalHit}
        </div>
      </div>
      <div className="rpt-panel__body">
        <ul className="al-rl__list">
          {rules.map((r) => (
            <li
              key={r.id}
              className="al-rl__item"
              data-cat={r.category}
              data-sev={r.severity}
              data-enabled={r.enabled ? "yes" : "no"}
            >
              <span className="al-rl__code">{r.code}</span>
              <div className="al-rl__body">
                <div className="al-rl__label">{r.label}</div>
                <div className="al-rl__meta">
                  <span className="al-rl__cat">{CAT_LABEL[r.category]}</span>
                  <span className="al-rl__sep">·</span>
                  <span className="al-rl__sev">{SEV_LABEL[r.severity]}</span>
                </div>
              </div>
              <span className="al-rl__hit">{r.enabled ? r.hit : "—"}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

const CAT_LABEL: Record<string, string> = { external: "外部", internal: "内部", cross: "交叉" };
const SEV_LABEL: Record<string, string> = { high: "高危", mid: "中危", low: "低危" };

function PipelinePanel({ steps }: { steps: AlertPipelineStep[] }) {
  return (
    <div className="rpt-panel al-pl">
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">扫描流水</div>
        <div className="rpt-panel__counter">
          {steps.filter((s) => s.status === "done").length}/{steps.length}
        </div>
      </div>
      <div className="rpt-panel__body">
        <ol className="al-pl__list">
          {steps.map((s, i) => (
            <li key={s.id} className="al-pl__item" data-status={s.status}>
              <span className="al-pl__idx">{String(i + 1).padStart(2, "0")}</span>
              <div className="al-pl__body">
                <div className="al-pl__label">{s.label}</div>
                {s.note ? <div className="al-pl__note">{s.note}</div> : null}
              </div>
              <span className="al-pl__mark" aria-hidden>
                {s.status === "done" ? "✓" : s.status === "active" ? "●" : "○"}
              </span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function RecentPanel({ recent }: { recent: AlertRecentSession[] }) {
  return (
    <div className="rpt-panel al-rc">
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">近期</div>
        <div className="rpt-panel__counter">{recent.length}</div>
      </div>
      <div className="rpt-panel__body">
        <ul className="al-rc__list">
          {recent.map((r) => (
            <li key={r.id} className="al-rc__item">
              <div className="al-rc__head">
                <div className="al-rc__name">{r.objective}</div>
                <span className="al-rc__red">红 {r.redCount}</span>
              </div>
              <div className="al-rc__meta">
                <span>{r.pool.toLocaleString()} 户</span>
                <span className="al-rc__time">{r.updated}</span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ────────────────────── MID ────────────────────── */

function ConversationPanel({
  msgs,
  children,
}: {
  msgs: ConversationMessage[];
  children?: React.ReactNode;
}) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [msgs.length]);

  return (
    <div className="rpt-panel rpt-panel--conv rpt-panel--conv-docked">
      <div className="rpt-conv" ref={scrollRef}>
        {msgs.map((m) => (
          <ConversationMsg key={m.id} m={m} />
        ))}
      </div>
      {children}
    </div>
  );
}

function ConversationMsg({ m }: { m: ConversationMessage }) {
  if (m.kind === "system-event") {
    return (
      <div className="rpt-msg rpt-msg--sys">
        <span className="rpt-msg__dot" aria-hidden>◈</span>
        <span className="rpt-msg__sys-txt">{m.content}</span>
        <span className="rpt-msg__at">{m.at}</span>
      </div>
    );
  }
  if (m.kind === "user-reply" || m.kind === "user-command") {
    const isCmd = m.kind === "user-command";
    return (
      <div className="rpt-msg rpt-msg--user" data-cmd={isCmd ? "yes" : "no"}>
        <div className="rpt-msg__head">
          <span className="rpt-msg__who">{isCmd ? "指令" : "我"}</span>
          <span className="rpt-msg__at">{m.at}</span>
        </div>
        <div className="rpt-msg__body">{m.content}</div>
      </div>
    );
  }
  if (m.kind === "ai-thinking") {
    return (
      <div className="rpt-msg rpt-msg--ai rpt-msg--thinking">
        <div className="rpt-msg__head">
          <span className="rpt-msg__who">TOWER · 推理</span>
          <span className="rpt-msg__at">{m.at}</span>
        </div>
        <div className="rpt-msg__body">{m.content}</div>
        {m.thinking?.steps?.length ? (
          <details className="rpt-think" open>
            <summary className="rpt-think__sum">推理过程 · {m.thinking.steps.length} 步</summary>
            <ol className="rpt-think__list">
              {m.thinking.steps.map((s, i) => (
                <li key={i} className="rpt-think__item">
                  <div className="rpt-think__lbl">
                    <span className="rpt-think__idx">{String(i + 1).padStart(2, "0")}</span>
                    {s.label}
                  </div>
                  {s.evidences?.length ? (
                    <ul className="rpt-think__ev">
                      {s.evidences.map((e, j) => (
                        <li key={j}>{e}</li>
                      ))}
                    </ul>
                  ) : null}
                </li>
              ))}
            </ol>
          </details>
        ) : null}
      </div>
    );
  }
  const who = m.kind === "ai-question" ? "TOWER · 问" : "TOWER";
  return (
    <div className="rpt-msg rpt-msg--ai" data-q={m.kind === "ai-question" ? "yes" : "no"}>
      <div className="rpt-msg__head">
        <span className="rpt-msg__who">{who}</span>
        <span className="rpt-msg__at">{m.at}</span>
        {m.fieldRef ? <span className="rpt-msg__ref">{m.fieldRef}</span> : null}
      </div>
      <div className="rpt-msg__body">{m.content}</div>
      {m.sectionDiff ? (
        <div className="rpt-msg__diff">
          <span className="rpt-msg__diff-anchor">{m.sectionDiff.sectionAnchor}</span>
          <span className="rpt-msg__diff-after">{m.sectionDiff.after}</span>
        </div>
      ) : null}
    </div>
  );
}

function AlertComposer() {
  const [value, setValue] = useState("");
  const hints = ["看 top 红档", "行业切片 · 建材", "升级触达", "下发工单", "对比上周"];
  return (
    <div className="rpt-composer">
      <div className="rpt-composer__hints">
        {hints.map((h) => (
          <button
            key={h}
            type="button"
            className="rpt-composer__hint"
            onClick={() => setValue((v) => (v ? v + " / " + h : h))}
          >
            {h}
          </button>
        ))}
      </div>
      <textarea
        className="rpt-composer__ta"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="对 TOWER 提问 / 给指令：看 top 红档、切行业、升级触达、下发工单…"
        rows={3}
      />
      <div className="rpt-composer__foot">
        <span className="rpt-composer__hint-txt">Enter 发 · Shift+Enter 换行 · /dispatch 下发触达</span>
        <button type="button" className="rpt-composer__send" disabled={!value.trim()}>
          发送
        </button>
      </div>
    </div>
  );
}

/* ────────────────────── RIGHT · OUTPUT ────────────────────── */

function OutputPanel(p: {
  tab: OutputTab;
  onTabChange: (t: OutputTab) => void;
  distribution: IndustryDistribution[];
  heat: HeatCell[];
  reach: ReachRate[];
  topCases: TopCase[];
  totals: { red: number; yellow: number; green: number };
}) {
  return (
    <div className="rpt-panel al-out">
      <div className="rpt-panel__head al-out__head">
        <div className="rpt-panel__eyebrow">预警看板</div>
        <div className="al-out__tabs" role="tablist">
          <TabBtn active={p.tab === "dist"} onClick={() => p.onTabChange("dist")}>分档</TabBtn>
          <TabBtn active={p.tab === "heat"} onClick={() => p.onTabChange("heat")}>热力</TabBtn>
          <TabBtn active={p.tab === "reach"} onClick={() => p.onTabChange("reach")}>触达</TabBtn>
        </div>
      </div>
      <div className="rpt-panel__body al-out__body">
        {p.tab === "dist" ? (
          <DistView distribution={p.distribution} totals={p.totals} topCases={p.topCases} />
        ) : null}
        {p.tab === "heat" ? <HeatView heat={p.heat} /> : null}
        {p.tab === "reach" ? <ReachView reach={p.reach} /> : null}
      </div>
    </div>
  );
}

function TabBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button type="button" className="al-out__tab" data-active={active ? "yes" : "no"} onClick={onClick}>
      {children}
    </button>
  );
}

/* ── 分档 stacked ── */

function DistView(p: {
  distribution: IndustryDistribution[];
  totals: { red: number; yellow: number; green: number };
  topCases: TopCase[];
}) {
  const maxTotal = Math.max(...p.distribution.map((d) => d.total));
  const tot = p.totals.red + p.totals.yellow + p.totals.green;
  return (
    <div className="al-dv">
      <div className="al-dv__tot">
        <div className="al-dv__tot-head">全池 {tot.toLocaleString()} 户</div>
        <div className="al-dv__tot-bar">
          <div
            className="al-dv__tot-seg al-dv__tot-seg--red"
            style={{ width: `${(p.totals.red / tot) * 100}%` } as CSSProperties}
            title={`红 ${p.totals.red}`}
          />
          <div
            className="al-dv__tot-seg al-dv__tot-seg--yellow"
            style={{ width: `${(p.totals.yellow / tot) * 100}%` } as CSSProperties}
            title={`黄 ${p.totals.yellow}`}
          />
          <div
            className="al-dv__tot-seg al-dv__tot-seg--green"
            style={{ width: `${(p.totals.green / tot) * 100}%` } as CSSProperties}
            title={`绿 ${p.totals.green}`}
          />
        </div>
        <div className="al-dv__tot-legend">
          <span className="al-dv__leg al-dv__leg--red">红 {p.totals.red}</span>
          <span className="al-dv__leg al-dv__leg--yellow">黄 {p.totals.yellow}</span>
          <span className="al-dv__leg al-dv__leg--green">绿 {p.totals.green}</span>
        </div>
      </div>

      <div className="al-dv__ttl">按行业切片</div>
      <ul className="al-dv__list">
        {p.distribution.map((d) => {
          const rp = (d.red / d.total) * 100;
          const yp = (d.yellow / d.total) * 100;
          const gp = (d.green / d.total) * 100;
          const barW = (d.total / maxTotal) * 100;
          return (
            <li key={d.industry} className="al-dv__row">
              <div className="al-dv__lbl">{d.industry}</div>
              <div className="al-dv__bar-wrap" style={{ width: `${barW}%` } as CSSProperties}>
                <div className="al-dv__bar">
                  <div className="al-dv__seg al-dv__seg--red" style={{ width: `${rp}%` } as CSSProperties} />
                  <div className="al-dv__seg al-dv__seg--yellow" style={{ width: `${yp}%` } as CSSProperties} />
                  <div className="al-dv__seg al-dv__seg--green" style={{ width: `${gp}%` } as CSSProperties} />
                </div>
              </div>
              <div className="al-dv__nums">
                <span className="al-dv__num al-dv__num--red">{d.red}</span>
                <span className="al-dv__num al-dv__num--yellow">{d.yellow}</span>
                <span className="al-dv__num al-dv__num--green">{d.green}</span>
              </div>
            </li>
          );
        })}
      </ul>

      <div className="al-dv__ttl">Top 红档</div>
      <ul className="al-dv__tops">
        {p.topCases.filter((c) => c.tier === "red").map((c) => (
          <li key={c.id} className="al-dv__tc">
            <div className="al-dv__tc-head">
              <span className="al-dv__tc-tier" data-tier={c.tier}>红</span>
              <div className="al-dv__tc-name">{c.customer}</div>
              <span className="al-dv__tc-amt">{c.amount}</span>
            </div>
            <ul className="al-dv__tc-trig">
              {c.triggers.map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
            <div className="al-dv__tc-adv">处置 · {c.advice}</div>
            <div className="al-dv__tc-time">{c.lastUpdate}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── 热力日历 ── */

function HeatView({ heat }: { heat: HeatCell[] }) {
  const total = heat.reduce((s, c) => s + c.count, 0);
  const peak = Math.max(...heat.map((c) => c.count));
  return (
    <div className="al-hv">
      <div className="al-hv__kpi">
        <div>
          <span className="al-hv__kpi-num">{total}</span>
          <span className="al-hv__kpi-unit">次</span>
        </div>
        <div className="al-hv__kpi-sub">
          近 30 天累计触发 · 峰值 {peak}/日 · 均值 {(total / heat.length).toFixed(1)}/日
        </div>
      </div>

      <div className="al-hv__grid">
        {heat.map((c) => (
          <div
            key={c.date}
            className="al-hv__cell"
            data-level={c.level}
            title={`${c.date} · ${c.count} 次`}
          >
            <span className="al-hv__cell-n">{c.count}</span>
          </div>
        ))}
      </div>

      <div className="al-hv__legend">
        <span>少</span>
        <span className="al-hv__leg-cell" data-level={0} />
        <span className="al-hv__leg-cell" data-level={1} />
        <span className="al-hv__leg-cell" data-level={2} />
        <span className="al-hv__leg-cell" data-level={3} />
        <span className="al-hv__leg-cell" data-level={4} />
        <span>多</span>
      </div>

      <div className="al-hv__note">
        近一周触发明显抬头（+180%）· 建议：重点关注 4-16 之后命中的 63 户建材/制造业客户
      </div>
    </div>
  );
}

/* ── 触达率 ── */

function ReachView({ reach }: { reach: ReachRate[] }) {
  return (
    <div className="al-rv">
      <ul className="al-rv__list">
        {reach.map((r) => (
          <li key={r.tier} className="al-rv__item" data-tier={r.tier}>
            <div className="al-rv__head">
              <span className="al-rv__tier" data-tier={r.tier}>
                {r.tier === "red" ? "红" : r.tier === "yellow" ? "黄" : "绿"}
              </span>
              <div className="al-rv__lbl">{r.label}</div>
              <span className="al-rv__pct">{r.reachedPct.toFixed(1)}%</span>
            </div>
            <div className="al-rv__bar">
              <div
                className="al-rv__bar-fill"
                data-tier={r.tier}
                style={{ width: `${r.reachedPct}%` } as CSSProperties}
              />
            </div>
            <div className="al-rv__meta">
              已触达 {r.reached.toLocaleString()} / 全量 {r.total.toLocaleString()}
            </div>
            <div className="al-rv__ch">
              <span className="al-rv__ch-item">
                <span className="al-rv__ch-lbl">电话</span>
                <span className="al-rv__ch-num">{r.channels.phone}</span>
              </span>
              <span className="al-rv__ch-item">
                <span className="al-rv__ch-lbl">短信</span>
                <span className="al-rv__ch-num">{r.channels.sms}</span>
              </span>
              <span className="al-rv__ch-item">
                <span className="al-rv__ch-lbl">面访</span>
                <span className="al-rv__ch-num">{r.channels.visit}</span>
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
