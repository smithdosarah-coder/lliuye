# Platform Shell v2 · 视觉 1:1 复刻规范

**设计源**：`design_mockups/rm-assistant-final-2026-04-19.html`（3748 行，2026-04-19 lock）
**SHA-256**：`84a5e0efdb303bb53a1e833764f67eada2a733d9a4d3eedf2e575d2f967b9aac`
**规范状态**：v2.1 · 2026-04-20 修订（Task K1/K2/K3 复刻纠偏） · supersedes v1（`platform-shell-v1.md` 转 historical）
**落地目标**：Stage 4 frontend Worker 按本规范实装 — **视觉 1:1 复刻**
**更新权责**：主 CLI 唯一可写

---

## 修订记录

**v2.1 · 2026-04-20（Task K1-K3 纠偏）**：
1. **Today view** 补 `.rule` + `.belt`（今日账册金额条，mockup L3114-3141）— 原 Task D 读到 grid-3 结束就停，漏 29 行。
2. **Warroom view** 裁回 14 卡 / 6 pill variant — 原 Task I 按 onboarding 字面扩到 51 卡 / 10 variant，违反 R-0 mockup 优先原则。`WARROOM_LEDE_COUNT = "12"` 按 mockup 字面（即便 4+5+2+3=14，mockup 自身数字不一致也不动）。
3. **Float-badge 整体删除** — mockup L1024 `.float-badge { display: none !important }`，终稿用 CSS 强隐藏，PM 确认右下角圆形图标不在最终稿视觉内。**规范新增硬约束**：mockup 中任何带 `display: none !important` 的节点，实现时必须连组件带 CSS 一并移除，**不留幽灵 DOM**。

---

## 〇、本规范与 v1 的关系

v1（`shell.html` 2026-04-18 lock）是**信息架构 + token 体系**奠基；v2 是**视觉精细化 + 组件库扩充**。两者**架构同源**（4 view + Desk + Masthead + 4 主题 token + 字体栈 + 圆角 + 浏览器基线全部继承），v2 仅在以下维度演进：

- 主题：Canvas / Matcha / Dusk / Ink 共 4 主题（Letterpress/crimson 2026-04-20 下架——用户判"黑红读老 DEMO"）
- 静态背景 → 三层动画背景（bodyBreath + drift + breathe + noise turbulence overlay）
- 通用 v-card → 三种特化 peek card（feed-card / sheet-card / board-card）
- 简单 ul 列表 → case-stack 卷宗堆叠 + 6 Agent 功能色 token
- 静态 hero → glyph-rise 玻璃字逐字升起（JS 驱动）
- /dispatch /archive /warroom 三个 placeholder view → 全实装
- ~~顶栏右下角加 float-badge（5 主题 SVG 符号）~~ → mockup 自身 `display: none !important` 隐藏，v2.1 规范移除（Task K3）

`shell.html` 保留作为 v1 历史参考，**不删**。Stage 3 ext 已实装的部分（Masthead / Desk 骨架 / sheet-card / `/archive/[agent]` workspace clients）作为基线，Stage 4 在其上扩展，**不推翻**。

## 一、核心 mandate · 视觉 1:1 复刻

### 1.1 必须 1:1 的（"视觉"层）

- **CSS 全量端口**：终稿 `<style>` 块所有内容 → `web/src/app/{tokens,globals,shell,views}.css`，包括 4 主题 token / 5 keyframe / cursor SVG / noise turbulence overlay / 三层 body 背景 / 22+ 透明度滑块
- **DOM 全量重建**：4 view 内每一组件实例对应 React 组件，class 名称、嵌套结构、`data-*` 属性 1:1 保留
- **动画行为 1:1**：bar-in / glyph-rise / rise / card-rise / case-in / bar-flow / wait-slide / blip / bodyBreath / drift / breathe — 时长、缓动、延迟全部照搬
- **JS 交互 1:1**：staggerH1 逐字入场 / drawer hover-from-edge (mousemove < 22px) / pin / Esc / live clock / theme switcher（4 button，含 Ink）/ tab→route 切换
- **4 主题 token 全实装**：CSS 4 套；switcher UI 4 button（Canvas/Matcha/Dusk/Ink）— 2026-04-20 Letterpress/crimson 下架，原 `data-theme="crimson"` block + Letterpress 按钮一并删除
- ~~**5 Float-badge SVG**~~ — v2.1 删除（mockup `display: none !important`）
- **Mock 数据扩量**：终稿渲 15 条 feed / **4 col × 14 kanban kcard**（4+5+2+3，6 pill variant：P0/P1/P2/urg/wait/cn）/ 6 dispatch channel / 1 active thread w/ memo block — mock fixture 必须对齐该量级，否则视觉对不齐
- **mockup `display: none !important` 硬规则**：mockup 中带此声明的节点，**连组件带 CSS 一并移除**，不留幽灵 DOM（v2.1 追加，Task K3 教训）

### 1.2 不必 1:1 的（"实际对应"层）

| 维度 | 终稿写啥 | 实装走 |
|---|---|---|
| Port | (无明示) | 3000（Next.js 16.2.3 Turbopack 默认） |
| 路由 | 4 view DOM 切换 | 4 route + `/archive/[agent]` workspace 子路由（保留） |
| 时间 | hardcoded 08:47 / 16:35 | live clock，setInterval 每 20s |
| 日期 | 2026·04·18·FRI | 当日真实日期 |
| Persona | 王哲·客户经理·华东 | ✓ 已对齐 |
| Mock 内容文案 | 终稿 sample（宁海汇通 / 星河医药 / §214 / 林楠 等） | 复用为 mock fixture，**不视作业务真实数据** |

### 1.3 Stage 4 不动的红区

- ❌ `web/src/app/{credit,channel,alert,compliance,report,riskctrl}/` 老 6 路由（Stage 5 cleanup scope，本轮不删不改）
- ❌ `web/src/components/workspace/*/` Stage 3 ext 已实装的 6 workspace client（Stage 5 升级，本轮不动）
- ❌ `shared/` `docs/contracts/` `agent_*/` Python 后端代码（A-004 § 〇 红区，永久生效）
- ❌ `next.config.ts` `package.json` `tsconfig.json`（除非新增依赖，需 Q-NNN 与主 CLI 确认）
- ❌ `web/src/lib/agents.ts` 的 schema（Stage 3 ext A-015/016 已锁，Stage 5 升级）

## 二、信息架构（继承 v1）

| view | route | 定位 | mockup 锚点 |
|---|---|---|---|
| **今日** Today | `/today` | 个人 dashboard · 三模块 peek（消息/agent/任务）+ hero 玻璃字 | L2791-3144 |
| **对话** Dispatch | `/dispatch` | 3 列 IM · 频道 / 主对话 thread + memo / 卷宗侧栏 | L3145-3268 |
| **AI 助手** Archive | `/archive` · `/archive/[agent]` | 6 Agent tile 落地（替 placeholder）+ 子路由 workspace（**保留 Stage 3 ext 实装**） | L3270-3351 |
| **任务** Warroom | `/warroom` | 4 列 kanban（待处理/进行中/冒出/已归档） | L3353-3478 |

**Desk drawer**（共享）：固定左侧 hover-from-edge 抽屉，4 节（我的客户 / 进行中 / 最近 / 新建），含 ⌘K 搜索、4 quick-create 按钮。

**Masthead**（共享）：Logo `乾策 Studio` + 4 tab + 右侧 persona dot + name + role + live clock。

~~**Float badge**（共享）~~ — v2.1 删除（mockup L1024 `display: none !important`，PM 终稿意图）。

**Theme switcher**（共享）：底部右侧 4 button（Canvas/Matcha/Dusk/Ink），点切 `body[data-theme]`。

## 三、4 主题 token（终稿 L11-158，Letterpress 下架后）

| 主题 | data-theme key | switcher 标签 | --accent | 风格定位 |
|---|---|---|---|---|
| **Canvas**（默认） | (无 attr) | Canvas | `#A03B1C` | 米黄 → 橙红 → 墨绿，editorial 暖色 |
| **Matcha** | `matcha` | Matcha | `#A04A2A` | 米杏 → 抹茶 → 墨绿，清雅 |
| **Dusk** | `dusk` | Dusk | `#CE4A65` | 粉白 → 玫瑰 → 紫黑，暮色桃花 |
| **Ink** | `ink` | Ink | `#8A2622` | 宣纸白 → 淡墨 → 浓墨 + 朱砂 accent，水墨 |

**2026-04-20 退场**：原 Letterpress / crimson 主题（米色 → 灰黑活字印刷感）整体下架。用户裁决"黑红读老 DEMO"；原 `[data-theme="crimson"]` CSS block + switcher 按钮 + `fb-sym--crimson` SVG 已从 mockup 与实装同步删除。

每主题暴露 `--g0..g7`（8 档渐变）+ `--g0b`（米黄变体）+ `--accent` + `--ink` + `--chalk` + `--safe`。

**透明度滑块**：`--ink-04..ink-80`（10 档，新增 ink-08/14/18/32 等 7 档细分）+ `--ch-08..ch-96`（22 档）。Ink 主题独立 body bg + ::before + ::after override（终稿 L136-158）。

**字体栈**：继承 v1（Funnel Display / Instrument Sans+Serif / Noto Sans+Serif SC / JetBrains Mono），Google Fonts CDN。

**圆角**：继承 v1（`--r-md: 18px` / `--r-lg: 26px`）。

**Cursor**：自定义点状 SVG，data URL 硬编码到 `--cursor-default`，body 应用。

## 四、组件库清单（按 view 拆，含 mockup 行号）

### 4.1 Shell（跨 view · 持久）

| 组件 | class | mockup 行 | 行为 |
|---|---|---|---|
| Drawer 容器 | `.drawer .dr-panel` | L2645-2768 | hover-from-edge < 22px 唤出，pin 钉住，Esc 收起 |
| Drawer head | `.dr-head .dr-pin` | L2650 | "工作台 Desk." 标题 + ◆ pin 按钮 |
| Drawer search | `.dr-search` | L2655 | input + ⌘K kbd hint |
| Drawer section | `.dr-sec .hd` | L2661-2725 | 4 节（我的客户/进行中/最近/新建） |
| Drawer row | `.dr-row .ic .nm-wrap .ts` | L2663+ | 状态点（dot-p0/dot-warn/dot-live/dot-chat）+ 名称 + 子文案 + 时间戳 |
| Drawer quick-create | `.dr-qc button .plus` | L2759 | 4 button（新对话/新任务/起草报告/开始获客） |
| Masthead bar | `.bar` | L2773-2787 | 入场动画 bar-in 0.9s + grid-template logo/tabs/op |
| Logo | `.logo .cn sup em` | L2774 | 乾策®Studio |
| Tabs | `.tabs button[data-v]` | L2775-2780 | 4 tab + .on 高亮 + n 编号 |
| Op (persona) | `.op .dot .name .role .time` | L2781-2786 | 安全 dot + 王哲 + 客户经理·华东 + live time |
| ~~Float badge~~ | ~~`.float-badge .mini .circle`~~ | ~~L3483-3558~~ | **v2.1 删**（mockup L1024 `display: none !important`） |
| Theme switcher | `.theme-sw button[data-t]` | L3562-3569 | 4 button + .on 高亮 + sw-dot |

### 4.2 Today view（L2791-3144）

| 组件 | class | mockup 行 | 备注 |
|---|---|---|---|
| Eyebrow | `.eyebrow span sep em` | L2794-2798 | 日期 + 早上好问候 |
| Hero h1 | `.hero-h1 .word .glyph(.cn)` | L2800-2802 | 单 word "今日看板" + glyph-rise 逐字 stagger |
| Hero meta | `.hero-meta--row .kv.big .pill` | L2804-2809 | 4 项（管道/队列/风险/LIVE pill） + kv unit-split (vnum + vunit) |
| 3-card grid | `.grid-3` | L2812 | 3 列均分 + card-rise 错峰入场 |
| **Feed card** | `.card.feed-card` | L2815-2950 | 消息预览，15 条 .feed-item（urgent/unread/sys） + .feed-av（warn/sys） + mask fade |
| **Sheet card** | `.card.warm.sheet-card` | L2953-3038 | ✓ Stage 3 ext 已实装；mock TODAY_RUNNING_SHEETS×3 + TODAY_IDLE_SHEETS×3 |
| **Board card** | `.card.deep.board-card` | L3040-3112 | 任务钉板，深色渐变 + .peek-list + .pk + .pk-bullet (mention/meeting/agent/pr-p0/pr-p1/pr-urg) + .pk-bar (waiting variant) |
| **Rule + Belt** | `.rule` + `.belt .col` | **L3114-3141** | **v2.1 补**：今日账册金额条，`.rule` 左右 grid（lbl/ln/rt）+ `.belt` 4 列（k 标签 / v.currency unit / note 含 em + strong） |

**Mock 扩量**：
- `TODAY_FEED`: 5 → **15** 条（含 urgent/unread/sys flag + org tag + ts）
- `TODAY_TASKS` → 替为 `TODAY_PEEK`：含 type (mention/meeting/agent/pr-p0/pr-p1/pr-urg) + bar pct + waiting flag
- **`TODAY_BELT`**（v2.1 补）：4 col（本月已放款 28.47 亿元 / 待签卷宗 27 份 / 观察名单黄 08 户 / 本周新政 04 条）+ `TODAY_BELT_RULE`（lbl + rt 时间戳）

### 4.3 Dispatch view（L3145-3268）

| 组件 | class | mockup 行 | 备注 |
|---|---|---|---|
| 3 列容器 | `.dispatch .dp-col .dp-main .dp-info` | L3158 | grid 3 列：频道 / 主对话 / 卷宗 |
| Channel list | `.ch-list .ch (.on)` | L3165-3196 | 6 频道 + last preview + meta 时间 |
| Thread | `.thread .msg (.me) .ln em .tm .bd` | L3204-3245 | 4 message（含 me 自己 + agent + memo block） |
| Memo block | `.memo .mhd ol li (h, s) .mft .chip (.ghost)` | L3219-3243 | Agent 输出含 ol 三点 + 3 chip（全部采纳/质疑/追溯原文） |
| Composer | `.composer input button.send` | L3247-3250 | "写一则 note … ⌘K 召唤 Agent · ⌘⇧E 附证据" + 发送按钮 |
| Info 卷宗 | `.dp-info .body .row .k .v .sub` | L3253-3265 | 5 row（卷宗号/授信金额/填写完成度/红线/签署进度） |

**Mock 新增**：`web/src/lib/mock/dispatch.ts`：
- `DISPATCH_CHANNELS`: 6 channel（id, name, last_preview, last_ts, unread, on）
- `DISPATCH_THREAD`: 1 active thread（{messages: [{who, role, ts, body, memo?}]}）
- `DISPATCH_DOSSIER`: 1 卷宗 row 数据

### 4.4 Archive view（L3270-3351）

| 组件 | class | mockup 行 | 备注 |
|---|---|---|---|
| Eyebrow / Hero / Lede | `.eyebrow .hero-h1 .lede` | L3273-3282 | "你的 agents." + 6 位助手听你调遣 |
| Tile grid | `.archive .agent (.g2..g6)` | L3284-3349 | 6 tile（Scout/Forge/Bench/Tower/Ledger/Press） |
| Tile 内部 | `.ix h4 .cn em .circle .blurb .foot .stat .num .open` | L3286+ | AGENT 编号 + 中英双语标题 + 大圆数字 + 简介（含 em 高亮） + 统计 + 进入箭头 |

**点击行为**：tile 点击 → `next/link` 跳 `/archive/[agent]`（**保留 Stage 3 ext 实装的 workspace clients**，不替换）。

**Mock**：复用 `web/src/lib/agents.ts` 现有 AGENTS 常量 + 新增 `circle / blurb / stat` 字段（per-agent）。

### 4.5 Warroom view（L3353-3478）

| 组件 | class | mockup 行 | 备注 |
|---|---|---|---|
| Eyebrow / Hero / Lede | `.eyebrow .hero-h1 .lede` | L3356-3365 | "正在 flight." + **"12 项在飞"**（mockup 字面，尽管 4+5+2+3=14；R-0 mockup 优先，不改） |
| Kanban | `.kanban .kcol (.done) .khd .kbody` | L3367-3477 | 4 列（待处理·04 / 进行中·05 / 冒出·02 / 已归档·03），**总计 14 卡** |
| Kcard | `.kcard .hd .t .pr (.P0 .P1 .P2 .urg .wait .cn) .meta .body .ft .who .av .go` | L3372+ | 优先级 pill **6 variant**：P0 / P1 / P2 / urg（加急） / wait（等候） / cn（新/完 复用） |

**Mock（v2.1 纠偏）**：`web/src/lib/mock/warroom.ts`：
- `WARROOM_COLUMNS`: 4 col（待处理·04 / 进行中·05 / 冒出·02 / 已归档·03，含 done flag）
- `WARROOM_CARDS`: **14 kcard 严格对齐**（id, column, title, pill, meta 含 cn wrap, body 含 em, who avatar, go "打开"/"查看"）
- `WARROOM_LEDE_COUNT = "12"` — mockup 字面（镜像 mockup 自身不一致）

**Task K2 教训**：Task I 按 onboarding 字面扩到 51 卡 / 10 pill variant（P3/compli/law/risk 等），违反 R-0 mockup 优先。v2.1 裁回严格 mockup literal（14 卡 / 6 pill）。**新增硬约束**：onboarding 字面与 mockup 不一致 → 以 mockup 为准。

## 五、动画与交互清单

| 名称 | 时长 | 缓动 | 触发 | 用途 |
|---|---|---|---|---|
| `bar-in` | 0.9s | `cubic-bezier(.2,.8,.25,1)` | mount + 0.15s delay | Masthead 滑入 |
| `glyph-rise` | 0.95s | `cubic-bezier(.2,.78,.2,1)` | per char 0.045s stagger | hero h1 逐字升 |
| `rise` | 0.8-1s | `cubic-bezier(.2,.8,.25,1)` | mount + delay | eyebrow / lede / hero-meta |
| `card-rise` | 1.05s | `cubic-bezier(.18,.82,.22,1)` | mount + nth-child delay | 3 卡错峰入场 |
| `case-in` | 0.55s | `cubic-bezier(.2,.82,.22,1)` | per case stagger | case-stack 行入场 |
| `bar-flow` | 1.8s | `cubic-bezier(.2,.8,.25,1)` | mount + 2.8s delay | pk-bar 进度填充 |
| `wait-slide` | 1.2s | linear infinite | bar-flow done 后 | waiting 条纹漂移 |
| `blip` | 2.4s | ease-in-out infinite | always | LIVE 安全 dot 呼吸 |
| `bodyBreath` | 22s | ease-in-out infinite | always | body 整体 saturate/brightness 呼吸 |
| `drift` | 38s | ease-in-out infinite alternate | always | body::before 雾层漂移 |
| `breathe` | 8.5s | ease-in-out infinite | always | body::before blur+brightness 呼吸 |

**JS 交互**：
- `staggerH1(h, baseDelay)`：把 hero h1 内 `.word > .glyph` 拆字 + 设 `animation-delay`（React effect，SSR 安全）
- Drawer hover-from-edge：global mousemove，`e.clientX < 22` → add `.open`；`> 360` 且非 pin → 180ms 延迟移除
- Drawer pin：`◆` 按钮 toggle `.pin` class
- Esc：移除 `.open` `.pin`
- Live clock：setInterval 20s tick，更新 `.bar .time` + hero `.pill`
- Theme switcher：button click → `body.setAttribute('data-theme', t)`（canvas 时移除 attr）
- Tab → route：`button[data-v]` click → Next.js router.push(`/${v}`)（取代终稿的 view toggle）
- Case chip 点击：`bub-detail` 弹层在卡内展开详情；点卡空白跳 view

## 六、浏览器基线（继承 v1）

`color-mix(in srgb, ...)` + `backdrop-filter` + SVG `feTurbulence` + `mix-blend-mode: multiply`：
- Chrome / Edge ≥ 111
- Safari ≥ 16.4
- Firefox ≥ 113

银行内网兼容（旧 IE / WebView）：Stage 6 评估自托管字体 + 降级方案；本规范不做兼容处理。

## 七、Stage 4 任务总览

详见 `docs/onboarding/frontend-stage-4-rmassistant.md`。10 Task A-J，依赖图：

```
A (tokens) ──┬─→ B (shell) ──┬─→ D (today hero)
             │               ├─→ E (today feed-card)
             │               ├─→ F (today board-card)
             │               ├─→ H (archive 6-tile)
             ├─→ C (drawer) ─┤
             │               ├─→ G (dispatch)
             │               └─→ I (warroom)
             └────────────────────→ J (regression sweep)
```

Worker 派发推荐：
- **单 Worker 串行**：A → B → C → D → E → F → G → H → I → J（约 3 工作日）
- **多 Worker 并行**：A 单干 → B+C 并行 → D-I 6 Worker 并行 → J 单干（约 1 工作日）

## 八、Q 决议（v2 落地默认）

| Q | 议题 | 默认决议 | 可 override |
|---|---|---|---|
| **Q-A** | 老 6 路由（/credit /channel 等）Stage 4 顺手清掉？ | **Defer Stage 5** — 终稿不含但实装无冲突 | 主 CLI 拍板可改 |
| **Q-B** | `/archive/[agent]` workspace UI 升级到新设计语言？ | **Defer Stage 5** — Stage 4 mandate 仅覆盖 mockup 渲染范围 | 主 CLI 拍板可改 |
| **Q-C** | Crimson 重定义为 Letterpress 单色 — retake 老演示截图？ | **Stage 4 末段（Task J）一次性 retake** + 在交付物里说明"4-19 起 Crimson → Letterpress" | 客户特殊要求可保留双版 |
| **Q-D** | 单 Worker vs 多 Worker dispatch | **Onboarding 同时支持** — 主 CLI 临时定 | — |

## 九、规范变更流程（继承 v1）

- 发现 mockup 与 spec 不一致 → 以 mockup 为准 → 主 CLI 补 spec
- 发现 spec 缺信息 → 主 CLI 补 spec · 不在 onboarding 里临时决策
- `docs/contracts/` 红区变更 → 走 shared-change-protocol v1.1 RFC
- mockup 二次更新 → 新版本号（v3 / v4 ...）+ 更新 `CLAUDE.md §7` lock date 与 sha256
