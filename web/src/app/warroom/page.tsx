import { WARROOM_COLUMNS, WARROOM_TASKS } from "@/lib/mock/warroom";

export const metadata = {
  title: "任务 · 乾策 Studio",
};

export default function WarroomPage() {
  return (
    <div>
      <div className="archive-h" style={{ fontSize: 36, marginBottom: 18 }}>
        任务 <em style={{ fontFamily: "var(--italic)", fontStyle: "italic", color: "var(--accent)" }}>warroom</em>
      </div>
      <div className="v-warroom">
        {WARROOM_COLUMNS.map((col) => {
          const tasks = WARROOM_TASKS.filter((t) => t.column === col.key);
          return (
            <section key={col.key} className="wr-col">
              <div className="hd">
                <span className="t">
                  <span className="cn">{col.label}</span>
                </span>
                <span className="meta">{col.meta} · {tasks.length}</span>
              </div>
              {tasks.map((t) => (
                <article key={t.id} className="wr-card">
                  <div className="title">{t.title}</div>
                  <div className="meta">
                    <span className={`prio ${t.prio}`}>{t.prio}</span>
                    <span className="who">{t.who}</span>
                    <span style={{ marginLeft: "auto" }}>{t.due}</span>
                  </div>
                </article>
              ))}
              {tasks.length === 0 && (
                <div style={{
                  margin: "auto", textAlign: "center",
                  fontFamily: "var(--cjk)", color: "var(--ink-48)", fontSize: 12,
                }}>
                  暂无任务
                </div>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
