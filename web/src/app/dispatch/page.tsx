import { ConflictAlert } from "./_components/ConflictAlert";
import { EventBridge } from "./_components/EventBridge";
import { ImLiveBridge } from "./_components/ImLiveBridge";
import { InspectorPanel } from "./_components/InspectorPanel";
import { MessageStream } from "./_components/MessageStream";
import { ThreadList } from "./_components/ThreadList";
import "./dispatch-im.css";

export const metadata = {
  title: "对话 · 乾策 Studio",
};

export default function DispatchPage() {
  return (
    <div className="v-dispatch-im" data-testid="dispatch-view">
      {/* F11 (V4 plan · Sprint 2 spike) · A5 跨 Agent 冲突显性化 banner ·
          mock fixture · Phase C1 接 /api/conflicts 真接审贷账本 */}
      <ConflictAlert />
      <ThreadList />
      <MessageStream />
      <InspectorPanel />
      <EventBridge />
      {/* Stage D.2F · IM WebSocket + REST 真接 (上批 backend 7c2afaf 配套) */}
      <ImLiveBridge />
    </div>
  );
}
