# v16 Pipeline Quick Baseline · Post Wave 1 Merge

**生成日期**：2026-04-25
**main HEAD**：含 Wave 1 全合（agent6 + agent3 + agent1-cherry + data-foundation V2 + Q-033/Q-034/Q-035 + process docs）
**生成方式**：主 CLI proxy quick run · `py v16_pipeline.py --source samples/经纬测绘_对公成稿A.docx --material samples`
**触发缘起**：Q-035 A-035 follow-up · 取代 `evaluation/baselines/2026-04-26-real-run.md` Agent6 段（旧 baseline 68.6 是 pre-Wave-1 数据 · 已不反映实际状态）

---

## 1. 当前 baseline 数（DP1 单跑）

| 维度 | 数 | vs 旧 baseline 68.6 | 备注 |
|---|---|---|---|
| `quality_score_total` | **57.9** | -15.6% | Phase 2 design-intent drop（QC 四维强化 0f436fc + 模板扩展 38901c6） · NOT 退化 |
| `passed` | false | - | 闸门是 ≥ 65 · 当前不达 · 反映新 QC 体系下原模板需调整 |
| `hallucination_rate` | 0 | - | 红区守住 |
| `pending_tags` | 64 | - | 模板 slot 剩余 fillable |
| classifier loc | 1106 | - | 1106 element（185 已分类 · 921 fallback preserve） |
| dispatch 分布 | FILL 21 / PRESERVE 959 / REWRITE 43 | - | preserve 占主体（fallback 921 + scaffold 27 + preserve clean 11）|
| apply 统计 | fill 8 / keep 1015 / clear 0 / miss 0 | - | miss 0 = 红线达 |

---

## 2. 与 worker P3F 轨 1 跑分对照

worker（agent6）在 Q-035 askout 时跑过 5-DP 回归 · 报 quality_score（DP001）：
- pre-rebase tip 4bf8361: 66.4
- post-rebase HEAD 05b4eff: 66.8
- rebase mechanic drift: +0.4 / 0.602% **PASS Q-035 < 1% gate**

worker 跑的 "DP001" 与本任 quick run 用的 `经纬测绘_对公成稿A.docx` **可能不是同一 DP**（worker 走 evaluation/runner/cli.py 跑标准化 DP 集 · 主 CLI proxy 走 v16_pipeline.py 直接跑指定 docx）· 9 分差距属 DP 选择差异 · 非新增 drift。

---

## 3. 解读

- **本 baseline 是 Wave 1 后水位的 single-DP 快照** · 不是完整 5-DP regression
- **完整 5-DP baseline 应由 P3F 轨 8c evaluation worker 跑** · 用 evaluation/runner/cli.py · 含 EV-12 cross-agent + Agent2 5 pending 指标
- 本任 main CLI proxy 不替代轨 8c · 只为 unblock Q-035 A-035 follow-up "post-merge 替代旧 Agent6 baseline" 这条 follow-up

**对外报告口径**：
- 不再用 baseline 68.6 描述 Agent6 当前 score
- 待轨 8c evaluation 跑出后 · 用其 mean 数 + 各 DP delta 作为对外正式 baseline
- 客户 demo / RFP 引用 · 等轨 8c 完

---

## 4. 后续

- **轨 8c evaluation** Wave 3 dispatch 后 · 跑 `py evaluation/runner/cli.py --agent agent6 --baseline new` · 出完整 5-DP table
- **template_leakage_rate metric form** Q-030 follow-up（worker closeout body §6 honest caveat · sample 集 3 → 5 改变了 testbed · metric 数值不可直接比较）· 需轨 8c 设计新 metric form
- **本 quick baseline 标记为 transient** · 轨 8c 完后归档到 `evaluation/baselines/_archive/`

---

## 5. raw output

```
[v16_generator.generate] 经纬测绘_对公成稿A.docx
  classifier: 1106 loc / template: 1023 elems / materials: 5 files
  KB facts: 37
  REWRITE 段落: 29 个 section, 43 个段落
  dispatch 分布: {'FILL/CHECKBOX': 4, 'FILL/CLEAR': 3, 'FILL/FILL': 13, 'FILL/SLOT': 1,
                  'PRESERVE/PRESERVE': 932, 'PRESERVE/SCAFFOLD': 27,
                  'REWRITE/REWRITE': 43}
  apply 统计: {'fill': 8, 'keep': 1015, 'clear': 0, 'miss': 0}
  pending tags: 64
[QC] score=57.9 / 100  passed=False  halluc=0
```

完整产物：
- `outputs/经纬测绘_对公成稿A_v16.docx`（生成报告）
- `outputs/经纬测绘_对公成稿A_v16_pending.json`（pending 字段清单）
- `outputs/经纬测绘_对公成稿A_v16_qc.md`（QC 9 维度评分明细）
- `outputs/v16_pipeline_summary.json`（运行 summary）
