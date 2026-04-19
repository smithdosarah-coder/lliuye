import { KanbanColumn } from "@/components/warroom/KanbanColumn";
import { WARROOM_CARDS, WARROOM_COLUMNS, WARROOM_LEDE_COUNT } from "@/lib/mock/warroom";

export const metadata = {
  title: "任务 · 乾策 Studio",
};

/**
 * Warroom view · mockup L3354-3478 (Task K2 裁回 mockup 字面)
 * - eyebrow "WAR ROOM · 第 17 周" + em "本周你有 12 项在飞"
 * - h1 "正在 flight." + lede 开头 num="12"
 * - kanban 4 col: 待处理·04 / 进行中·05 / 冒出·02 / 已归档·03 (done 深色)
 * - 14 card + 6 pill variant (P0/P1/P2/urg/wait/cn)
 * - eyebrow/lede 数字走 mockup 字面 "12", kanban 内实际 14 卡 (mockup 自身
 *   数字不一致, R-0 mockup 优先 · 按 mockup 字面原样镜像)
 */
export default function WarroomPage() {
  return (
    <div className="v-warroom">
      <div className="eyebrow">
        <span>WAR ROOM · 第 17 周</span>
        <span className="sep" />
        <em>本周你有 {WARROOM_LEDE_COUNT} 项在飞。</em>
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
        <span className="num">{WARROOM_LEDE_COUNT}</span> 条任务分派到你与三位 AI 助手的桌上。拖卡片换列，或在对话里召唤 <em>Bench</em> 重排。
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
