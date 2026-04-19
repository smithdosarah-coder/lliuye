import type { MemoBlock } from "@/lib/mock/dispatch";
import { Segs } from "./Segs";

/** .memo callout · mockup L3219-3243 */
export function MemoCallout({ memo }: { memo: MemoBlock }) {
  return (
    <div className="memo">
      <div className="mhd">
        <span className="t">
          {memo.title} · <em>{memo.titleEm}</em>
        </span>
        <span className="rt">{memo.rt}</span>
      </div>
      <ol>
        {memo.items.map((it, i) => (
          <li key={i}>
            <div className="h">{it.h}</div>
            <div className="s">
              <Segs segs={it.s} />
            </div>
          </li>
        ))}
      </ol>
      <div className="mft">
        {memo.chips.map((c, i) => (
          <button key={i} type="button" className={`chip${c.ghost ? " ghost" : ""}`}>
            {c.label}
          </button>
        ))}
      </div>
    </div>
  );
}
