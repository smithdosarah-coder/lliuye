export function EmptyColumn({ hint }: { hint?: string }) {
  return (
    <div className="kempty">
      <span className="dot" aria-hidden="true" />
      <span>{hint ?? "暂无 ticket"}</span>
    </div>
  );
}
