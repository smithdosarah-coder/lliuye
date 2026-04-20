"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { DESK_QUICK_CREATE, DESK_SECTIONS } from "@/lib/mock/desk";
import { useAuthStore, useCustomerStore } from "@/lib/store";
import type { Customer } from "@/lib/store/types";
import { DeskCustomerRow } from "./DeskCustomerRow";
import { DeskSearch } from "./DeskSearch";
import { useDeskStore } from "./_desk-store";

/** 根据搜索串命中 name/shortName/industry/tag */
function matches(c: Customer, q: string): boolean {
  if (!q) return true;
  const hay = [
    c.name,
    c.shortName ?? "",
    c.industry ?? "",
    c.region ?? "",
    c.tags.join(" "),
  ]
    .join(" ")
    .toLowerCase();
  return hay.includes(q.toLowerCase());
}

export function Desk() {
  const [open, setOpen] = useState(false);
  const [pinnedDrawer, setPinnedDrawer] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const moveThrottle = useRef<number>(0);
  const searchRef = useRef<HTMLInputElement | null>(null);

  const customers = useCustomerStore((s) => s.customers);
  const recents = useCustomerStore((s) => s.recents);
  const currentUserId = useAuthStore((s) => s.currentUser?.id ?? null);
  const query = useDeskStore((s) => s.query);
  const filter = useDeskStore((s) => s.filter);
  const pinnedIds = useDeskStore((s) => s.pinned);
  const setFilter = useDeskStore((s) => s.setFilter);

  // Sync pin state -> body dataset so main content can reserve space via CSS.
  useEffect(() => {
    if (typeof document === "undefined") return;
    if (pinnedDrawer) {
      document.body.dataset.deskPinned = "true";
    } else {
      delete document.body.dataset.deskPinned;
    }
    return () => {
      delete document.body.dataset.deskPinned;
    };
  }, [pinnedDrawer]);

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (pinnedDrawer) return;
      const now = performance.now();
      if (now - moveThrottle.current < 16) return;
      moveThrottle.current = now;

      if (e.clientX < 22) {
        if (closeTimer.current) clearTimeout(closeTimer.current);
        setOpen(true);
      } else if (open && e.clientX > 360) {
        if (closeTimer.current) clearTimeout(closeTimer.current);
        closeTimer.current = setTimeout(() => setOpen(false), 180);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        setPinnedDrawer(false);
        return;
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(true);
        requestAnimationFrame(() => searchRef.current?.focus());
      }
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("keydown", onKey);
      if (closeTimer.current) clearTimeout(closeTimer.current);
    };
  }, [open, pinnedDrawer]);

  function toggleDrawerPin() {
    setPinnedDrawer((p) => !p);
    setOpen(true);
  }

  /**
   * 分组规则（按优先级）：
   *   1. 置顶  = 用户 pin 过的；若为空，退化为 recents 前 3
   *   2. 我负责 = assignedTo === currentUser.id
   *   3. 协同  = sharedWith.includes(currentUser.id)
   *   4. 全部  = 不属于上述分组的其余客户
   * 一个客户只出现在最高优先级的分组里，避免重复。
   * filter tab 选中 owned/shared 时只展示对应分组；all 时展示全部。
   */
  const groups = useMemo(() => {
    const kept = customers.filter((c) => matches(c, query));
    const byId = new Map(kept.map((c) => [c.id, c]));
    const claimed = new Set<string>();

    let pinnedList: Customer[] = pinnedIds
      .map((id) => byId.get(id))
      .filter((c): c is Customer => Boolean(c));
    if (pinnedList.length === 0) {
      // 退化：recents 前 3 替代空 pinned 组，仅当没主动 pin 时显示
      pinnedList = recents
        .slice(0, 3)
        .map((id) => byId.get(id))
        .filter((c): c is Customer => Boolean(c));
    }
    pinnedList.forEach((c) => claimed.add(c.id));

    const owned = kept.filter(
      (c) => !claimed.has(c.id) && c.assignedTo === currentUserId,
    );
    owned.forEach((c) => claimed.add(c.id));

    const shared = kept.filter(
      (c) =>
        !claimed.has(c.id) &&
        currentUserId !== null &&
        c.sharedWith.includes(currentUserId),
    );
    shared.forEach((c) => claimed.add(c.id));

    const rest = kept.filter((c) => !claimed.has(c.id));

    return { pinned: pinnedList, owned, shared, rest };
  }, [customers, pinnedIds, recents, currentUserId, query]);

  const visibleGroups: Array<{ key: string; title: string; meta: string; rows: Customer[] }> = [];
  if (groups.pinned.length > 0 && (filter === "all")) {
    visibleGroups.push({
      key: "pinned",
      title: "置顶",
      meta: pinnedIds.length > 0 ? `PINNED · ${String(groups.pinned.length).padStart(2, "0")}` : "RECENT · TOP 3",
      rows: groups.pinned,
    });
  }
  if (filter === "all" || filter === "owned") {
    if (groups.owned.length > 0) {
      visibleGroups.push({
        key: "owned",
        title: "我负责的",
        meta: `MINE · ${String(groups.owned.length).padStart(2, "0")}`,
        rows: groups.owned,
      });
    }
  }
  if (filter === "all" || filter === "shared") {
    if (groups.shared.length > 0) {
      visibleGroups.push({
        key: "shared",
        title: "协同",
        meta: `SHARED · ${String(groups.shared.length).padStart(2, "0")}`,
        rows: groups.shared,
      });
    }
  }
  if (filter === "all" && groups.rest.length > 0) {
    visibleGroups.push({
      key: "rest",
      title: "全部",
      meta: `ALL · ${String(groups.rest.length).padStart(2, "0")}`,
      rows: groups.rest,
    });
  }

  const totalVisible =
    groups.pinned.length +
    groups.owned.length +
    groups.shared.length +
    (filter === "all" ? groups.rest.length : 0);

  const cls = ["drawer", open ? "open" : "", pinnedDrawer ? "pin" : ""]
    .filter(Boolean)
    .join(" ");

  // 其余静态 section 保留（进行中 / 最近），客户部分走动态
  const staticSections = DESK_SECTIONS.filter((s) => s.title !== "我的客户");

  return (
    <aside className={cls} aria-label="工作台 Desk">
      <div className="dr-hint" />
      <div className="dr-panel" role="region">
        <div className="dr-head">
          <span className="t">
            <span className="cn">工作台</span>
            <em>Desk.</em>
          </span>
          <button
            className="dr-pin"
            onClick={toggleDrawerPin}
            title={pinnedDrawer ? "解钉" : "钉住"}
            aria-pressed={pinnedDrawer}
          >
            ◆
          </button>
        </div>

        <DeskSearch ref={searchRef} />

        <div className="dr-sec dr-customers">
          <div className="hd">
            <span>我的客户</span>
            <em>BOOK · {String(totalVisible).padStart(2, "0")}</em>
          </div>

          <div className="dr-filter" role="tablist" aria-label="客户分组过滤">
            <button
              type="button"
              role="tab"
              aria-selected={filter === "all"}
              data-active={filter === "all" || undefined}
              onClick={() => setFilter("all")}
            >
              全部
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={filter === "owned"}
              data-active={filter === "owned" || undefined}
              onClick={() => setFilter("owned")}
            >
              我负责
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={filter === "shared"}
              data-active={filter === "shared" || undefined}
              onClick={() => setFilter("shared")}
            >
              协同
            </button>
          </div>

          {visibleGroups.length === 0 ? (
            <div className="dr-empty">
              {query ? `无「${query}」相关客户` : "暂无客户"}
            </div>
          ) : (
            visibleGroups.map((g) => (
              <div className="dr-subsec" key={g.key}>
                <div className="hd-sub">
                  <span>{g.title}</span>
                  <em>{g.meta}</em>
                </div>
                {g.rows.map((c) => (
                  <DeskCustomerRow key={c.id} customer={c} />
                ))}
              </div>
            ))
          )}
        </div>

        {staticSections.map((sec) => (
          <div className="dr-sec" key={sec.title}>
            <div className="hd">
              <span>{sec.title}</span>
              <em>{sec.meta}</em>
            </div>
            {sec.rows.map((r) => (
              <Link
                key={`${sec.title}-${r.nm}`}
                href={r.href}
                className="dr-row"
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.effectAllowed = "copy";
                  e.dataTransfer.setData(
                    "application/x-desk-row",
                    JSON.stringify({ name: r.nm, href: r.href }),
                  );
                  e.dataTransfer.setData("text/plain", r.nm);
                }}
              >
                <span className={`ic${r.icClass ? ` ${r.icClass}` : ""}`}>
                  {r.ic}
                </span>
                <span className="nm-wrap">
                  <span className="nm">{r.nm}</span>
                  <span className="sub">{r.sub}</span>
                </span>
                <span className="ts">{r.ts}</span>
              </Link>
            ))}
            {sec.more && (
              <span className="dr-more">
                {sec.more.label}{" "}
                {sec.more.count && <span className="a">{sec.more.count}</span>}{" "}
                <span className="a">↘</span>
              </span>
            )}
          </div>
        ))}

        <div className="dr-sec">
          <div className="hd">
            <span>新建</span>
            <em>CREATE</em>
          </div>
          <div className="dr-qc">
            {DESK_QUICK_CREATE.map((q) => (
              <Link key={q.label} href={q.href}>
                <button type="button">
                  <span className="plus">+</span>
                  {q.label}
                </button>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
