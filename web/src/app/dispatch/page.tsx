import { DISPATCH_CHANNELS, DISPATCH_MESSAGES } from "@/lib/mock/dispatch";

export const metadata = {
  title: "对话 · 乾策 Studio",
};

export default function DispatchPage({
  searchParams,
}: {
  searchParams?: Promise<{ channel?: string }>;
}) {
  // Stage 2 stub: 不读 query，固定展示首个 channel 的 messages 或 empty state
  void searchParams;
  const active = DISPATCH_CHANNELS[0];
  const messages = DISPATCH_MESSAGES[active.id] || [];

  return (
    <div className="v-dispatch">
      <aside className="dp-panel" aria-label="频道列表">
        <div className="hd">
          <span className="t">频道 · Channels</span>
          <span className="meta">{DISPATCH_CHANNELS.length} CH</span>
        </div>
        <div className="dp-list">
          {DISPATCH_CHANNELS.map((c) => (
            <div key={c.id} className="dp-row">
              <div>
                <div className="nm">{c.name}</div>
                <div className="preview">{c.preview}</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
                <span className="ts">{c.ts}</span>
                {c.unread > 0 && <span className="unread">{c.unread}</span>}
              </div>
            </div>
          ))}
        </div>
      </aside>

      <section className="dp-panel" aria-label="消息流">
        <div className="hd">
          <span className="t">{active.name}</span>
          <span className="meta">STAGE 2 · MOCK</span>
        </div>
        <div className="dp-stream">
          {messages.length === 0 ? (
            <div className="dp-empty">
              本频道暂无消息
              <div className="sub">Stage 4 will wire real-time messaging</div>
            </div>
          ) : (
            messages.map((m) => (
              <div key={m.id} className="dp-msg">
                <span className="who">{m.who}</span>
                <span className="ts">{m.ts}</span>
                <div className="body">{m.body}</div>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
