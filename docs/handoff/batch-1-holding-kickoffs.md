# Batch 1 Holding Task · 3 Worker Kickoff Prompts

> **定位**："Holding task" ≠ Batch 2。是 Batch 1 review warning 的 polish 补丁，给 code-urgent / code-arch / evaluation 3 worker 在 data-foundation v2 返工期间填档期用，防止窗口空转，同时严防越权启动 Batch 2 scope。
>
> **Batch 2 启动前提**：4 worker 全 APPROVE + Product Hardening Phase 1 全部落地 main。当前只有 Batch 1 过半（data-foundation 返工中），Batch 2 尚未立项。
>
> **粘发时机**：各 worker 只在收到主 CLI `PHASE-1-<X>-APPROVED` 合流 commit 落 main **之后**才粘对应 holding prompt；提前粘会撞 Batch 1 尾部评审流。worker 先 `git fetch origin main` 确认合流 sha 可见,再 ACK。
>
> **生效前提**：code-urgent / code-arch / evaluation 三条 Batch 1 分支已合流 main(commit 可 `git log origin/main --grep` 查)。data-foundation v2 返工期间三 worker 不领 Batch 2,只做本文档列出的 Holding task。

---

## ① code-urgent holding

```
HOLDING GO. Batch 1 CONDITIONAL-APPROVED 已合流. 清 review warning, 不抢 Batch 2 scope.

1. 先 commit doc-only trailer:
   Signal: HOLDING-CU-ACK
2. Task H-A: Agent2/4 health 端点
   - agent_riskctrl/api.py + agent_alert/api.py 各加 GET /health 返 200 + {"status":"ok","agent":"<name>"}
   - api_server.py 挂载确认
   - curl 冒烟验 200
   - Signal: HOLDING-CU-H-A-DONE
3. Task H-B: BLE001 defensive except 精确化
   - ruff check --select BLE001 agent_*/ shared/ 列出 43 处
   - 每处改为精确 exception 类型(如 ValueError / KeyError / RuntimeError)· 禁止广泛 except Exception
   - 保持行为不变(原 fallback 语义)
   - ruff check 后 BLE001 = 0
   - Signal: HOLDING-CU-H-B-DONE
4. 全部完成: Signal: HOLDING-CU-DONE

红线: 不改 Agent6 / financial_analyzer / quality_scorer / truth_fill / web/ / evaluation/ / data/mock/. 每 Task 独立 commit. 不启动 Batch 2 新功能.
开干.
```

---

## ② code-arch holding

```
HOLDING GO. Batch 1 APPROVED 已合流. 清 W1, 不抢 Batch 2 scope.

1. Signal: HOLDING-CA-ACK
2. Task H-A: scripts/feedback_to_fewshot.py 加 --dry-run 参数
   - argparse 加 --dry-run flag (default False)
   - dry-run 模式下只打印"将写入 N 条 few-shot 到 data/fewshot/<agent>/"不真写
   - 正常模式下维持现逻辑(写 data/fewshot/)
   - 加 tests/test_feedback_to_fewshot_dryrun.py 覆盖两个路径
   - 同一批 feedback 连跑两次 --dry-run 结果一致(幂等性)
   - Signal: HOLDING-CA-H-A-DONE
3. 全部完成: Signal: HOLDING-CA-DONE

红线: 不改 Agent6 / v16_* / financial_analyzer / quality_scorer / truth_fill / web/. 每 Task 独立 commit.
开干.
```

---

## ③ evaluation holding

```
HOLDING GO. Batch 1 APPROVED 已合流. 清 W1, 不碰 EV-12 (Batch 2 议题).

1. Signal: HOLDING-EV-ACK
2. Task H-A: v16_pipeline_summary.json 自动 parse 替换 method=manual
   - 读 evaluation/runner/adapters/agent6_report.py 当前 evidence_rate/hallucination_rate/quality_score_total 三项 method=manual 位置
   - 改为 parse v16_pipeline 产出的 summary JSON(当 Agent6 有 artifact 时自动读 qc.score / hallucinations / evidence_rate_summary 等字段)
   - 如无 artifact 则 fallback 到 manual 标记
   - 跑 py -m evaluation.runner --agent report --artifacts <samples 目录> --out /tmp/eval.json 验三项数字出
   - 同步更新 evaluation/baselines/<date>-first-run.md "首轮数字偏乐观" 警示仍保留
   - Signal: HOLDING-EV-H-A-DONE
3. 全部完成: Signal: HOLDING-EV-DONE

红线: 不改 v16_pipeline.py / agent_*/ 业务代码 / data/mock/ / evaluation rubric YAML. EV-12 ratio_calc_consistency 留给 Batch 2. 每 Task 独立 commit.
开干.
```

---

## 尾部说明

- **签名**：Holding kickoff 2026-04-24 · 主 CLI
- **预计工时**：每 worker 1-2 天(H-A 单日可收, H-B 一天精确化 43 处 BLE001)
- **Batch 2 冷冻期**：3 worker 领完各自 `HOLDING-<X>-DONE` 后原地待命,**不得**自行启动 Batch 2——等主 CLI 在 data-foundation v2 APPROVE 后统一派 Batch 2 kickoffs
- **Signal 索引**:
  - ACK × 3:`HOLDING-CU-ACK` / `HOLDING-CA-ACK` / `HOLDING-EV-ACK`
  - Task done × 3:`HOLDING-CU-H-A-DONE` / `HOLDING-CU-H-B-DONE` / `HOLDING-CA-H-A-DONE` / `HOLDING-EV-H-A-DONE`
  - 总 DONE × 3:`HOLDING-CU-DONE` / `HOLDING-CA-DONE` / `HOLDING-EV-DONE`
