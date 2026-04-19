/**
 * Today BoardCard · mockup L3040-3111 1:1
 * - .card.deep.board-card (深色渐变 --g1 78% → --g4 84% → --g6 90%, chalk 文字)
 * - .pv-board 滚动 + mask-image 底部 fade
 * - .note 钉纸条样: 每 note 按 nth-child 轻微旋转 -1.4° ~ 1.6° 带胶带伪元素
 * - 4 变体: p0 (桃红) / p1 (奶黄) / p2 (抹茶) / done (褪白 + 标题删除线)
 * - pure server component (静态 mock, 无 client state)
 */

import Link from "next/link";
import { TODAY_BOARD_NOTES } from "@/lib/mock/today";

export function BoardCard() {
  const openCount = TODAY_BOARD_NOTES.filter((n) => n.variant !== "done").length;
  const urgentCount = TODAY_BOARD_NOTES.filter((n) => n.variant === "p0").length;
  const pad2 = (n: number) => String(n).padStart(2, "0");

  return (
    <article className="card deep board-card" data-go="warroom">
      <div className="tag">
        <span className="dash" />
        <span className="label">任务 · 我的桌上</span>
        <span className="sum">加急 {pad2(urgentCount)}</span>
      </div>
      <h3>
        <span className="nbr">{pad2(openCount)}</span>
        <em>open.</em>
      </h3>
      <div className="pv-board">
        {TODAY_BOARD_NOTES.map((n) => (
          <div key={n.id} className={`note ${n.variant}`}>
            <div className="note-top">
              <span className="note-pri">{n.pri}</span>
              <span className="note-due">{n.due}</span>
            </div>
            <div className="note-title">{n.title}</div>
            <div className="note-src">{n.src}</div>
          </div>
        ))}
      </div>
      <div className="pv-foot board-foot">
        <span className="cnt">
          本周 <b>{pad2(openCount)}</b> 项 · 已完成 <b>23</b>
        </span>
        <Link href="/warroom" className="tail">
          看板 ↘
        </Link>
      </div>
      <div className="badge">03.</div>
    </article>
  );
}
