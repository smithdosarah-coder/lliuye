import { KanbanColumn } from "@/components/warroom/KanbanColumn";
import { WARROOM_CARDS, WARROOM_COLUMNS } from "@/lib/mock/warroom";

export const metadata = {
  title: "任务 · 乾策 Studio",
};

/**
 * Warroom view · mockup L3353-3478
 * - eyebrow (WAR ROOM · 第 17 周) + h1 (正在 flight.) + lede
 * - .kanban 4-col grid (待处理/进行中/冒出/已归档), last col .kcol.done 深色
 * - 50+ .kcard 总数, 7 priority-pill + 3 mockup status 变体
 * - kcol rise 逐列 stagger (mockup) + kcard case-in 逐卡 stagger (onboarding 追加)
 */
export default function WarroomPage() {
  const total = WARROOM_CARDS.length;
  return (
    <div className="v-warroom">
      <div className="eyebrow">
        <span>WAR ROOM · 第 17 周</span>
        <span className="sep" />
        <em>本周你有 {total} 项在飞。</em>
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
        <span className="num">{total}</span> 条任务分派到你与三位 AI 助手的桌上。拖卡片换列，或在对话里召唤 <em>Bench</em> 重排。
      </p>

      <div className="kanban">
        {WARROOM_COLUMNS.map((col) => {
          const cards = WARROOM_CARDS.filter((c) => c.column === col.key);
          return <KanbanColumn key={col.key} column={col} cards={cards} />;
        })}
      </div>
    </div>
  );
}
