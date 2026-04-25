# Phase 3-Final · 轨 7 · 合规文档 + 模型卡 / 演示脚本 + Agent1 信号时间线 UI Onboarding

**状态**：Phase 3-Final GO（**主 CLI 本地代理（默认） · 或拆 doc worker · 与 Wave 1 并行写**）
**发布日期**：2026-04-25
**Signal 入口**：N/A（主 CLI 自代理 · 无 worker ACK · 拆 doc worker 时挂 `PHASE-3-FINAL-T7-ACK`）
**前置**：commit `4f2132e ORCHESTRATOR-HANDOFF-PHASE-3-FINAL-PLANNED` + Q-032 + 轨 1 agent6-unfreeze APPROVED merged（带 agent6 模型卡作模板基线）
**参照决策**：`docs/handoff/decisions-log.md` Q-032 + `docs/handoff/session-2026-04-25-phase-3-final-handoff.md` §4.7 + `docs/scorecard/dod-current-status-2026-04-24.md` §2.3.3 L2-15 + §2.4 L3-11/L3-12 + §2.2 L1-3 Agent1
**Final commit signal**：`READY-FOR-DOCS-COMPLIANCE-REVIEW`（subagent pre-review）

---

## 1. 背景与目标

剩余 docs gap + 一个前端组件兜底：

| 条 | 内容 | 状态 | 本轨产 |
|---|---|---|---|
| L2-15 | 客户数据本地处理 · 禁境外 API · 文档化 | 🟡 代码层境内 · 文档未明文 | Task A |
| L3-11 | 6 Agent 模型卡（agent6 在 agent6 branch 由轨 1 带） | 🔴 5/6 缺 | Task B |
| L3-12 | 6 Agent 演示脚本（agent6 在 agent6 branch 由轨 1 带） | 🔴 5/6 缺 | Task C |
| L1-3 | Agent1 信号时间线前端组件 | 🔴 7 frozen branch 不含 · 需新写 | Task D |

**硬边界**：
- Task A/B/C：纯文档 · `docs/` 域内 · 不动代码
- Task D：仅新建 `web/src/app/archive/channel/_components/SignalTimeline.tsx` ≤ 250 行 · 消费 Agent1 SSE 已有 `signal_timeline` 字段 · **不动后端 / 不改 store / 不偏 §7 spec**

---

## 2. Task 清单

### Task A · L2-15 客户数据本地处理文档

**目标**：`docs/data-classification.md`（或 `docs/compliance/data-localization.md` · 看 agent6 branch 已带 docs/compliance/ 是否覆盖 · 不重复）

**内容**：
1. 数据分级 · 已由轨 1 agent6 branch `e12805c` 带回（`L2-14 数据分级标签`） · 本 Task 在其基础上补"客户数据本地处理"专章
2. 境内 / 境外 API 清单：
   - **境内**（生产用）：DeepSeek 中国区 / Tavily（特定 endpoint） / 国家企业信用信息公示系统 / 央行 / 银保监公开 API
   - **境外**（禁用）：OpenAI / Anthropic 公网 endpoint / 任何 IP 在境外的 LLM API
3. Code 层落地证据：grep `DeepSeek` / `tavily` 配置位置 + 域名白名单 ref
4. 例外申请流程（如客户场景需用境外 · 需走的 RFC + 审批）
5. 数据传输加密要求（HTTPS / TLS 1.2+ / 内网 mTLS）

**约束**：
- 与 agent6 branch 已带 `docs/compliance/partners-register.md` 不重复 · 互相 ref
- 法律法规引用真实条款（《数据安全法》《个人信息保护法》《关键信息基础设施安全保护条例》）
- 不臆造监管条文 · 引用国家网信办 / 央行 / 银保监公开发布的 spec

---

### Task B · 5 Agent 模型卡（agent1/2/3/4/5）

**目标**：每个 Agent 一份 `docs/model_cards/agent{1,2,3,4,5}.md` · agent6 由轨 1 带回作模板基线。

**模板**（按 agent6 branch `33d6295 docs(agent6): model card + demo script` 实现 · 轨 1 合后 ref）：

```markdown
# Model Card · Agent{N} · {功能名}

## 1. 算法概览
- 核心模型 / 算法范式（确定性 vs 概率性 vs 混合）
- 关键依赖（LLM / 规则引擎 / 评分模型）
- 决策框架（Agent3 用四维评分 / Agent4 用双路交叉等）

## 2. 输入字段
- 必填字段（schema + 含义 + 示例）
- 可选字段
- 字段约束（取值范围 / 枚举 / 校验）

## 3. 输出字段
- 主输出（结构 + 含义）
- 副输出（建议 / 解释 / reason_codes）
- SSE 流式 chunk 协议（如有）

## 4. 评估指标
- 引 Batch 2 baseline `evaluation/baselines/2026-04-26-real-run.md` 中本 Agent 段
- 5-10 关键指标 · 当前数值 + 目标 + blocker 阈值
- 知名缺陷 / pending 指标

## 5. 局限
- 不解决的场景
- 已知失败 mode（如 template_leakage / FP > X）
- 不适用范围

## 6. 对标
- 国内：壹账通 / 同盾 / 百融 / 微众
- 国际：FICO / Moody's / Experian
- 对比维度（覆盖度 / 解释性 / 部署门槛 / 数据要求）
```

**Agent 维度备注**：
- **Agent1 获客**：核心 = SearchProvider + lookalike 评分 · 对标国内拉新 SaaS / 国际 ZoomInfo
- **Agent2 风控**：核心 = DSL 生成 + 回测（KS / FPR） · 对标 SAS / FICO
- **Agent3 授信**：核心 = 四维评分 + 红线 · 对标传统打分卡 + LLM 增强
- **Agent4 预警**：核心 = 双路交叉 + 红黄绿分级 · 对标同盾贷后预警
- **Agent5 合规**：核心 = 政策事件驱动 + 业务矩阵冲突 · 对标 RegTech 国内案例（金融壹账通 / 蚂蚁链法务）

**约束**：
- 引用必须真实（评估数据引 baseline · 对标公司引公开报告）
- 不臆造能力（若某指标 pending · 标 pending 不写虚高数值）
- 字数 200-400 / 节 · 不超长

---

### Task C · 5 Agent 演示脚本（agent1/2/3/4/5）

**目标**：每个 Agent 一份 `docs/demo_script/agent{1,2,3,4,5}.md` · agent6 由轨 1 带回作模板基线。

**模板**：

```markdown
# Demo Script · Agent{N} · 30 分钟标准演示

## 1. 演示前准备（5 min）
- 启动检查（健康端点 / mock 数据 / 主题选择）
- 客户角色对应（客户经理 / 审贷员 / 合规官 / 风险经理）
- 浏览器 / 主题 / 屏幕分辨率建议

## 2. 演示流程（20 min）
### Step 1 · 入口（2 min）
- 切到 /archive/{agent} workspace
- 点击 Float-badge 切主题（演示 4 主题）
- 解释为什么选这个 Agent

### Step 2 · 核心交互（10 min）
- 主路径 1：{触发 → 中间态 → 结果}
  - 话术 + 客户视角解读
- 主路径 2：{第二条业务路径}
- 跨 Agent 联动（如 L1-11 button）

### Step 3 · 证据链 + 导出（5 min）
- EvidenceTrail 点开 · 30 秒追到原材料
- reason_codes 解读
- 导出 xlsx / docx · 文件结构展示

### Step 4 · 局限 + Roadmap（3 min）
- 当前 pending 指标坦白
- 不在场景的兜底（"未能自动填写"）
- Phase 4 / Phase 5 路线（按客户兴趣展开）

## 3. Q&A 预案（5 min）
- TOP 5 客户高频问题 + 标准答案
- "幻觉怎么防" / "数据怎么进" / "评估怎么对标银行内部"
- "上线 / 部署 / 培训成本" 估算
```

**约束**：
- 话术真人化（不用"接下来我将展示"等机器感强的句式）
- 每个 step 含"客户视角"一句解读
- Q&A 答案对标真实银行场景 · 不空话

---

### Task D · Agent1 信号时间线前端组件

**目标**：新建 `web/src/app/archive/channel/_components/SignalTimeline.tsx` · ≤ 250 行 · 消费 Agent1 SSE 的 `signal_timeline` 字段。

**判断（先做）**：
1. grep 7 frozen branch 是否真不含 SignalTimeline（`git log feat/{shell-free-drag,canvas-mode-toggle,alert-codex-fusion,compliance-codex-fusion,credit-mock-endpoint,chat-wechat-style,agent-workspaces-v2}` --grep="SignalTimeline\|signal-timeline\|signal_timeline"）
2. 若**有任一 branch 含**：本轨**跳过 Task D** · final body 写明跳过理由 + 引用 branch SHA
3. 若**全无**：本轨新写

**组件 spec**：
- 入口：`/archive/channel` workspace 内嵌
- 数据源：消费 Agent1 SSE `event: signal_timeline { type, ts, payload }` chunks
- 视觉：竖向时间线 · 每信号一节点 · 信号类型 icon（工商变更 / 司法 / 招投标 / 招聘 / 媒体）+ 时间戳 + payload 摘要
- 交互：点击节点展开详情 + 跳转原材料 URL
- 主题适配：4 主题 token 化（`--t-channel` 青绿色 + `--g0..--g7` 渐变）
- 动画：节点 stagger rise（参照 §7 `bar-in` / `case-in` 现有动画 · 不引入新 keyframe）
- 测试：附 1 个 spec `web/tests/signal-timeline.spec.ts` · 渲染 / 数据流 / 主题切换 3 case

**约束**：
- 只动 `web/src/app/archive/channel/_components/SignalTimeline.tsx`（新建）+ `web/tests/signal-timeline.spec.ts`（新建）
- 不动 channel workspace 主页面（`ChannelWorkspace.tsx` 加 `<SignalTimeline />` 一行 import + 一行挂载即可）
- 不动 store · 不动 SSE handler · 不动后端
- §7 spec 严守（4 主题 / 圆角 / 字体栈 / 动画 token）

---

## 3. 验收硬指标（T7-1 ~ T7-10 · 10 项）

| # | 指标 | 阈值 | 判定 |
|---|---|---|---|
| T7-1 | L2-15 docs 落盘 | `docs/data-classification.md` 或 `docs/compliance/data-localization.md` 存在 + 含境内/境外 API 清单 + 法规引用 | grep |
| T7-2 | 5 Agent 模型卡齐 | `ls docs/model_cards/agent{1,2,3,4,5}.md` 全 5 份 + 6 节齐 | ls + grep |
| T7-3 | 模型卡引 baseline 数据 | 每份 model card 含 evaluation/baselines/ 引用 + 真实数值 · 不空话 | grep |
| T7-4 | 5 Agent 演示脚本齐 | `ls docs/demo_script/agent{1,2,3,4,5}.md` 全 5 份 + 30 min 流程齐 | ls + grep |
| T7-5 | 演示脚本含 Q&A 预案 | 每份 demo_script 含 ≥ 5 条 Q&A | grep |
| T7-6 | SignalTimeline 决策 | 7 branch grep 结果 + 写或跳过决策 + 理由（1 句） | body |
| T7-7 | SignalTimeline 实装（如未跳过） | 组件 + spec 落盘 + tsc 0 error | ls + tsc |
| T7-8 | 红区 0 漂移 | git diff name-only 限于 `docs/` + `web/src/app/archive/channel/_components/SignalTimeline.tsx` + `web/src/app/archive/channel/_components/ChannelWorkspace.tsx`（仅挂载行）+ `web/tests/signal-timeline.spec.ts` | git diff |
| T7-9 | 解 DoD 自检 | final body L2-15 ✓ / L3-11(5) ✓ / L3-12(5) ✓ / L1-3 Agent1 ✓-or-skipped | body |
| T7-10 | 法规引用真实 | grep 数据安全法 / 个人信息保护法 / 关键信息基础设施 + 央行 / 银保监条款序号 | grep |

---

## 4. 红线

- ❌ **不动后端** · 不动 SSE handler · 不动 store
- ❌ **不动其他 5 Agent workspace**（轨 4 frontend-integration scope）
- ❌ **不动红区 3 文件 + web/src/lib/store/***
- ❌ **臆造法规条款** · 必须引真实条文（《数据安全法》第 X 条 + 央行 X 号文具体序号）
- ❌ **臆造 baseline 数值** · 必须引 `evaluation/baselines/` 真实 md
- ❌ **臆造对标公司能力** · 引公开报告 / 公司官网
- ❌ **不 git push**
- ✅ Task D 先 grep 7 branch 再决策 · 不重复造轮子
- ✅ 模型卡 / 演示脚本与 agent6 模板（轨 1 带）格式对齐
- ✅ Final body 含 4 task 完成清单 + 解 DoD 4 项自检 + 红区漂移自检

---

## 5. 工期

- Task A · L2-15 文档（基于 agent6 branch 已带 docs/compliance/） · 0.5 天
- Task B · 5 Agent 模型卡 · 1 天（每份 ~1.5h）
- Task C · 5 Agent 演示脚本 · 1 天（每份 ~1.5h）
- Task D · SignalTimeline 决策 + 实装（如需） · 0.5 天
- Final body · 0.25 天
- 合计 **2-3 天**（主 CLI 代理 · 与 Wave 1 并行 · Task A 等轨 1 合后启动 · Task B/C/D 立即可启）
