# Product Hardening Phase 1 Batch 1 · 4 Worker Kickoff Prompts

> **定位**：4 条 GO 指令，每条粘到对应 worker CLI（worker resume 汇报完后）。
> **生效前提**：`PRODUCT-HARDENING-BATCH-1-DISPATCHED` 已落 main（见本 commit）。
> **主 CLI 仲裁**：任何 worker 开 Q-NNN / RFC，主 CLI 回 A-NNN 后 worker 才能继续。

---

## ① code-urgent

```
GO。按 onboarding 执行：

1. 先 commit 一条 doc-only commit，trailer:
   Signal: PRODUCT-HARDENING-BATCH-1-ACK
2. 按 Task 0 → A → B → C 顺序推进：
   - 0: archive workspace 归位（cherry-pick from feat/agent6-dialog-shell）→ Signal: ARCHIVE-WORKSPACE-REHOMED
   - A: Agent3 接入 financial_analyzer（§3.1 反模式修复）→ Signal: CREDIT-FINANCIAL-ANALYZER-INTEGRATED
   - B: 5 Agent 补占位符 QC blocker（shared/qc/placeholder_guard.py）→ Signal: QC-PLACEHOLDER-GUARD-5AGENTS-DONE
   - C: agent_riskctrl/api.py + agent_alert/api.py 新建 + api_server.py 挂载 → Signal: AGENT2-AGENT4-API-WIRED
3. 全部完成后 commit:
   Signal: READY-FOR-CODE-URGENT-REVIEW

红线：不动 financial_analyzer / Agent6 / web lib/store/shell / 其他 worker 地盘。
不做架构重构（那是 code-arch）。
每 Task 独立 commit，不攒。
开干。
```

---

## ② code-arch

```
GO。按 onboarding 执行：

1. 先 commit doc-only，trailer:
   Signal: PRODUCT-HARDENING-BATCH-1-ACK
2. Task A → B → C 顺序：
   - A: 5 Agent 工具域按 §3.2 重拆（命名 <域>_<动作>）→ Signal: TOOL-DOMAIN-SPLIT-DONE
   - B: 5 Agent Evidence 三阶段协议（shared/evidence/protocol.py + 5 个继承实现）→ Signal: EVIDENCE-PROTOCOL-5AGENTS-DONE
   - C: scripts/feedback_to_fewshot.py + inject_fewshot_to_prompts.py（§6 第 4 环自动化）→ Signal: FEEDBACK-FEWSHOT-PIPELINE-DONE
3. 全 Task 完成：
   Signal: READY-FOR-CODE-ARCH-REVIEW

红线：不动 Agent6 行为 / financial_analyzer / quality_scorer / truth_fill / web 前端。
不抢 code-urgent 的活（§3.1 修复、占位符 QC、Agent2/4 api.py）。
每 Task 独立 commit。
开干。
```

---

## ③ data-foundation

```
GO。按 onboarding 执行：

1. 先 commit doc-only，trailer:
   Signal: PRODUCT-HARDENING-BATCH-1-ACK
2. Task A → B → C 顺序：
   - A: data/mock/README.md + wide-base.yaml + deep-pillar.yaml schema → Signal: DATA-SCHEMA-DONE
   - B: 宽基 100 家 YAML（8 行业分布 + 难度 20/50/20/10，参考 A 股年报 + 天眼查模板）→ Signal: DATA-WIDE-100-DONE
   - C: 深柱 15 家名单 + 15 份埋坑清单模板（交 PM 填）→ Signal: DATA-DEEP-SHORTLIST-DONE
3. 全 Task 完成：
   Signal: READY-FOR-DATA-FOUNDATION-B1-REVIEW

必守：反结果导向 4 原则（盲测 / 难度分层 / 真实锚定 / 脱敏再造）。
简单档 ≤20%，违者反工。PM 抽检 20%，真度 < 80% 反工。
不做深柱完整材料包（那是 Batch 2）。
每 Task 独立 commit。
开干。
```

---

## ④ evaluation

```
GO。按 onboarding 执行：

1. 先 commit doc-only，trailer:
   Signal: PRODUCT-HARDENING-BATCH-1-ACK
2. Task A → B → C 顺序：
   - A: 6 × rubric YAML（5 通用 + 5 领域，每条带 method/baseline_target/blocker_threshold）→ Signal: EVAL-RUBRIC-YAML-6AGENT-DONE
   - B: evaluation/base_evaluator.py + 6 adapter + CLI（RFC 20260418-evaluation-runner.md 蓝图）→ Signal: EVAL-RUNNER-BASE-DONE
   - C: 首轮基线 JSON + markdown（用现有 samples/ + customer/，不等 data-foundation B1）→ Signal: EVAL-BASELINE-FIRST-RUN
3. 全 Task 完成：
   Signal: READY-FOR-EVALUATION-B1-REVIEW

警示：首轮基线会偏乐观（mock 太简单，见 Q-023 PM 判断）。本轮作为"起点参照"，不作为产品达标证据。B2 用 data-foundation B2 真脏数据重跑。
红线：不改 v16_pipeline.py / agent_*/ 业务代码 / data/mock/。
需要 Agent 输出接口配合时开 RFC。
每 Task 独立 commit。
开干。
```

---

## 新主 CLI 使用说明

1. 用户双击 `C:\Users\Mr.S\Desktop\mesh-credit-agents.bat`（如已配 4 新 worker）起 worker tabs，或用户自己 cd 到各 worktree 手起
2. 每个 worker tab 粘 "读 AGENT_IDENTITY.md ..." 万能 resume 指令
3. worker 汇报 "Resume 完成" 后，主 CLI 把本文件对应小节的 GO prompt 粘给用户 / 或指示用户按次序粘贴
4. 进度追踪：`py C:/Users/Mr.S/.claude/skills/multi-cli-mesh/scripts/mesh_status.py`

**预计收齐 4 ACK 时间**：约 15-30 分钟（取决于 worker resume 速度）
**预计收齐 4 READY 时间**：约 7-10 天（最长是 code-arch，含 Evidence 三阶段 L 工时）
