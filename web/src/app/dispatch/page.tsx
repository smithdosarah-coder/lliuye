import { DispatchShell } from "@/components/dispatch/DispatchShell";

export const metadata = {
  title: "对话 · 乾策 Studio",
};

export default function DispatchPage() {
  return (
    <div className="v-dispatch">
      <DispatchShell />
    </div>
  );
}
