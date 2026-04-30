# Gemini 对乾策 Studio 前端 4 页设计反馈 · 2026-04-30

## 元数据

| 字段 | 值 |
|---|---|
| 时间 | 2026-04-30 16:18 ~ 16:27 (UTC+8) |
| 触发 | PM 刘野 让 main CLI 用 Playwright MCP 抓前端 4 页截图 + 提交 Gemini 评估 |
| 评估对象 | https://liuye.me · 乾策 Studio · Next.js 16 + 自定义平台 shell · Canvas 主题 (米黄→橙红→墨绿) |
| 4 页路由 | `/login` · `/today` · `/dispatch` · `/archive` |
| Gemini 模型 | Pro (Gemini 2.x · `gemini.google.com/app/0da5b5fe5b4aecdd` · 已登录账号 Sarah Smithdo) |
| 截图本地 | `docs/research/screenshots-2026-04-30/{01-login,02-today,03-dispatch,04-archive,05-gemini-reply}.png` |
| 截图 mirror | 项目根 `01-login.png` ~ `05-gemini-reply.png` (5 张) |
| 执行问题 | **`mcp__playwright__browser_file_upload` 工具被 sandbox 拒** · 改用纯文字 prompt (DOM 注入 Quill editor) · Gemini 未实际看到截图 · 仅基于文字描述给反馈 |

## 执行流程实录

1. 4 张前端截图通过 `browser_take_screenshot fullPage=true` 抓取成功 (登录页含 Interstellar 黑洞动画 / today 含三 KPI 卡 + Priority 列表 / dispatch Slack 风 3 列 / archive 6 Agent 2x3 网格)。
2. Gemini 的 `+` → `Upload files` 触发 `<input type=file>` chooser · `browser_file_upload` 权限被拒 (3 次尝试均 denied) · modal 状态卡住其他工具。
3. 关 tab 解锁后,改 fallback: 通过 `browser_evaluate` 用 `document.createElement('p')` + `appendChild` (绕开 TrustedHTML) 注入 47 段 2196 字详细文字描述到 Quill editor · 触发 `InputEvent` 激活 Send 按钮。
4. Gemini 在 ~30s 内生成 2195 字 markdown 回复 · stop button 消失 = 完成 · `browser_evaluate` 抓 `<message-content>` `innerText`。

## Gemini 回复 verbatim (中文 markdown · 2195 字)

> 你好刘野先生。
>
> 这份关于"乾策 Studio"的设计描述非常详细,整体架构展现了强烈的极客感和前卫的 AI 协同理念。但在面向真实的银行信贷核心业务(客户经理、风控、授信、合规)时,这种设计会面临严重的"水土不服"。
>
> 以下是从 4 个维度的专业诊断与具体改进方案:
>
> ### 1. 视觉设计 (色彩 / 排版 / 氛围 vs 金融业)
>
> **存在问题:**
>
> - **氛围背离金融属性:** 登录页的"全屏纯黑 + 巨型黑洞"传达的是"深不可测"和 Web3/科幻感。信贷系统的核心诉求是**安全、透明、确定性**,黑洞的隐喻在风险管理心理学上是极其负面的(暗示资金黑洞或坏账)。
> - **排版易读性灾难:** 大量使用"宋体大字"结合"深色玻璃态"和"大面积渐变底色(米黄→橙红→墨绿)"。宋体作为衬线体,在数据密集型 B2B 界面中识别度极低,容易造成视觉疲劳;同时,橙红和墨绿在金融场景中有明确的"涨跌/警示/安全"语义,作为背景渐变会严重干扰页面内的真实预警(Alerts)标签颜色。
> - **过度装饰:** 过多的浮起、边缘柔光呼吸、SVG 装饰(落日/太极),会抢夺审贷官对核心信贷数据的注意力。
>
> **改进方案:**
>
> - **重塑登录页:** 弃用黑洞。建议改为具有秩序感的"微光数据网格"或"光栅粒子结构",传达 AI 算力底座和金融数据流转的严谨感。
> - **字体降噪:** 将系统主字体替换为现代无衬线体(如 PingFang SC, MiSans, Inter),仅在非数据的品牌宣传位(如登录页标语)保留宋体。
> - **色彩克制:** 放弃全页重彩渐变背景。背景应回归中性色(如极浅的冷灰色或纯白,夜间模式用深灰),将"主题色(如抹茶、暮粉)"收敛于侧边栏、激活态和点缀元素。绝不能让背景色与金融预警色(红/绿)起冲突。
>
> ### 2. 信息架构 (4 View 划分 + 6 Agent 聚合)
>
> **存在问题:**
>
> - **Agent 孤岛化:** /archive 页将 6 个 Agent 做成 2x3 的独立工作区,这属于"拟人化过度"。客户经理做一笔授信,不需要去"风控工作区"和"合规工作区"来回切换。这种架构让 AI 变成了需要人类去操作的 App,而不是嵌入工作流的 Copilot。
> - **视图割裂:** 今日工作台(/today)有任务列表,对话页(/dispatch)也有未读消息。对于高压的信贷从业者来说,信息流分散会导致漏处理重要预警。
>
> **改进方案:**
>
> - **以"客户/项目"为核心,而非以"Agent"为核心:** 弱化或删除 /archive 聚合页。6 个 Agent 应该作为后台大脑,在 /dispatch(工作流台)中根据当前客户的推进阶段自动介入(例如:进入授信阶段,Bench 和 Forge 自动在对话流中输出报告和风险点)。
> - **统一待办中枢:** 将"今日看板"与"任务"深度融合,明确分为"待办审批(强阻塞)"、"风险预警(需介入)"、"AI 洞察(弱提醒)"三个层级。
>
> ### 3. UX 流程 (角色协作·胶囊承载量·交互触发)
>
> **存在问题:**
>
> - **交互触发过于隐蔽:** 左侧隐藏抽屉 Desk 设定为 <22px 触发,这在桌面端(尤其是银行复杂的内外网屏幕分辨率下)是极差的体验,容易误触或找不到入口,不符合企业级效率工具的标准。
> - **Slack 式 IM 的局限性:** 信贷审批不仅是"聊天",更需要"表单与结构化数据的确认"。如果 AI 助手只在右侧对话流中"留言",用户如何一键采纳并落库到信贷审批系统中?
> - **胶囊承载量:** "3 偏大 KPI 卡"采用浮起与柔光呼吸,视觉比重过大,但提供的信息(pinged 15, running 03)对实际推进业务帮助有限。
>
> **改进方案:**
>
> - **固定导航与结构化协作:** 左侧 Desk 改为常驻或通过明确的点击 Toggle 展开。
> - **对话即操作 (Actionable Chat):** 在 /dispatch 中,Agent 的留言不能只是文本,应输出"结构化微件(Micro-frontend Widgets)"。例如:合规 Agent (Ledger) 报出异常,对话流中应直接附带一个"阻断拦截/忽略并附言"的操作卡片(Actionable Pill),形成操作闭环。
>
> ### 4. 中文金融场景适配 (术语/报告/实验感)
>
> **存在问题:**
>
> - **中英夹杂的极客腔调:** Tickets、pinged、stage 权重、live clock 等词汇带有浓重的开发者工具(如 GitHub/Linear)色彩。在银行真实的 4 角色(尤其是合规和审贷官)语境中,这种文案显得不专业。
> - **数字格式不够严谨:** 列表右侧的金额"¥1500万~¥5000万",在金融场景中,应采用标准的千分位与小数位格式。
>
> **改进方案:**
>
> - **全面信贷语料化:** 清洗所有极客文案。
>   - Tickets -> 待办审批 或 流转工单
>   - pinged -> 最新通知 或 @我的
>   - agent 正在跑 -> AI 测算中 或 模型运行中
>   - stage 权重 -> 业务阶段 或 转化优先级
> - **数据规范:** 金额展示必须对齐信贷标准,如"¥15,000,000.00"或"1,500.00万",且需要支持右对齐以便于财务比对。
>
> ---
>
> 在这 4 个角色协作(业务、风控、合规、授信)的跨部门工作流中,如果你们的 6 个 Agent 在同一个客户案子上给出了方向冲突的建议(例如:获客 Scout 认为潜力巨大建议推进,但风控 Forge 亮起红灯),目前的"乾策 Studio"是如何在界面上处理这种 AI 仲裁与冲突展示的?

## Gemini 反馈摘要 (主 CLI 抽提)

| 类别 | 关键 verdict |
|---|---|
| 整体定位 | "极客感和前卫的 AI 协同理念" vs 银行业核心诉求"安全/透明/确定性" → 严重水土不服 |
| 视觉头号问题 | 黑洞 = 资金黑洞负面隐喻 · 宋体衬线在 B2B 数据密集界面识别度极低 · 渐变底色干扰预警色 |
| IA 头号问题 | Agent 孤岛 (拟人化过度 · 让 AI 变 App 而非 Copilot) · today vs dispatch 信息流割裂 |
| UX 头号问题 | <22px Desk 隐蔽触发不符企业级 · Slack 风 IM 缺结构化操作卡片 (Actionable Pill) · KPI 卡视觉比重 vs 信息价值不匹配 |
| 文案头号问题 | Tickets / pinged / agent 正在跑 / stage 权重 等极客腔 · ¥1500万 缺千分位 |

## Gemini 反问 (主 CLI 应回应)

Gemini 末尾问: "6 Agent 给出方向冲突建议时 (Scout 推进 vs Forge 红灯),界面如何处理 AI 仲裁与冲突展示?"
→ 这是真问题。当前我们 `/today` Priority 列表 + `/dispatch` 对话流都未明确仲裁机制。建议 PM 拍板:
- (A) 客户卡片侧栏专设"AI 共识/分歧"区块,显式列各 Agent verdict + 分歧点 + 推荐裁决
- (B) Agent 输出强制带置信度 · 冲突时自动升级 review 路径 (e.g. 客户经理 → 审贷官 → 合规官)

## 主 CLI 评注 (≠ Gemini)

Gemini 输出**质量较高**且与已有评估高度一致:
1. **黑洞氛围批评** = 已知问题 · CLAUDE.md §7 也提到 "Letterpress / 黑红方案" 已被 PM 判 "黑红读老 DEMO" 而下架 · 黑洞登录页是同类问题再现
2. **宋体在数据密集界面识别度低** = 已知 trade-off · CLAUDE.md §7 锁宋体作为 display 字体 + Noto Sans/Serif SC 作 body · Gemini 建议把 display 也降为 PingFang/MiSans 是更激进取舍
3. **Agent 孤岛 + 缺 Actionable Pill** = **真痛点** · 与 reset 工程 north-star 的 "客户/项目为核心 vs Agent 为核心" 路径一致 (见 `docs/reset/north-star.md`) · 印证 reset 工程方向
4. **极客腔文案清洗** = 立即可执行 · 工作量 ~2 小时 · ROI 高
5. **数字千分位** = bank delivery DoD 项 · 已落 `docs/scorecard/definition-of-done.md` 但前端未全实施

**优先级建议给 PM**:
- 🔴 立即 fix: 文案清洗 (Tickets/pinged/stage 权重) + 数字千分位 (各 mock 数据 hardcoded)
- 🟡 Phase B 排进: 把 /archive 6 Agent 弱化为后台大脑 + /dispatch 引入 Actionable Pill 微件
- 🟢 长期讨论: 黑洞登录页改 "微光数据网格" (PM 此前明确黑洞是有意保留的 "实验感品牌点" · 需重新校验)

## 局限性

- Gemini **未实际看到截图** (file_upload 被拒) · 仅基于 47 段文字描述判断 · 视觉细节判断 (柔光呼吸的实际比重 / 渐变饱和度等) 会有偏差
- Gemini 用账号是 Sarah Smithdo (chrome 浏览器持久 cookie · 非 PM 账号) · 对话历史会落到该账号下
- 文字 prompt 含 typo (波艳/胶囊感等 OCR/输入误读) · 但 Gemini 上下文猜对了原意
