/**
 * InkSeal — 朱砂印章。
 * shape="square" → 方印（标签用）； shape="round" → 圆印（hero 用）。
 */
export function InkSeal({
  code,
  size = "md",
  shape = "square",
  className = "",
}: {
  code: string;
  size?: "sm" | "md" | "lg";
  shape?: "square" | "round";
  className?: string;
}) {
  if (shape === "round") {
    const sizeCls = size === "sm" ? "ink-seal-round-sm" : "";
    return (
      <span
        className={`ink-seal-round ${sizeCls} ${className}`}
        aria-label={`编号 ${code}`}
      >
        {code}
      </span>
    );
  }
  const sizeCls =
    size === "sm"
      ? "text-[10px] px-1.5 py-[2px]"
      : size === "lg"
      ? "text-[15px] px-2.5 py-1"
      : "text-[12px] px-2 py-[3px]";
  return (
    <span className={`ink-seal ${sizeCls} ${className}`} aria-label={`编号 ${code}`}>
      {code}
    </span>
  );
}
