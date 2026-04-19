import Link from "next/link";
import type { CSSProperties } from "react";
import {
  TODAY_FEED,
  TODAY_IDLE_SHEETS,
  TODAY_RUNNING_SHEETS,
  TODAY_SUMMARY,
  TODAY_TASKS,
} from "@/lib/mock/today";

export const metadata = {
  title: "今日 · 乾策 Studio",
};

export default function TodayPage() {
  return (
    <div className="v-today">
      <div className="eyebrow">
        <span className="sep" />
        2026 · 04 · 19 · Saturday <em>华东分行 · 王哲</em>
      </div>

      <h1 className="hero-h1">
        今日 <em>collaboration</em> 起点
      </h1>

      <p className="lede">
        本日工作围绕 <strong>宁海汇通终审</strong>、<strong>星河医药预警复核</strong>
        与 <strong>§214 政策合规筛查</strong> 三个主线推进。
        AI 助手 <span className="num">3</span> 个在跑，待办
        <span className="num">{TODAY_TASKS.length}</span> 项，未读消息
        <span className="num">3</span> 条。
      </p>

      <div className="hero-meta">
        <span className="pill">
          <span className="cn">今日实时</span> · 08:47
        </span>
        <span className="kv">
          <span className="k">PIPELINE</span>
          <span className="v">{TODAY_SUMMARY.pipeline.value}</span>
          <span className="k" style={{ marginLeft: 6 }}>{TODAY_SUMMARY.pipeline.sub}</span>
        </span>
        <span className="kv">
          <span className="k">QUEUE</span>
          <span className="v">{TODAY_SUMMARY.queue.value}</span>
          <span className="k" style={{ marginLeft: 6 }}>{TODAY_SUMMARY.queue.sub}</span>
        </span>
        <span className="kv">
          <span className="k">RISK</span>
          <span className="v">{TODAY_SUMMARY.risk.value}</span>
          <span className="k" style={{ marginLeft: 6 }}>{TODAY_SUMMARY.risk.sub}</span>
        </span>
      </div>

      <div className="v-grid-3">
        {/* 消息预览 */}
        <Link href="/dispatch" className="v-card">
          <div className="v-card-tag">
            <span className="dash" />
            消息 · Dispatch
            <span className="sum">{TODAY_FEED.length} ITEMS</span>
          </div>
          <div className="v-card-h">
            {TODAY_FEED.length}
            <em>messages</em>
          </div>
          <ul>
            {TODAY_FEED.slice(0, 4).map((f) => (
              <li key={f.id}>
                <span>
                  {f.who}
                  <span className="sub">{f.preview}</span>
                </span>
                <span className="ts">{f.ts}</span>
              </li>
            ))}
          </ul>
        </Link>

        {/* A-017: agent · 正在跑 — card.warm.sheet-card (shell.html:2047-2131) */}
        <Link href="/dispatch" className="card warm sheet-card">
          <div className="tag">
            <span className="dash" />
            <span className="label">agent · 正在跑</span>
            <span className="sum">
              共 {String(TODAY_RUNNING_SHEETS.length + TODAY_IDLE_SHEETS.length).padStart(2, "0")} 位
            </span>
          </div>
          <h3>
            <span className="nbr">{String(TODAY_RUNNING_SHEETS.length).padStart(2, "0")}</span>
            <em>running.</em>
          </h3>
          <div className="pv-sheets">
            {TODAY_RUNNING_SHEETS.map((s) => (
              <div
                className="sheet running"
                key={s.id}
                style={{ "--p": `${s.pct}%` } as CSSProperties}
              >
                <div className="sheet-top">
                  <span className="sheet-tag">{s.tag}</span>
                  <span className="sheet-state">{s.state}</span>
                </div>
                <div className="sheet-title">{s.title}</div>
                <div className="sheet-sub">
                  <span>{s.sub}</span>
                  <span className="eta">{s.eta}</span>
                </div>
                <div className="sheet-bar" />
              </div>
            ))}
            {TODAY_IDLE_SHEETS.map((s) => (
              <div className="sheet idle" key={s.id}>
                <div className="sheet-top">
                  <span className="sheet-tag">{s.tag}</span>
                  <span className="sheet-state">idle</span>
                </div>
                <div className="sheet-title">{s.title}</div>
                <div className="sheet-sub">
                  <span>{s.sub}</span>
                  <span className="eta">—</span>
                </div>
              </div>
            ))}
          </div>
          <div className="pv-foot sheet-foot">
            <span className="cnt">
              运行中 <b>{String(TODAY_RUNNING_SHEETS.length).padStart(2, "0")}</b> · 空闲{" "}
              <b>{String(TODAY_IDLE_SHEETS.length).padStart(2, "0")}</b>
            </span>
            <span className="tail">调度台 ↘</span>
          </div>
          <div className="badge">02.</div>
        </Link>

        {/* 任务 */}
        <Link href="/warroom" className="v-card">
          <div className="v-card-tag">
            <span className="dash" />
            任务 · Warroom
            <span className="sum">{TODAY_TASKS.length} TASKS</span>
          </div>
          <div className="v-card-h">
            {TODAY_TASKS.length}
            <em>queued</em>
          </div>
          <ul>
            {TODAY_TASKS.map((t) => (
              <li key={t.id}>
                <span>
                  <span className={`prio ${t.prio}`}>{t.prio}</span>
                  {t.title}
                </span>
                <span className="ts">{t.due}</span>
              </li>
            ))}
          </ul>
        </Link>
      </div>
    </div>
  );
}
