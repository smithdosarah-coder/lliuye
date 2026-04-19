import { Fragment, type CSSProperties } from "react";
import type { KCard as KCardData, MetaSeg } from "@/lib/mock/warroom";

/** .kcard 单卡 · mockup L1482-1504 + L3372-3473 · case-in 逐卡 stagger 由 --i 驱动 */
export function KCard({ card, idx }: { card: KCardData; idx: number }) {
  return (
    <article
      className="kcard"
      style={{ "--i": idx } as CSSProperties}
    >
      <div className="hd">
        <span className="t">{card.title}</span>
        <span className={`pr ${card.pill.variant}`}>{card.pill.label}</span>
      </div>
      <div className="meta">
        {card.meta.map((seg, i) => (
          <Fragment key={i}>
            {i > 0 ? " · " : null}
            {typeof seg === "string" ? seg : <span className="cn">{seg.cn}</span>}
          </Fragment>
        ))}
      </div>
      <div className="body">
        {card.body.map((s, i) =>
          s.em ? <em key={i}>{s.text}</em> : <Fragment key={i}>{s.text}</Fragment>,
        )}
      </div>
      <div className="ft">
        <span className="who">
          <span className="av">{card.who.av}</span>
          {card.who.name}
        </span>
        <span className="go">
          {card.go} <span>↘</span>
        </span>
      </div>
    </article>
  );
}
