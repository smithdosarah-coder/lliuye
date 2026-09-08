"use client";

import { Fragment, useEffect, useState } from "react";
import { TODAY_BELT, TODAY_BELT_RULE } from "@/lib/mock/today";

/**
 * 今日账册 · mockup L3114-3141
 * - .rule: 左中右 三段 grid ("今日账册" / 横线 / timestamp)
 * - .belt: 4 col grid, 每栏 k / v(digits+unit) / note
 */
export function AccountBelt() {
  const [ledgerTime, setLedgerTime] = useState("—");
  useEffect(() => {
    const render = () => {
      const parts = new Intl.DateTimeFormat("zh-CN", {
        timeZone: "Asia/Shanghai",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).formatToParts(new Date());
      const value = (type: Intl.DateTimeFormatPartTypes) =>
        parts.find((part) => part.type === type)?.value ?? "--";
      setLedgerTime(`${value("year")} · ${value("month")} · ${value("day")} · ${value("hour")}:${value("minute")}`);
    };
    render();
    const timer = window.setInterval(render, 60_000);
    return () => window.clearInterval(timer);
  }, []);
  return (
    <>
      <div className="rule">
        <span className="lbl">{TODAY_BELT_RULE.lbl}</span>
        <span className="ln" />
        <span className="rt">{ledgerTime}</span>
      </div>

      <div className="belt">
        {TODAY_BELT.map((col) => (
          <div className="col" key={col.id}>
            <div className="k">{col.k}</div>
            <div className="v">
              {col.v.currency ? "¥" : null}
              <span className="dg">{col.v.digits}</span>
              <sub>{col.v.unit}</sub>
            </div>
            <div className="note">
              {col.note.map((seg, i) => (
                <Fragment key={i}>
                  {seg.em ? (
                    <em>{seg.text}</em>
                  ) : seg.strong ? (
                    <strong>{seg.text}</strong>
                  ) : (
                    seg.text
                  )}
                </Fragment>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
