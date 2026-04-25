# DoD 现状 Gap 映射 · 2026-04-24

**版本**：v1.0 · 2026-04-24
**基线**：Batch 1 Product Hardening 3/4 合流（code-urgent `28d1037` + code-arch `53f3eca` + evaluation `069f589` → `chore/l0-infra`）· data-foundation v2 返工中
**DoD 源**：`docs/scorecard/definition-of-done.md` v1.0（2026-04-17）
**用途**：为 Batch 2 规划提供 gap 映射 + 优先级基线·供主 CLI / PM 决策

---

## 1. L0-L4 现状快照

| 层级 | 问题 | 整体状态 | 已达标 Agent | gap 最大 Agent |
|---|---|---|---|---|
| **L0 工程基础** | 能运行吗？ | 🟡 65% | Agent6 | Agent2 · Agent4 之前 api.py 缺·Batch 1 已修 |
| **L1 Demo 完整度** | 客户一眼能看懂吗？ | 🟡 55% | Agent6 · Agent3 基本就绪 | Agent2 · Agent5 前端可视化薄 |
| **L2 金融合规** | 合规官能放行吗？ | 🟡 60% | Agent6 | 5 个其他 Agent 都缺 reason_codes 字典文件 |
| **L3 客户 POC** | 真实数据跑得出合理结果吗？ | 🔴 30% | 无 | 全部·卡在 data-foundation v2 真脏数据尚未落地 |
| **L4 商业交付** | 能签合同吗？ | 🔴 10% | 无 | 全部·非本阶段目标 |

**一句话 verdict**：Agent6 达到 L2 成熟度 · Agent3 接近 L2 · 其他 4 Agent 还在 L1→L2 过渡 · 全体卡 L3 数据门槛 · L4 推到商务阶段再说。

---

## 2. Batch 1 覆盖矩阵（逐条标）

### 2.1 L0 工程基础（14 条）

| # | 条目 | Batch 1 前 | code-urgent 28d1037 | code-arch 53f3eca | evaluation 069f589 | data-found v2 预期 | Batch 1 后 |
|---|---|---|---|---|---|---|---|
| L0-1 | lint + type check | 🟡 | — | — | — | — | 🟡（未强 CI） |
| L0-2 | 单测覆盖率 ≥70% | 🔴 | — | 🟡 工具域重拆带测试 | 🟡 adapter 测试 | — | 🟡 |
| L0-3 | 无硬编 key | 🟢 | — | — | — | — | 🟢 |
| L0-4 | 外部调用超时+降级 | 🟡 | — | ✅ Evidence 三阶段协议强化 | — | — | 🟢 |
| L0-5 | 无裸 except | 🟡 | — | ✅ 工具域重拆顺便清 | — | — | 🟢 |
| L0-6 | 日志不打敏感 | 🟡 | — | — | — | — | 🟡（需审计） |
| L0-7 | .env.example 齐 | 🟢 | — | — | — | — | 🟢 |
| L0-8 | requirements 版本锁 | 🟢 | — | — | — | — | 🟢 |
| L0-9 | CHANGELOG / commit 可追溯 | 🟢 | ✅ 3 worker signal commit 全齐 | ✅ | ✅ | — | 🟢 |
| L0-10 | 单行启动（`py /tmp/start_uvicorn.py`） | 🟢 | ✅ Agent2/4 api.py 补齐后端到端可跑 | — | — | — | 🟢 |
| L0-11 | `/api/{agent}/health` 返 200 | 🟡 Agent2/4 缺 | ✅ 新建 api.py | — | — | — | 🟢 |
| L0-12 | P95 延时 ≤1s | 🟡 | — | — | — | — | 🟡（未 load test） |
| L0-13 | 运维文档起/停/监/回 | 🔴 | — | — | — | — | 🔴（Batch 2 候选） |
| L0-14 | 新模块归属业务域 | 🟡 | ✅ Task 0 archive workspace 归位 | ✅ 5 Agent 工具域 §3.2 重拆 | — | — | 🟢 |

**L0 小结**：Batch 1 把 L0-11 / L0-14 / L0-4 / L0-5 / L0-10 从 🟡🔴 推到 🟢 · 剩下 L0-13 运维文档 + L0-12 P95 load test 是 Batch 2 候选 · L0-2 单测覆盖率全仓 ≥70% 是中远期目标。

### 2.2 L1 Demo 完整度（12 条）

| # | 条目 | Batch 1 前 | Batch 1 后 | Batch 2 需补 |
|---|---|---|---|---|
| L1-1 | 预置场景 ≥2/Agent | 🟡 | 🟡 | 🟡 等真 mock 灌场景 |
| L1-2 | 首屏 3 区块·非纯 chatbot | 🟢 | 🟢 | — |
| L1-3 | 核心可视化 ≥1 | 🟡 | 🟡 | 🔴 Agent1 信号时间线 · Agent4 红黄绿盘 · Agent2 KS 图表 · Agent5 政策矩阵 UI 待建 |
| L1-4 | 导出 ≥1 种 | 🟡 | 🟡 | 🟡 Agent3 决策书 docx · Agent5 合规报告 docx · Agent4 台账 xlsx · Agent1 候选 xlsx · Agent2 回测 pdf 全待补 |
| L1-5 | 30s 内中间态 | 🟢 | 🟢 | — |
| L1-6 | 跨机访问 demo.liuye.me 跑通 | 🟢 | 🟢 | — |
| L1-7 | 视觉符合 §7 ink 主题 | 🟢 | 🟢 | — |
| L1-8 | 文案中文·无 jargon | 🟢 | 🟢 | — |
| L1-9 | 降级明确提示 | 🟡 | 🟢（code-arch 强化） | — |
| L1-10 | Mock 独立可跑 | 🟢 | 🟢 | — |
| L1-11 | Agent6 handoff → Agent3 预填 | 🟡 | ✅（code-urgent Agent3 接 financial_analyzer 后联动通） | — |
| L1-12 | Demo 数据稳定可复现 | 🟡 | 🟡 | 🟢 等 evaluation Batch 2 真脏数据验证 |

**L1 小结**：核心短板是 **L1-3 可视化** + **L1-4 导出**·5 个 Agent（除 Agent6）的前端证据链展示 / 图表 / 导出全要补·这是 **Batch 2 最大价值洼地**。

### 2.3 L2 金融合规（15 条 · 最硬层）

#### 2.3.1 零幻觉与证据链（6 条）

| # | 条目 | Agent6 | Agent3 | Agent1 | Agent4 | Agent5 | Agent2 | Batch 1 关键动作 |
|---|---|---|---|---|---|---|---|---|
| L2-1 | 证据率 ≥0.95 | 🟢 | 🟢 | 🟡 | 🟡 | 🟡 | 🔴 | code-arch Evidence 三阶段协议推 5 Agent |
| L2-2 | 幻觉率 ≤0.01 | 🟢 | 🟡 | 🟡 | 🟡 | 🟡 | 🔴 | evaluation baseline 跑出首轮数（虚高·等 Batch 2 真数据校） |
| L2-3 | 确定性走 Python | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | code-urgent Agent3 接 `financial_analyzer` · §3.1 全通过 |
| L2-4 | QC Blocker 终审 | 🟢 | 🟡 | 🟡 | 🟡 | 🟡 | 🔴 | code-urgent Task B QC 占位符 5 Agent 补齐 |
| L2-5 | 占位符 0 容忍 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟡 | code-urgent Task B · Agent2 待补 |
| L2-6 | 30 秒追到原材料 | 🟢 | 🟡 | 🟡 | 🔴 | 🔴 | 🔴 | 前端证据点击溯源 UI 未建 |

#### 2.3.2 可解释性 · Reason Code（3 条 · 对标 FCRA AAN）

| # | 条目 | 状态 | Batch 1 | Batch 2 需求 |
|---|---|---|---|---|
| L2-7 | Top-3~5 reason_codes | 🟡 Agent3 后端齐 · 前端待渲染 | — | 🔴 Agent4/5 reason_codes 字典文件缺 |
| L2-8 | reason_codes 字典固定可枚举 | 🔴 `docs/reason_codes/{agent}.yaml` 全部缺 | — | 🔴 Batch 2 Top-3 候选 |
| L2-9 | 拒绝结论给"为什么+怎么改" | 🟡 | — | 🟡 UI 渲染待建 |

#### 2.3.3 人在回路 · 数据治理（6 条）

| # | 条目 | 状态 | Batch 1 | Batch 2 需求 |
|---|---|---|---|---|
| L2-10 | 输出标"建议"不"决定" | 🟢 前端文案已达标 | — | — |
| L2-11 | 审批人/复核人电子签章位 | 🟡 占位存在·真流程未打通 | — | 🟡 Batch 2+ |
| L2-12 | 审计日志落盘 | 🔴 `data/audit/*.jsonl` 未建 | — | 🔴 Batch 2 必补 |
| L2-13 | 合作机构清单文档化 | 🔴 `docs/partners/third-party-services.md` 缺 | — | 🔴 Batch 2 必补（银行采购要） |
| L2-14 | 数据分级标签 | 🔴 `docs/data-classification.md` 缺 | — | 🔴 Batch 2 必补（监管硬要求） |
| L2-15 | 客户数据本地处理·禁境外 API | 🟢 代码层 DeepSeek 境内已选·文档未明文 | — | 🟡 文档化 |

**L2 小结**：零幻觉与证据链**后端基本齐**·前端溯源点击 UI 待建·**reason_codes 字典 3 个 Agent 缺 + 审计日志 + 合作机构清单 + 数据分级 4 份合规文档必补**·这些是 L3 POC 前的硬门槛。

### 2.4 L3 客户 POC（12 条）

#### 2.4.1 评估基线（4 条）

| # | 条目 | Batch 1 前 | Batch 1 后 | 备注 |
|---|---|---|---|---|
| L3-1 | rubric YAML + 结果落盘 | 🔴 | 🟢（evaluation 069f589 · 6 × YAML + 首轮 baseline） | **但基线虚高**·等 Batch 2 真脏数据重跑 |
| L3-2 | 通用指标达标 | 🔴 | 🟡 Agent6 部分达 · 其他 5 Agent 基线暂估 | 等 Batch 2 真数据校 |
| L3-3 | 领域指标达标 | 🔴 | 🟡 | 等 Batch 2 真数据校 |
| L3-4 | 基线回归 | 🔴 | 🔴 | CI 对比脚本 Batch 2+ |

#### 2.4.2 工程能力（4 条）

| # | 条目 | 状态 | Batch 1 后 | Batch 2 需求 |
|---|---|---|---|---|
| L3-5 | P95 首字延时 ≤1.5s | 🟡 未系统 load test | — | 🟡 Batch 2 跑一轮 |
| L3-6 | Mock/Web 双模靠配置 | 🟢 SearchProvider 抽象早就有 | — | — |
| L3-7 | 多客户数据隔离 | 🟡 session_id 有·未压测验 | — | 🟡 |
| L3-8 | `/api/feedback` + `data/feedback/` | 🟡 端点有·落盘验过 | 🟢 code-arch 第 4 环 `feedback_to_fewshot` 脚本（飞轮闭环） | — |

#### 2.4.3 E2E 验证（4 条）

| # | 条目 | 状态 | Batch 2 需求 |
|---|---|---|---|
| L3-9 | Playwright E2E × 3 路径 | 🔴 | 🔴 必补 |
| L3-10 | 3 张关键截屏留证 | 🔴 | 🔴 必补 |
| L3-11 | 模型卡片 `docs/model_cards/` | 🔴 | 🔴 必补（银行 RFP 要） |
| L3-12 | 演示脚本 `docs/demo_script/` | 🟡 本 runbook 是雏形 | 🟡 每 Agent 拆一份 |

**L3 小结**：**L3 是 Batch 1 后最大 gap 层**·评估基线跑出来了但虚高·真 POC 需要 data-foundation v2 落地后重跑。E2E + 模型卡片 + 演示脚本这 4 条（L3-9~12）是 Batch 2 必补项·银行 POC 邀标会直接要。

### 2.5 L4 商业交付（8 条 · 按需启用）

全体 🔴·非 Batch 1/2 目标·留给商务阶段。

---

## 3. Batch 2 候选优先级

### 🟢 高 ROI（第一梯队 · Batch 2 必选）

| # | 项目 | 对应 DoD | 为什么紧急 | 预估工作量 |
|---|---|---|---|---|
| 1 | **6 Agent 证据链前端化**（溯源点击 / 高亮 / 悬浮卡） | L2-1 / L2-6 | 后端齐了·前端不展示 = 演示效果 50% · PM 反复强调 | 1 worker × 2-3 天 |
| 2 | **Data Phase 1 深柱 5 家真实材料包**（中锐形态） | L3-1~3 | 评估基线虚高·没真数据等于没 POC 门槛 | data-foundation v2 已在跑 |
| 3 | **reason_codes 字典 × 3 Agent**（3/4/5） | L2-7 / L2-8 | 合规硬指标 · Agent3 有 · 3/4/5 缺·对标 FCRA AAN | 1 worker × 1-2 天 |
| 4 | **前端可视化补齐**（Agent1 信号时间线 · Agent4 红黄绿盘 · Agent2 KS 图 · Agent5 政策矩阵） | L1-3 | 演示核心场景缺可视化·客户一眼看不懂 | 1 worker × 3-5 天 |
| 5 | **evaluation Batch 2 真脏数据重跑基线** | L3-1~4 | Batch 1 基线暂估 · 等 Phase 1 落地后必须重跑对比 gap | 1 worker × 1 天（脚本跑）|

### 🟡 中 ROI（第二梯队 · Batch 2 选做）

| # | 项目 | 对应 DoD | 触发条件 |
|---|---|---|---|
| 6 | **合作机构清单 + 数据分级 + 客户数据本地化**三份文档 | L2-13 / L2-14 / L2-15 | 银行合规部 RFP 要看·POC 前必有 |
| 7 | **审计日志 `data/audit/*.jsonl`** | L2-12 | 合规硬要求·但 copilot 阶段容忍延后 |
| 8 | **导出能力补齐**（Agent3 docx · Agent5 docx · Agent4 xlsx · Agent1 xlsx · Agent2 pdf） | L1-4 | 客户带走物料价值 |
| 9 | **模型卡片 × 6 Agent**（`docs/model_cards/`） | L3-11 | 银行 AI 算法披露指南要求·POC 前必有 |
| 10 | **Playwright E2E × 3 关键路径** | L3-9 | 银行科技部 POC 会要看 CI |

### 🔴 低 ROI（第三梯队 · Batch 3+）

| # | 项目 | 对应 DoD | 推后理由 |
|---|---|---|---|
| 11 | L0-12 P95 load test | L0-12 | 当前单机规模不急 |
| 12 | L0-13 运维文档 | L0-13 | POC 阶段手工运维可接受 |
| 13 | L0-2 单测覆盖 ≥70% 全仓 | L0-2 | 工程债·不卡演示 |
| 14 | L2-11 真实审批流 | L2-11 | copilot 阶段电子签占位即可 |
| 15 | L4 商业交付全部 8 条 | L4-全 | 商务阶段启用 |

---

## 4. 依赖链（Batch 2 哪些 item 等 Phase 1 先落地）

### 4.1 硬依赖（Phase 1 data-foundation v2 不落地·无法启动）

| Batch 2 item | 为什么依赖 Phase 1 |
|---|---|
| #2 Data Phase 1 深柱 5 家 | **就是 Phase 1 本身** |
| #5 evaluation Batch 2 真脏数据重跑 | 需要 deep-pillar/DP001~005 真材料 + channel-kb / compliance-kb 真 mock |
| L3-2 / L3-3 通用/领域指标达标 | 虚高基线不能当达标证据 |

### 4.2 软依赖（Phase 1 未落地可并行启动·但 demo 效果打折）

| Batch 2 item | Phase 1 影响 |
|---|---|
| #1 证据链前端化 | UI 逻辑可先写·真 mock 来了灌数据即可 |
| #3 reason_codes 字典 | 字典可先按 FCRA 结构先起·后续灌真实分布 |
| #4 前端可视化补齐 | 组件可先按 mock 数据 shape 写·真 mock 来了替换 data props |
| #8 导出能力补齐 | 模板可先出·数据后填 |
| #9 模型卡片 | 算法部分可先写·准确率等真脏数据基线跑完补 |

### 4.3 无依赖（Phase 1 不影响·可独立启动）

| Batch 2 item | 备注 |
|---|---|
| #6 三份合规文档（合作机构 / 数据分级 / 本地化） | 纯文档类 · 主 CLI 或 doc worker 都能做 |
| #7 审计日志 jsonl | 后端埋点 · 不依赖数据真度 |
| #10 Playwright E2E | 测试脚本 · 跑 demo 流程即可 |
| #11~#14 低 ROI 工程债 | 独立 |

---

## 5. Batch 2 启动建议

### 5.1 推荐组合（等 Phase 1 落地后启动）

- **data-Batch2**（延续 data-foundation worker · Phase 1 完成后直接接 Phase 2）：#2 深柱 5 家真材料包
- **eval-Batch2**（evaluation worker · 等 data-Batch2 落地）：#5 真脏数据重跑基线 + #9 模型卡片草稿
- **frontend-evidence worker**（新开）：#1 证据链前端化 + #4 前端可视化补齐·并行 data 等待期即可开工
- **code-compliance worker**（新开 · 可与 frontend 并行）：#3 reason_codes 字典 + #6 三份合规文档 + #7 审计日志

**4 worker 并行拓扑**（对标 Batch 1 四轨经验）·mesh 撑得住。

### 5.2 启动时间窗

- **Phase 1 落地预估**：data-foundation v2 返工 + v2 kickoff 已下发·1 周内预期 READY-FOR-DATA-FOUNDATION-B1-V2-REVIEW
- **Batch 2 启动时间**：Phase 1 APPROVE 后立即启 · 预估 2026-05 第一周
- **Batch 2 目标完成**：2026-05 第三周 · 对齐银行 Q2 末的 POC 窗口（若有客户需求）

### 5.3 关键依赖里程碑

```
2026-04-24 今天 · Batch 1 3/4 APPROVE
   ↓
2026-04-28~30 · Phase 1 data-foundation v2 APPROVE（关键闸门）
   ↓
2026-05-01 · Batch 2 正式启动（4 worker 并行）
   ↓
2026-05-15 · Batch 2 目标完成 · 准备客户 POC 邀标
   ↓
2026-06+ · L4 商业交付（按客户决定）
```

---

## 6. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| Phase 1 data-foundation v2 再返工 | 中 | 高·整体推后 1 周 | v2 kickoff 已约束 mock 形态矩阵 + §3.5 反结果导向 · 再返工概率已降 |
| Batch 2 frontend worker 视觉偏移 Letterpress | 低 | 中·需复盘 | CLAUDE.md §7 已明文 ink 主题 · mockup 锁定 rm-assistant-final-2026-04-19.html · 红线已立 |
| 银行合规文档（#6）未通过合规部审核 | 中 | 中·POC 延期 | 对齐金管总局 2025-10 助贷新规 + CAC AI 安全治理 2.0 · 引用监管文件明确 |
| 真脏数据基线 gap 过大（#5）Agent1/5 evidence_rate 跌破 0.90 | 中 | 高·触发停工红线 | Batch 2 首轮跑完对比 B1 虚高值·若 gap > 30% 立即根因分析·可能触发 Agent1/5 算法层重构 |

---

## 7. 与 DoD v1.0 的对齐审计

本文档所有 L0-L4 打分严格对应 `definition-of-done.md` 逐条·无擅自增改标准。

**DoD 版本升级触发点**（后续可能发生）：
- 监管新规（金管总局 / CAC / 人行新文件）
- 市场基线变化（壹账通 / 同盾 / 百融新产品发布）
- 重大事故后根因修订
- Phase 1 真实客户数据后·领域指标（L3 §7）可能需重新校准阈值

**下次复核**：2026-07-01（季度复核 · 与 DoD v1.0 §12 约定一致）

---

**文档更新**：Batch 2 启动时同步更新为 `dod-current-status-2026-05-XX.md` · 本文档存档。
