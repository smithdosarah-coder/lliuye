import { RbacTileGate } from "@/components/archive/RbacTileGate";
import { ARCHIVE_TILES } from "@/lib/mock/archive";

export const metadata = {
  title: "AI 助手 · 乾策 Studio",
};

/**
 * Archive view · mockup L3270-3351
 * - eyebrow + h1 (你的 agents.) + lede + .archive 3×2 grid
 * - 6 AgentTile, 每 tile <Link> 到 /archive/<key> 既有 workspace
 * - hover card-rise 动画由 views.css .archive .agent nth-child stagger 驱动
 */
export default function ArchivePage() {
  return (
    <div className="v-archive">
      <div className="eyebrow">
        <span>ARCHIVE · 频道 03</span>
        <span className="sep" />
        <em>6 位助手听你调遣。</em>
      </div>
      <h1 className="hero-h1" id="h1Archive">
        <span className="word" data-w="你的" data-cjk="1">
          你的
        </span>{" "}
        <span className="word" data-w="agents">
          <em>agents.</em>
        </span>
      </h1>
      <p className="lede">
        每一位助手是一间独立工作区，有自己的数据、提示词和历史。点击进入，继续之前的工作。
      </p>

      <div className="archive">
        {ARCHIVE_TILES.map((t) => (
          <RbacTileGate key={t.key} tile={t} />
        ))}
      </div>
    </div>
  );
}
