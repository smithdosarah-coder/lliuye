"use client";

/**
 * EvidenceTrail — 6 Agent archive workspace 底部挂的统一证据链区块。
 *
 * 渲染:
 *   - 按 source 分组,折叠默认收起(首组展开)
 *   - 低置信度条(confidence < 0.5)加 .is-low-confidence 灰斜
 *   - 点击条目弹 EvidencePopover
 *   - items 为空 → 空态"暂无证据"
 *
 * 数据源优先级(见 EvidenceContext):
 *   1. window.__EVIDENCE_TEST__(测试注入)
 *   2. props.items(workspace 直传)
 *   3. EvidenceProvider 上游 context
 */

import { useEffect, useMemo, useState, useCallback } from "react";
import type { EvidenceItem } from "./types";
import { isLowConfidence } from "./types";
import { useEvidence } from "./EvidenceContext";
import { EvidencePopover } from "./EvidencePopover";
import "./evidence.css";

export interface EvidenceTrailProps {
  /** 显式传入 items;省略则从 EvidenceProvider 上游读取 */
  items?: EvidenceItem[];
  /** 点击某条证据的回调(popover 打开前触发,可用于上报埋点) */
  onSourceClick?(item: EvidenceItem): void;
  /** 区块标题,默认"证据链" */
  title?: string;
  /** Agent 功能色 key,供 CSS 变量 --t-<agent> 染色 */
  agentTone?: "channel" | "credit" | "alert" | "compliance" | "report" | "riskctrl";
}

interface GroupedSource {
  source: string;
  items: EvidenceItem[];
}

function groupBySource(items: EvidenceItem[]): GroupedSource[] {
  const map = new Map<string, EvidenceItem[]>();
  for (const it of items) {
    const bucket = map.get(it.source);
    if (bucket) bucket.push(it);
    else map.set(it.source, [it]);
  }
  return Array.from(map.entries()).map(([source, arr]) => ({ source, items: arr }));
}

export function EvidenceTrail({
  items,
  onSourceClick,
  title = "证据链",
  agentTone,
}: EvidenceTrailProps) {
  const ctx = useEvidence();
  const resolved = items ?? ctx.items;

  const groups = useMemo(() => groupBySource(resolved), [resolved]);
  const firstSource = groups[0]?.source;
  const [openGroups, setOpenGroups] = useState<Set<string>>(
    () => new Set(firstSource ? [firstSource] : [])
  );
  useEffect(() => {
    // 当 items 变化(如 test 注入或真实 SSE 更新)导致首组 source 变化时
    // 重置展开态 — 只展开新的首组,避免 openGroups 指向已消失的旧 source。
    setOpenGroups((prev) => {
      if (firstSource && prev.has(firstSource)) return prev;
      return new Set(firstSource ? [firstSource] : []);
    });
  }, [firstSource]);
  const [activePopover, setActivePopover] = useState<string | null>(null);
  useEffect(() => {
    // items 变化清空 popover 选中,避免指向已消失的 ref_id。
    setActivePopover(null);
  }, [resolved]);

  const toggleGroup = useCallback((source: string) => {
    setOpenGroups((prev) => {
      const next = new Set(prev);
      if (next.has(source)) next.delete(source);
      else next.add(source);
      return next;
    });
  }, []);

  const handleItemClick = useCallback(
    (item: EvidenceItem) => {
      onSourceClick?.(item);
      setActivePopover((curr) => (curr === item.ref_id ? null : item.ref_id));
    },
    [onSourceClick]
  );

  const closePopover = useCallback(() => setActivePopover(null), []);

  if (resolved.length === 0) {
    return (
      <section
        className="ev-trail ev-trail--empty"
        data-agent-tone={agentTone}
        aria-label={title}
      >
        <header className="ev-trail-head">
          <h3 className="ev-trail-title">{title}</h3>
          <span className="ev-trail-count">0 条</span>
        </header>
        <p className="ev-trail-empty-msg">暂无证据</p>
      </section>
    );
  }

  return (
    <section
      className="ev-trail"
      data-agent-tone={agentTone}
      aria-label={title}
    >
      <header className="ev-trail-head">
        <h3 className="ev-trail-title">{title}</h3>
        <span className="ev-trail-count">
          {resolved.length} 条 · {groups.length} 源
        </span>
      </header>
      <ul className="ev-trail-groups">
        {groups.map((g) => {
          const open = openGroups.has(g.source);
          return (
            <li
              key={g.source}
              className="ev-trail-group"
              data-open={open ? "true" : "false"}
            >
              <button
                type="button"
                className="ev-trail-group-head"
                aria-expanded={open}
                onClick={() => toggleGroup(g.source)}
              >
                <span className="ev-trail-group-caret" aria-hidden>
                  {open ? "▾" : "▸"}
                </span>
                <span className="ev-trail-group-source" title={g.source}>
                  {g.source}
                </span>
                <span className="ev-trail-group-badge">{g.items.length}</span>
              </button>
              {open && (
                <ul className="ev-trail-items">
                  {g.items.map((it) => {
                    const low = isLowConfidence(it);
                    const active = activePopover === it.ref_id;
                    return (
                      <li
                        key={it.ref_id}
                        className={`ev-trail-item${low ? " is-low-confidence" : ""}`}
                        data-active={active ? "true" : "false"}
                      >
                        <button
                          type="button"
                          className="ev-trail-item-btn"
                          onClick={() => handleItemClick(it)}
                          aria-haspopup="dialog"
                          aria-expanded={active}
                          title={low ? "置信度偏低" : undefined}
                        >
                          <span className="ev-trail-item-snippet">{it.snippet}</span>
                          <span className="ev-trail-item-confnum">
                            {Math.round(it.confidence * 100)}%
                          </span>
                        </button>
                        {active && (
                          <EvidencePopover
                            item={it}
                            open={active}
                            onClose={closePopover}
                          />
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
