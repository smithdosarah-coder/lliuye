/**
 * Today FeedCard · mockup L2815-2950 1:1
 * - .card.feed-card 外壳,tag + h3 nbr/em + pv-feed 滚动列表 + feed-foot
 * - feed-item 三态: urgent.unread (红边+accent dot halo) / unread (accent dot) / 普通
 * - feed-av 变体: 默认(chalk gradient) / sys (深色) / warn (accent)
 * - 底部 mask-image fade 在 views.css .card.feed-card .pv-feed 里, 本组件只管 DOM
 * - pure server component (静态 mock 数据, 无 client state)
 */

import Link from "next/link";
import { TODAY_FEED } from "@/lib/mock/today";

function clsFeedItem(urgent?: boolean, unread?: boolean): string {
  const parts = ["feed-item"];
  if (urgent) parts.push("urgent");
  if (unread) parts.push("unread");
  return parts.join(" ");
}

function clsFeedAv(variant?: "sys" | "warn"): string {
  return variant ? `feed-av ${variant}` : "feed-av";
}

export function FeedCard() {
  const unreadCount = TODAY_FEED.filter((f) => f.unread).length;
  const urgentCount = TODAY_FEED.filter((f) => f.urgent).length;
  const pad2 = (n: number) => String(n).padStart(2, "0");

  return (
    <article className="card feed-card" data-go="dispatch">
      <div className="tag">
        <span className="dash" />
        <span className="label">消息 · 最要紧</span>
        <span className="sum">未读 {pad2(unreadCount)}</span>
      </div>
      <h3>
        <span className="nbr">{pad2(TODAY_FEED.length)}</span>
        <em>pinged.</em>
      </h3>
      <div className="pv-feed">
        {TODAY_FEED.map((f) => (
          <div key={f.id} className={clsFeedItem(f.urgent, f.unread)}>
            <div className={clsFeedAv(f.avVariant)}>{f.av}</div>
            <div className="feed-bd">
              <div className="feed-who">
                {f.who} <span className="org">· {f.org}</span>
              </div>
              <div className="feed-msg">{f.msg}</div>
            </div>
            <div className="feed-meta">
              <span className="feed-time">{f.time}</span>
              <span className="feed-dot" />
            </div>
          </div>
        ))}
      </div>
      <div className="pv-foot feed-foot">
        <span className="cnt">
          加急 <b>{pad2(urgentCount)}</b> · 未读 <b>{pad2(unreadCount)}</b>
        </span>
        <Link href="/dispatch" className="tail">
          进入消息 ↘
        </Link>
      </div>
      <div className="badge">01.</div>
    </article>
  );
}
