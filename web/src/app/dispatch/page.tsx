import { EventBridge } from "./_components/EventBridge";
import { InspectorPanel } from "./_components/InspectorPanel";
import { MessageStream } from "./_components/MessageStream";
import { ThreadList } from "./_components/ThreadList";
import "./dispatch-im.css";

export const metadata = {
  title: "对话 · 乾策 Studio",
};

export default function DispatchPage() {
  return (
    <div className="v-dispatch-im">
      <ThreadList />
      <MessageStream />
      <InspectorPanel />
      <EventBridge />
    </div>
  );
}
