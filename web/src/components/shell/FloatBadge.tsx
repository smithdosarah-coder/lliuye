/**
 * FloatBadge · 5 主题符号浮标
 * Source: design_mockups/rm-assistant-final-2026-04-19.html L3483-3558
 *
 * 所有 5 个 SVG 全部渲染,由 CSS selector `body[data-theme="..."] .fb-sym--...`
 * 控制单一显隐。主题切换即时生效,无需 JS 干预。
 * Ink 主题 CSS 额外覆盖 circle 为方形 (mockup L1054-1055)。
 */
export function FloatBadge() {
  return (
    <div className="float-badge" aria-hidden="true">
      <div className="mini">
        <div>今日</div>
        <div>
          <em>channel · one</em>
        </div>
      </div>
      <div className="circle">
        {/* Canvas · 落日 */}
        <svg
          className="fb-sym fb-sym--canvas"
          viewBox="0 0 64 64"
          aria-hidden="true"
          fill="none"
          strokeLinecap="round"
        >
          <circle cx="32" cy="28" r="13" stroke="#C2532B" strokeWidth="1.4" />
          <circle cx="32" cy="28" r="13" fill="#E88957" opacity=".14" />
          <line x1="8" y1="44" x2="56" y2="44" stroke="#A8431F" strokeWidth="1.4" />
          <line x1="12" y1="49" x2="52" y2="49" stroke="#A8431F" strokeWidth=".9" opacity=".55" />
          <line x1="18" y1="53" x2="46" y2="53" stroke="#A8431F" strokeWidth=".7" opacity=".32" />
          <circle cx="32" cy="28" r="1.5" fill="#A8431F" />
        </svg>

        {/* Matcha · 禅圆 enso */}
        <svg className="fb-sym fb-sym--matcha" viewBox="0 0 64 64" aria-hidden="true" fill="none">
          <path
            d="M50 19 A22 22 0 1 0 48 46"
            stroke="#355F41"
            strokeWidth="4.6"
            strokeLinecap="round"
          />
          <circle cx="50" cy="19" r="2.8" fill="#1F3A28" />
          <path
            d="M46 47 L52 50 M48 45 L54 47"
            stroke="#355F41"
            strokeWidth="1"
            strokeLinecap="round"
            opacity=".5"
          />
        </svg>

        {/* Dusk · 桃花（单枝三花 + 一叶） */}
        <svg className="fb-sym fb-sym--dusk" viewBox="0 0 64 64" aria-hidden="true" fill="none">
          <path
            d="M12 46 Q24 38 34 30 T54 16"
            stroke="#8B3F5E"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
          <g transform="translate(22 39)">
            <g fill="#E88FA4">
              <ellipse cx="0" cy="-4" rx="3" ry="4.5" />
              <ellipse cx="0" cy="-4" rx="3" ry="4.5" transform="rotate(72)" />
              <ellipse cx="0" cy="-4" rx="3" ry="4.5" transform="rotate(144)" />
              <ellipse cx="0" cy="-4" rx="3" ry="4.5" transform="rotate(216)" />
              <ellipse cx="0" cy="-4" rx="3" ry="4.5" transform="rotate(288)" />
            </g>
            <circle r="1.6" fill="#B14774" />
          </g>
          <g transform="translate(42 22)">
            <g fill="#F0A8B9">
              <ellipse cx="0" cy="-6" rx="4" ry="6" />
              <ellipse cx="0" cy="-6" rx="4" ry="6" transform="rotate(72)" />
              <ellipse cx="0" cy="-6" rx="4" ry="6" transform="rotate(144)" />
              <ellipse cx="0" cy="-6" rx="4" ry="6" transform="rotate(216)" />
              <ellipse cx="0" cy="-6" rx="4" ry="6" transform="rotate(288)" />
            </g>
            <circle r="2" fill="#B14774" />
            <circle r=".7" fill="#FFE3ED" />
          </g>
          <path
            d="M28 36 Q32 32 30 27"
            stroke="#8B3F5E"
            strokeWidth="1"
            fill="none"
            strokeLinecap="round"
          />
        </svg>

        {/* Letterpress · 铅字印章（mockup selector 沿用 fb-sym--crimson） */}
        <svg className="fb-sym fb-sym--crimson" viewBox="0 0 64 64" aria-hidden="true" fill="none">
          <g transform="translate(32 32) rotate(-3) translate(-32 -32)">
            <rect x="13" y="13" width="38" height="38" fill="#1C1A17" />
            <rect
              x="15"
              y="15"
              width="34"
              height="34"
              fill="none"
              stroke="#F0EBE0"
              strokeWidth=".6"
              opacity=".5"
            />
            <text
              x="32"
              y="43"
              textAnchor="middle"
              fontFamily="'Noto Serif SC','Songti SC',serif"
              fontWeight="700"
              fontSize="24"
              fill="#F0EBE0"
            >
              乾
            </text>
          </g>
        </svg>

        {/* Ink · 太极 */}
        <svg className="fb-sym fb-sym--ink" viewBox="0 0 64 64" aria-hidden="true" fill="none">
          <defs>
            <clipPath id="fbTai2">
              <circle cx="32" cy="32" r="22" />
            </clipPath>
          </defs>
          <g clipPath="url(#fbTai2)">
            <path
              d="M32 10 A22 22 0 0 1 32 54 A11 11 0 0 1 32 32 A11 11 0 0 0 32 10 Z"
              fill="#0C0C0B"
            />
          </g>
          <circle cx="32" cy="32" r="22" fill="none" stroke="#0C0C0B" strokeWidth="1.1" />
          <circle cx="32" cy="21" r="2.2" fill="#F6F1E4" />
          <circle cx="32" cy="43" r="2.2" fill="#0C0C0B" />
        </svg>
      </div>
    </div>
  );
}
