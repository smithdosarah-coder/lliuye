# 12 View Screenshot Inventory · R1 v2 Gemini Round

**Captured**: 2026-04-30 02:32-02:36 (local) · ECS production https://liuye.me
**Account**: u_wangzhe / wangzhe (RM 客户经理 王哲 · 华东·上海第一支行)
**Accessible agents**: channel / report / credit / alert / compliance / riskctrl (RM role · 6/6 全开)
**Viewport**: 1440 × 900 · fullPage screenshots
**Output dir**: `docs/research/screenshots-2026-04-30/v2/`

## 总览: 12/12 全成 OK

无 fail · 无 RBAC 阻断 · 无 404/500 · 不需切 admin (u_liuye) — RM 单账号覆盖全部 12 view。

## 详细 inventory (按截图顺序)

| # | filename | URL | size | 状态 / 备注 |
|---|---|---|---|---|
| 01 | `01-login.png` | `/login` | 680 KB | OK · 黑洞 3D 背景 + 右侧 sign in panel · persona 默认 王哲 + bcrypt backend chip |
| 02 | `02-today.png` | `/today` | 1510 KB | OK · 今日看板 hero (15 / 03 / 06 三块计数) + Priority queue 5 tickets + Timeline 5 events |
| 03 | `03-dispatch.png` | `/dispatch` | 1558 KB | OK · 默认空 thread (per spec 不需点击) · 左 8 conversation (5 group + 3 direct) · 中央 ⌘K 引导 · 右侧客户档案占位 |
| 04 | `04-archive.png` | `/archive` | 1423 KB | OK · 6 Agent tile 平铺 (获客 Scout / 风控 Forge / 授信 Bench / 预警 Tower / 合规 Ledger / 报告 Press) · 各带计数 chip |
| 05 | `05-archive-report.png` | `/archive/report` | 1404 KB | OK · 报告 Press workspace · idle 状态 (等待触发) · 含上传区 + 模板/历史/业务线 select + 演示难度分层 (简单/中等/困难) chip + 不调 LLM 红线 |
| 06 | `06-archive-credit.png` | `/archive/credit` | 1385 KB | OK · 授信 Bench workspace · 板块 tab (对公/普惠/对私) · 3 主操作 card (从 Agent6 起决策 / 演示模式 / demo scenario) + 4 维评分 + 红线 + 案例 + 决策建议书 panel · idle 状态 |
| 07 | `07-archive-channel.png` | `/archive/channel` | 1273 KB | OK · 获客 Scout workspace · KB 上传 3 类 (客户名录 / 政策文件 / 行业指引) + Query 双模式 + 12 标 mock chip + 等待触发空态 |
| 08 | `08-archive-alert.png` | `/archive/alert` | 1889 KB | OK · 预警 Tower workspace · session "2026-04-21 周度贷中预警扫描 (常态批次)" · 含 6 维 metric / 红 3 黄 7 绿 90 计数 / Top 命中 8 客户 tile / 详情 drawer 打开 (TopAlerts + 操作记录 + 上传 KB + 命中规则 chips + 客户列表 + 通话纪要 + history) · 6 列指标 / 投放雷达 / 证据链 |
| 09 | `09-archive-compliance.png` | `/archive/compliance` | 2075 KB | OK · 合规 Ledger workspace · 政策《消费金融公司管理办法》修订版 - 条款冲突扫描 · 6 维 metric / 上传政策 / 影响评估 chips / 业务规则左 list / 详情 drawer + 影响矩阵 (5×4 colored grid 严重度) + 处置建议 3 card (公开决议 / 我已采集冷案 / 主动事件) + 处置记录 / 日志 |
| 10 | `10-archive-riskctrl.png` | `/archive/riskctrl` | 1628 KB | OK · 风控 Forge workspace · 新客户首贷拒绝策略 v1.5 · KS 0.42 / AUC 0.762 / PASS 32% / Cost 6 列 metric · Query 样本/目标指标 + Rules 在线 4 strategy + Conversation thread (策略命中率 K0.42 / 通过率 32%) + Output DSL v1.5 r3 · IF AND OR THEN nested 决策树 + 证据链 4 条 |
| 11 | `11-customer.png` | `/customer/cust_zrgs` | 1405 KB | OK · 中锐工商 360 视图 · CUST_ZRGS · hero (行业 批发零售 / 区域 华东 / 阶段 报告撰写 / 授信 5000 万) + Agent 产出 6 tile (A06 报告完成 + A01 Look-alike + A03/02/04/05 暂无产出) + 时间线 4 events + 协同人员 (王哲 + 李华) |
| 12 | `12-warroom.png` | `/warroom` | 1416 KB | OK · 4 列 kanban (待受理 1 / 已受理 1 / 进行中 0 / 已完成 1) · 3 张 ticket (中锐工商 流转 → 报告→报告 / 海元供应链 流转 获客→报告 / 鼎川精密 加急 已完成) + 我的任务/全部 toggle + 5 维 filter chip |

## 总文件 size: 17.3 MB (12 张 · 平均 1.4 MB)

## RBAC 切账号

无切换 — RM 单账号 u_wangzhe (role=rm · accessibleAgents 全 6) 覆盖全部 12 view · login API 返回 token 后 cookie session 跨所有 view 通行。

## 特殊状态总结

- **空态/idle** (用户未上传材料 / 未触发任务): 05-archive-report / 06-archive-credit / 07-archive-channel · 三 workspace 都已显示完整骨架 + 等待触发 placeholder · Gemini 可看到 input 入口 + KB 上传 + 演示模式 chip · 设计意图清晰
- **空 thread**: 03-dispatch · 默认未选 conversation · 左侧 group/direct list 完整可见
- **rich content**: 08-archive-alert / 09-archive-compliance / 10-archive-riskctrl · 三 workspace 均已含完整 demo session (mock 数据 / metric / drawer / DSL / matrix) · 截图含 main + drawer 同屏
- **错误页**: 无 · 12 view 全部 200 OK

## 注意事项 (供主 CLI 决策给 Gemini)

1. 03-dispatch 是默认空 thread 状态 · 若 Gemini 想看消息流形态需另截 thread 内态 (当前未截 · spec 明示不需点击)
2. 11-customer 用了 cust_zrgs (中锐工商 · 报告撰写阶段 · 授信中) · Agent 产出 5/6 tile 是空 ("暂无产出") · 若想看更"满"的客户档案需找别的 cust_id
3. 05-07 三 workspace 是 idle 态 · 若 Gemini 反馈"看不到 active 状态" 主 CLI 可考虑触发一个 mock demo (如点 demo scenario 起决策 / 选历史 session) 后补图
4. 截图全 fullPage · 长 view (08 alert ~3000px / 09 compliance ~3500px) 已完整截入
