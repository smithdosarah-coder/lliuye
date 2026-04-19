import type { Msg, Thread } from "@/lib/mock/dispatch";
import { MemoCallout } from "./MemoCallout";
import { Segs } from "./Segs";

/** dp-col.dp-main 中栏 · mockup L3199-3251 */
export function MessageThread({ thread, messages }: { thread: Thread; messages: Msg[] }) {
  return (
    <div className="dp-col dp-main">
      <div className="hd">
        <span className="t">
          <span className="cn">{thread.activeTitleCn}</span> <em>{thread.activeTitleEm}</em>
        </span>
        <span className="n">{thread.activeCount}</span>
      </div>
      <div className="thread">
        {messages.map((m) => (
          <div key={m.id} className={m.me ? "msg me" : "msg"}>
            <div className="ln">
              {m.who}
              {m.whoEm ? (
                <>
                  {" · "}
                  <em>{m.whoEm}</em>
                </>
              ) : null}
              {" · "}
              <span className="tm">{m.time}</span>
            </div>
            <div className="bd">
              <Segs segs={m.body} />
            </div>
            {m.memo ? <MemoCallout memo={m.memo} /> : null}
          </div>
        ))}
      </div>
      <div className="composer">
        <input placeholder="写一则 note …  ⌘K 召唤 Agent · ⌘⇧E 附证据" />
        <button type="button" className="send">
          发送 <span style={{ opacity: 0.6 }}>↘</span>
        </button>
      </div>
    </div>
  );
}
