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
      <ThreadList />
      <MessageStream />
      <InspectorPanel />
      <EventBridge />
      {/* Stage D.2F · IM WebSocket + REST 真接 (上批 backend 7c2afaf 配套) */}
      <ImLiveBridge />
    </div>
  );
}
