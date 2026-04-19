import type { KCard as KCardData, KColumn } from "@/lib/mock/warroom";
import { KCard } from "./KCard";

/** .kcol 单列 · mockup L1468-1481 + L3369-3475 */
export function KanbanColumn({
  column,
  cards,
}: {
  column: KColumn;
  cards: KCardData[];
}) {
  const cls = column.done ? "kcol done" : "kcol";
  return (
    <section className={cls}>
      <div className="khd">
        <span className="t">
          {column.label} <em>· {column.count}</em>
        </span>
        <span className="n">{column.count}</span>
      </div>
      <div className="kbody">
        {cards.map((c, i) => (
          <KCard key={c.id} card={c} idx={i} />
        ))}
      </div>
    </section>
  );
}
