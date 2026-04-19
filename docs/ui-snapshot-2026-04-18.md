# UI 现状快照 · 2026-04-18

**分支**：`feat/tiered-search`
**扫描范围**：`web/` 全目录 + `feat/tiered-search` 最近 20 个 commits
**扫描日期**：2026-04-18
**扫描人**：主 CLI 派出的 Explore agent（由主 CLI 整理落盘）
**UI 完成度（按 unified platform pivot 要求粗估）**：**45%**

---

## 一、信息架构

当前 7 个路由：首页 + 6 个 Agent 工作区。AppShell 仅提供基础顶栏 + 侧栏导航。

**对照 unified platform pivot（2026-04-17 确立）**：
- ✅ 共享 AppShell 基础（顶栏 / 侧栏）
- ❌ 右栏协作面板
- ❌ 全局搜索
- ❌ 通知中心
- ❌ 登录态 / 账户切换 UI

**结论**：现有 shell 与 pivot 要求的"协作平台"相差甚远——当前仍更接近"6 Agent 卡片拼接 + 共享导航"，pivot 里的平台级元素几乎未启动。

---

## 二、关键组件 / 页面

6 个 Agent 页面 UI 美观度高，统一采用"左 INPUT + PIPELINE / 右结果区"的双栏布局。

**自建组件库（无 shadcn / Radix 依赖）**：
- `ScoreRadar`（授信四维雷达 / 预警信号灯）
- `PipelineRail`（流程进度条，SSE 驱动）
- `Card` / `VerdictBadge`（卡片 + 裁定徽章）
- `ChatTagInput`（对话式标签输入）

**导航模型**：当前为 Next.js 16 路由切换（本质是独立页面），不是 pivot 要求的"shell 内工作区切换 + 保留上下文"。

---

## 三、数据依赖（前后端契约）

### 3.1 已接通 endpoint
- `/api/credit/presets`、`/api/credit/decision`
- `/api/channel/run`
- `/api/report/*`（Agent6 最成熟）

### 3.2 前端依赖、后端缺失（Top-5 脱节点）
| # | 前端调用 | 后端状态 | 影响 Agent |
|---|---|---|---|
| 1 | Compliance 一套 endpoint（前端 UI 完整） | 后端仅 stub | Agent5 |
| 2 | `/api/riskctrl/backtest` | 后端无 | Agent2 |
| 3 | `/api/alert/scan_portfolio` | 后端无 | Agent4 |
| 4 | `/auth/*` 登录会话 | 后端无鉴权层 | 全平台 |
| 5 | sessionStorage 跨页预填 | 后端无会话端点 | 跨 Agent |

### 3.3 后端已有、前端未接通（Top-3）
| # | 后端 endpoint | 前端状态 |
|---|---|---|
| 1 | `/api/feedback` | 前端无调用 → 数据飞轮未闭环 |
| 2 | `/api/feedback/stats` | 前端无仪表盘 |
| 3 | `/api/channel/scenarios` | 前端未接入场景元数据 |

### 3.4 字段命名 / 单位不一致清单
- `amount` 在不同 Agent 中单位混用（万元 vs 元）
- `approved_amount` 单位未标注
- `is_hard`（bool）+ `severity`（enum）语义重复（红线触发既有硬开关又有等级，字段冗余）

---

## 四、设计系统（对照 CLAUDE.md §7）

| 项 | 要求 | 实际 | 状态 |
|---|---|---|---|
| 深炭 | `#07090B` | `#0d1116` | ✅ 接近（色调一致） |
| 纸白 | `#FDFBF6` | `#fbf7ee` | ✅ 接近 |
| 古铜金 | `#F0D488` | `#f0d488` | ✅ 完全对标 |
| Display 字体 | Fraunces | Fraunces | ✅ |
| Body 字体 | Geist Sans | Geist Sans | ✅ |
| Mono 字体 | Geist Mono | Geist Mono | ✅ |
| 图表库 | 未指定 | recharts | ✅（足以覆盖雷达 / 条形 / 信号灯） |

设计系统**完全符合**项目规范。

---

## 五、平台 shell 4 要素成熟度

| 要素 | 状态 | 完成度 | 举证 |
|---|---|---|---|
| 登录态 | ❌ | 0% | 顶栏硬编码 "Demo·本地运行"，无 session/cookie/token 逻辑 |
| RBAC 权限分流 | ❌ | 0% | 无角色定义，无 route-guard |
| 站内 IM | ❌ | 0% | 无 `/chat` 路由，无 WebSocket 客户端 |
| 任务看板 / 通知中心 | ❌ | 0% | 无 Task 模型，无通知组件 |

**严峻结论**：unified platform pivot 的 4 要素**全部未启动**。

---

## 六、与后端契约匹配度

### 前端"演示优先"的 3 个 Agent
Agent5 合规 / Agent2 风控 / Agent4 预警——UI 完整但后端 stub。前端 CC 为了演示流程提前假设了 endpoint 命名和字段结构，后端补齐时需**反向适配前端契约**，不能自定。

### 对 5 路子 CC 启动的影响
- Agent5 / Agent2 / Agent4 子 CC 的 Phase 1 必须先读前端实际调用的 endpoint 和字段，以前端为准补后端
- Agent3 / Agent1 后端更成熟，前端契约已稳定，风险较低

---

## 七、给主 CLI 的 3 个待决点

1. **Agent5 / 2 / 4 后端补齐 vs 登录优先？**
   前端预设的 endpoint 很多，但 platform shell 4 要素全 0%。要先补齐 3 个 Agent 后端让演示流畅，还是先启动平台 shell 补 RBAC / IM / 看板？建议 **"后端补齐 + 登录 shell 并行"**——后端由 5 路子 CC 做，登录 shell 由前端 CC 做。

2. **登录 + RBAC 是 AppShell 统一实现还是逐 Agent？**
   建议**统一实现**（一套 session middleware + route-guard），各 Agent 只消费 `useUser()` 返回的 user_id / role，零侵入。

3. **站内 IM 用 WebSocket 还是 REST poll？**
   建议**先 REST poll（5s 间隔）验证产品形态**，确认用户真用起来后再升级 WebSocket 减延迟。避免早优化。

---

## 八、对 Phase 1 onboarding prompt 的影响

- 5 份 onboarding prompt 里的 API endpoint 命名必须**对齐前端已调用的实际字符串**（见 §3.2 Top-5 脱节点）
- Agent5 / 2 / 4 子 CC 在 Task 1 完成后，**必须先做"前端调用清单反抽"**——跑一遍前端 fetch 调用清单，与自己规划的 endpoint 对齐，有冲突立即同步主 CLI
- Agent3 / 1 子 CC 更自由，可按 DoD 和 GLOBAL.md §六标准流程
- 字段命名不一致（amount / severity）要由主 CLI 发 `docs/contracts/field-naming.md` 统一契约

---

**文档维护人**：主 CLI
**下次复核**：UI CC 完工 merge 后，或启动 Phase 2 之前
