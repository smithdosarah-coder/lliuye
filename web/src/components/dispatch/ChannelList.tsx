"use client";

import type { Thread } from "@/lib/mock/dispatch";
import { Segs } from "./Segs";

/** dp-col 左栏 · mockup L3160-3197 */
export function ChannelList({
  threads,
  activeId,
  onSelect,
}: {
  threads: Thread[];
  activeId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="dp-col">
      <div className="hd">
        <span className="t">
          <span className="cn">频道</span> <em>· {String(threads.length).padStart(2, "0")}</em>
        </span>
        <span className="n">{String(threads.length).padStart(2, "0")}</span>
      </div>
      <div className="ch-list">
        {threads.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`ch${t.id === activeId ? " on" : ""}`}
            onClick={() => onSelect(t.id)}
          >
            <span className="nm">{t.name}</span>
            <span className="meta">{t.meta}</span>
            <span className="last">
              <Segs segs={t.last} />
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
