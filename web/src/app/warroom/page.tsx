import { KanbanBoard } from "./_components/KanbanBoard";

export const metadata = {
  title: "任务 · 乾策 Studio",
};

/**
 * Warroom view · Platform Phase 1 Batch 1
 * 外壳（eyebrow / hero / lede）沿用 mockup L3354-3478；kanban 本体换成
 * 接 ticket-store 的 @dnd-kit 可拖拽 4 列 + TicketDrawer。
 * 数量走 tickets.length，不再硬编 mockup 字面 "12"。
 */
export default function WarroomPage() {
  return (
    <div className="v-warroom">
      <div className="eyebrow">
        <span>WAR ROOM · 实时任务流</span>
        <span className="sep" />
        <em>跨 Agent 交接 kanban · 拖卡片换列</em>
      </div>
      <h1 className="hero-h1" id="h1Warroom">
        <span className="word" data-w="正在" data-cjk="1">
          正在
        </span>{" "}
        <span className="word" data-w="flight">
          <em>flight.</em>
        </span>
      </h1>
      <p className="lede">
        从各 Agent 汇入的 <em>HandoffTicket</em>，按状态流转到 4 列 kanban。拖卡片更新状态，或点开 ticket 查看证据链。
      </p>
      <KanbanBoard />
    </div>
  );
}
