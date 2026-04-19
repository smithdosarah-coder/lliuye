import { Fragment } from "react";
import type { TextSeg } from "@/lib/mock/dispatch";

/**
 * 把 TextSeg[] 渲染成交替 plain / <em> 斜体片段
 * mockup 全局约定: <em> 字面走 --italic font (Instrument Serif)
 */
export function Segs({ segs }: { segs: TextSeg[] }) {
  return (
    <>
      {segs.map((s, i) =>
        s.em ? <em key={i}>{s.text}</em> : <Fragment key={i}>{s.text}</Fragment>,
      )}
    </>
  );
}
