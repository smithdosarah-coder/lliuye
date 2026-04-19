"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import {
  DISPATCH_CASEFILES,
  DISPATCH_MESSAGES,
  DISPATCH_THREADS,
} from "@/lib/mock/dispatch";
import { CaseSidebar } from "./CaseSidebar";
import { ChannelList } from "./ChannelList";
import { MessageThread } from "./MessageThread";

/**
 * Dispatch view client shell · mockup L3145-3268
 * - 承接 .view[data-view="dispatch"] 的 eyebrow + h1 + .dispatch 3 列
 * - h1 双 word (写一则 / note.) 按字拆 .glyph 重放 stagger (同 Today Hero 套路)
 * - activeThreadId useState 控制中栏/右栏切换
 */

const HERO_WORDS = [
  { text: "写一则", cjk: true },
  { text: "note.", italic: true },
];
const STAGGER_BASE = 0.8;
const STAGGER_STEP = 0.045;

export function DispatchShell() {
  const h1Ref = useRef<HTMLHeadingElement | null>(null);
  const [activeId, setActiveId] = useState<string>(DISPATCH_THREADS[0].id);

  useEffect(() => {
    const glyphs = h1Ref.current?.querySelectorAll<HTMLSpanElement>(".glyph");
    if (!glyphs) return;
    glyphs.forEach((g, i) => {
      g.style.animation = "none";
      void g.offsetWidth;
      g.style.animation = "";
      g.style.animationDelay = `${STAGGER_BASE + i * STAGGER_STEP}s`;
    });
  }, []);

  const activeThread =
    DISPATCH_THREADS.find((t) => t.id === activeId) ?? DISPATCH_THREADS[0];
  const activeMessages = DISPATCH_MESSAGES[activeId] ?? [];
  const activeCase =
    DISPATCH_CASEFILES[activeId] ?? DISPATCH_CASEFILES[DISPATCH_THREADS[0].id];

  let glyphIdx = 0;

  return (
    <>
      <div className="eyebrow">
        <span>DISPATCH · 频道 02</span>
        <span className="sep" />
        <em>来，和团队说几句。</em>
      </div>
      <h1 ref={h1Ref} className="hero-h1" id="h1Dispatch">
        {HERO_WORDS.map((w, wi) => {
          const chars = [...w.text];
          return (
            <span
              key={wi}
              className="word"
              data-w={w.text}
              data-cjk={w.cjk ? "1" : undefined}
            >
              {w.italic ? (
                <em>
                  {chars.map((ch) => {
                    const i = glyphIdx++;
                    return (
                      <span
                        key={`${wi}-${i}`}
                        className="glyph"
                        style={
                          {
                            animationDelay: `${STAGGER_BASE + i * STAGGER_STEP}s`,
                            "--i": i,
                          } as CSSProperties
                        }
                      >
                        {ch}
                      </span>
                    );
                  })}
                </em>
              ) : (
                chars.map((ch) => {
                  const i = glyphIdx++;
                  return (
                    <span
                      key={`${wi}-${i}`}
                      className={w.cjk ? "glyph cn" : "glyph"}
                      style={
                        {
                          animationDelay: `${STAGGER_BASE + i * STAGGER_STEP}s`,
                          "--i": i,
                        } as CSSProperties
                      }
                    >
                      {ch}
                    </span>
                  );
                })
              )}
            </span>
          );
        })}
      </h1>

      <div className="dispatch">
        <ChannelList
          threads={DISPATCH_THREADS}
          activeId={activeId}
          onSelect={setActiveId}
        />
        <MessageThread thread={activeThread} messages={activeMessages} />
        <CaseSidebar caseFile={activeCase} />
      </div>
    </>
  );
}
