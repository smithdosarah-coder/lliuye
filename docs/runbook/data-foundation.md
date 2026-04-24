# data-foundation worker · Runbook

**Worktree**：`D:/claude code/demo-data-foundation`
**分支**：`feat/data-foundation`
**当前批次**：Product Hardening · Batch 1
**Onboarding**：`docs/onboarding/data-foundation-phase-1.md`
**决策**：`docs/handoff/decisions-log.md` · Q-023 / A-023
**入场时间**：2026-04-24

---

## 本 runbook 的作用

Worker CLI 执行 "拟真数据底座" 任务的现场操作手册。记录：
- 产出物路径约定（唯一入口）
- 反"结果导向"4 原则在动作层的落地写法
- 每 Task 的 commit 粒度 + signal trailer 对应关系
- 未来 Batch 2 触发条件与候补动作

不重复 onboarding 里已有的任务清单；补充的是**"怎么做"级别**的细节。

---

## 产出物唯一入口

```
data/mock/
├── README.md                       # 架构哲学 + 目录说明 + 消费方指南
├── schemas/
│   ├── wide-base.yaml              # 宽基 100 schema
│   └── deep-pillar.yaml            # 深柱 15 的 11 类信号 schema
├── wide-base/
│   ├── companies.yaml              # 100 家企业骨架（Task B 产）
│   └── source-notes.md             # 每家企业的"标杆参考"脚注（PM 验真用）
└── deep-pillar/
    ├── shortlist.md                # 15 家深柱候选 + 难度分布 + 参考标杆
    ├── pit-template.md             # 埋坑清单空模板
    └── pits/<company_id>.md × 15   # 各家一份埋坑空表（交 PM 填）
```

**禁区**：`agent_*/` / `web/**` / `evaluation/` / `customer/` / `demo_data/` / `industry_cards/` 均只读。

---

## 反结果导向 4 原则 · 落地动作表

| 原则 | 在本 worker 动作中的表现 |
|---|---|
| 1 盲测法 | 埋坑清单是**空模板**，worker 不填答卷；PM 填完再回传触发 Batch 2 |
| 2 难度分层 | 宽基 100 家严格 `easy:20 / medium:50 / hard:20 / extreme:10`；深柱 15 家 `easy:3 / medium:7-8 / hard:3 / extreme:1-2` |
| 3 真实来源锚定 | 每家企业 `source-notes.md` 必须注明"脱敏前身"（A 股年报代码 / 央行征信模板章节 / 银保监处罚文号之一）；禁止无锚点凭空编 |
| 4 脱敏再造 | 修改名称、统一社会信用代码后 4 段随机、注册资本量级保留但数值浮动 ±30%、地址具体到区但门牌脱敏 |

---

## Commit 粒度 · Signal trailer 映射

| 步骤 | Commit 范围 | Trailer |
|---|---|---|
| 0 | ACK 入场（本 runbook） | `Signal: PRODUCT-HARDENING-BATCH-1-ACK` |
| A | `data/mock/README.md` + 2 份 schema + 空目录骨架 | `Signal: DATA-SCHEMA-DONE` |
| B | `data/mock/wide-base/companies.yaml` + `source-notes.md` | `Signal: DATA-WIDE-100-DONE` |
| C | `data/mock/deep-pillar/shortlist.md` + `pit-template.md` + 15 份空 pit 文件 | `Signal: DATA-DEEP-SHORTLIST-DONE` |
| 总 | 不产新文件，empty commit 或小幅 README 更新 | `Signal: READY-FOR-DATA-FOUNDATION-B1-REVIEW` |

**规则**：
- 每 Task 一个 commit；中途不请示，除非 blocker
- 不跨 Task 合并 commit
- Trailer 必须顶格单行，`Signal: ` 前缀与 onboarding 完全一致

---

## PM 抽检应对（Task B 专用）

PM 会随机抽 20 家（20%）交叉验证：
- 如被判真度 < 80%（标杆脱敏粗糙 / 行业常识错误 / 难度档失真），**整档反工**（不是补那 20 家）
- 反工优先级：标杆注解补全 > 行业常识复核 > 财务量级校准 > 名称脱敏收敛
- 反工 commit 走 `Signal: DATA-WIDE-100-REVISED-v2`（如发生再定）

---

## Batch 2 触发条件（不在本 Runbook 范围，仅预告）

1. 用户（PM）填完 15 份 `pits/<company_id>.md` 并回传
2. 主 CLI 下发 `PRODUCT-HARDENING-BATCH-2-DISPATCHED`
3. 本 worker 拿到埋坑清单后才启动 MVP 3 家（或更多）完整材料包：3 年财报 + 12 月流水 + 征信 + 担保 + 合同 + 舆情 + 政策关联 + 贷后行为 + 风险标记 + 策略样本元数据

Batch 1 阶段严禁预制材料包，即使"顺手就做"也不做——避免污染盲测。

---

## 工作日志（append-only）

- **2026-04-24**：worker resume 完成；发 ACK doc-only commit（即本 runbook 首稿）。等 GO 进 Task A。
- **2026-04-24**：收到 GO，按 A → B → C 顺序一口气跑完 Batch 1：
  - Task A `5bac8e4 → 95a4d4f`：`data/mock/README.md` + 2 份 schema + 目录骨架 → `DATA-SCHEMA-DONE`
  - Task B `b6299dc`：宽基 100 家 companies.yaml + source-notes.md（分布 25/20/15/12/10/8/5/5 · 难度 20/50/20/10 严格）→ `DATA-WIDE-100-DONE`
  - Task C `82dcce3`：深柱 15 家 shortlist + pit-template + 15 份 pit 空白表 + wide-base `deep_pillar_candidate` 同步置 true → `DATA-DEEP-SHORTLIST-DONE`
  - 全 Task 完成 → 发 `READY-FOR-DATA-FOUNDATION-B1-REVIEW` 等主 CLI review。

- **2026-04-24 (REJECT-V2)**：主 CLI 判 v1 形态错——`yaml` 清洗版本把答案喂到模型嘴边（`difficulty` / `benchmark_ref` / `deep_pillar_candidate` 这些字段就是"答案字段"）。按 v2 onboarding 返工：
  - **路线切换**：数据形态从"yaml 清洗版"改为"**真实材料包**：文件夹 + 异构格式 + 命名噪声 + 三方数字矛盾 + 零答案字段"
  - **Agent1/5 外部边界**：不 mock 外部搜索结果——只建 Agent1 内部 KB（历史客户 / 营销偏好 / 产品目录）+ Agent5 内部制度库
  - **v2 Task 清单**：A 删老产物+重建骨架 / B 深柱 5 家材料包 / C channel-kb / D compliance-kb / E 全轨 final signal
  - 本次 ACK 即发 `PRODUCT-HARDENING-BATCH-1-V2-ACK`，等读完 v2 onboarding + Q-028 后依序开干。
