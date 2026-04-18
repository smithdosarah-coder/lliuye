---
rule: Rule 16 · 同比/环比表述禁止前置年份
agent: Agent6 / V16 REWRITE 管线
commit: b1c4d13
status: APPROVED · regression PASS (90.0 > 88.5 基线)
date: 2026-04-18 (决策) / 2026-04-19 (回归 + 归档)
tags: [治本, 幻觉规避, CLAUDE.md §3.1, CLAUDE.md §12, shared-change-protocol §1.1]
supersedes: section_generator.py:1407 _fix_dup_year_phrases 的下游清洗依赖
---

# Rule 16 决策档 · 同比/环比表述禁止前置年份

> 本文件是"对公/普惠 Rule 17/18 治本提案"的样板。5 段式结构固定,
> 未来同类规则(LLM 输出格式幻觉类)按本模板在 `docs/decisions/` 递增。

---

## 1. 触发现象

**问题形态**:LLM 在 REWRITE 段落里为每个对比句重复补写年份前缀,形如
`"营业收入 2025 年同比增长 14.9%"` / `"资产负债率 2025 年较年初下降 7.7 个百分点"`。
年份归属本应由段首统一交代,逐句复写破坏语义、污染下游 regex 清洗,
并在"分别为 X、X, 同比 ±Y%"这一对账句式中引发**两侧数值残留不被消解**的次生缺陷。

**历史真证**(并非本次新发,是 V14 阶段已观察并被下游 regex 兜底过的老问题):
- `section_generator.py:1407` `_fix_dup_year_phrases` 的 docstring 原文:
  > "V14-H 治本:LLM 写 '近两年 X 分别为 A、A, 同比 B%' 这种双写自矛盾句式"
- 该函数的触发正则([section_generator.py:1424-1433](../../section_generator.py#L1424))
  专门匹配 "分别为 X、X,同比 Y%" 并反算上年真值。存在即证明 LLM 曾稳定产出该错形。

**本次 V16 复现路径**:
- V16 管线绕过 `section_generator.py` 主链(独立的 `v16_op_handlers.REWRITE`),
  上游 V14-H 兜底逻辑**不经过 V16 输出**。
- 近期测试中 V16 REWRITE 输出存在 `"20XX 年+同比/环比/较年初"` 前缀,
  同样的结构性幻觉在新管线未经清洗直接落到 docx。
- 有人起手想在 `section_generator.py:1428` 处把兜底正则从 `"\s*同比\s*"`
  扩成 `"\s*(?:20\d{2}\s*年?\s*)?同比\s*"`(已 stash 为
  `v16-section-gen-regex-polish-park`),即方案 A 备选。

**影响面**:
- 读者侧:冗余年份污染段落节奏,违反信贷审贷书"客观简洁"的文体要求。
- 工程侧:下游 QC scorer 用严格正则识别 `"同比 X%"`,年份前缀让"同比"与数字
  之间出现 "20XX 年" 断裂,**同比项命中率被误杀**(Rule 16 回归前 1 次 reproduce
  测到 "③同比" 项 0 命中,9 维评分 财务深度 → 4.0/10)。
- 数据侧:`_fix_dup_year_phrases` 失配 → 两值残留保留("营收分别为 10010 万元、
  10010 万元,同比增长 14.9%" 里两个 10010 不会被反算修正)。

---

## 2. 备选方案

| 方案 | 路径 | 否决理由 |
|---|---|---|
| **A. 下游 regex 扩容**(`section_generator._fix_dup_year_phrases` 正则加 `(?:20\d{2}\s*年?\s*)?`) | 保留 LLM 原样输出,在兜底函数里吞掉前缀 | **触犯 shared-change-protocol v1.1 §1.1 红区**(`section_generator.py` 在红区,禁止 Agent6 在未 RFC 的前提下改)。即便红区豁免,CLAUDE.md §12 明令「不写关键词/正则黑名单兜底幻觉 —— 治本用证据链 + QC Blocker」。此路是典型 V10~V15 技术债积累路径。 |
| **B. Stash 作补丁长期挂着** | 就地 stash `v16-section-gen-regex-polish-park`,视情况解套 | 违反「work tree clean」DoD 硬指标;stash 是临时工具不是长期策略;多 CLI 协作下 stash 对其他 session 不可见,bus factor 极高。 |
| **C. REWRITE prompt 硬规则**(v16_op_handlers._REWRITE_SYSTEM_PROMPT 追加 Rule 16) | **上游堵住生成**,让 LLM 从源头就不输出 `"20XX 年+同比"` | 无否决理由。 |

**选 C**。A/B 都是在幻觉发生**之后**打扫,C 是在幻觉发生**之前**阻止。
前者是症状管理,后者是病因管理。

---

## 3. 选定路径

**Commit**:`b1c4d13 fix(v16): prevent year-prefixed 同比/环比 in REWRITE prompt`
(chore/l0-infra,2026-04-18)

**落点**:[`v16_op_handlers.py:503-508`](../../v16_op_handlers.py#L503)

```
16. 【同比/环比表述禁止前置年份】"同比""环比""较年初""较上年末""较去年"等对比
    短语前,禁止插入任何年份前缀("20XX年"/"XXXX年"/"FY20XX"/"去年"/"上年")。
    正确:"营业收入同比增长14.9%"、"资产负债率较年初下降7.7个百分点";
    错误:"营业收入2025年同比增长14.9%"、"资产负债率2025年较年初下降7.7个百分点"。
    年份归属由段首统一交代,不得在每个对比句重复。违者下游 regex 清洗无法识别,
    会导致"分别为X、Y"的重复值残留在最终文档。
```

**选它的理由**:
1. **CLAUDE.md §12**「不写关键词/正则黑名单兜底幻觉(治本用证据链 + QC Blocker)」
   —— 方案 A 精准撞在这条红线。
2. **CLAUDE.md §3.1 确定性 vs 概率性**「概率性计算…用 LLM + 证据链」—— LLM 输出
   格式问题属于 LLM 自己的职责域,应在 prompt 层约束而非事后清洗。
3. **shared-change-protocol v1.1 §1.1 红区**`section_generator.py` 禁止未 RFC
   改动,方案 A 需开 RFC;方案 C 改的 `v16_op_handlers.py` 不在红区(绿区 Agent6
   独立域),决策阻力 1/10。
4. **单点修复**:错形正例/反例直接写进 prompt,LLM 自解释合规,无需额外组件。

**配套动作**:
- `v16-section-gen-regex-polish-park` stash 已 drop(commit `3ef89c7` 对应 object)
- stash@{1} `pre-merge-stash-2026-04-18` 与本规则无关,保留

---

## 4. 回归证据

**回归环境**(demo-agent6 worktree,Rule 16 单独生效,**无下游 regex 辅助**):

| 指标 | 基线(88.5 run, 带下游 regex) | Rule 16 run | Δ |
|---|---|---|---|
| 总分 | 88.5 | **90.0** | **+1.5** ✅ |
| 状态 | PASS | PASS | — |
| halluc_rate | 0 | 0 | — |
| 年份前缀命中 `20XX年+同比/环比/较年初` | — | **0** | 目标达成 ✅ |
| 重复值残留 `X、X` 对账句 | — | **0** | 连带缺陷消解 ✅ |
| 正向对比短语总数(同比/环比/较年初) | — | 22 | 表达力未被压制 ✅ |

**9 维细分**(仅列变动维度):

| 维度 | 基线 | Rule 16 | Δ |
|---|---|---|---|
| 征信分析 | 7.8 | 8.9 | +1.1 |
| 其余 8 维 | — | — | 持平或改善 |

**剩余 miss 项**均为**材料侧缺口**,与 Rule 16 无关:
- 注册资本(KB 未覆盖)
- ⑩异常项识别
- 担保覆盖度
- 风险点数量(仅 1 处)

**证据文件**(demo-agent6):
- [`outputs/普惠申报书_骨架型_v16.docx`](../../outputs/普惠申报书_骨架型_v16.docx)
- [`outputs/普惠申报书_骨架型_v16_qc.md`](../../outputs/普惠申报书_骨架型_v16_qc.md)
- [`outputs/普惠申报书_骨架型_v16_pending.json`](../../outputs/普惠申报书_骨架型_v16_pending.json)

**材料包**:`D:/claude code/credit_report_agent_work/outputs/sessions/work_4t07wts7`
(中锐 真实材料,不入库,外部挂载)

---

## 5. 可复用性 — Rule 17/18 套用参数表

未来任何「LLM 输出格式性幻觉 + 下游 regex 清洗倾向」的场景,按以下参数替换即可
复用本决策路径:

| 参数槽 | Rule 16 实例 | 替换说明 |
|---|---|---|
| **错形 pattern** | `20XX 年 + 同比/环比/较年初/较上年末/较去年` | 新规则的错误正则 |
| **正例句** | "营业收入同比增长 14.9%" | 展示 LLM 该怎么写 |
| **反例句** | "营业收入 2025 年同比增长 14.9%" | 展示禁止的写法 |
| **连带缺陷** | "分别为 X、X,同比 Y%" 两值残留 | 错形引发的二阶症状 |
| **现存下游清洗函数**(若有) | `section_generator.py:1407 _fix_dup_year_phrases` | 证明症状曾观察过,非推测 |
| **落点文件** | `v16_op_handlers.py:_REWRITE_SYSTEM_PROMPT` | prompt 层的上游堵漏点 |
| **回归样本** | `samples/普惠申报书_骨架型.docx` + 中锐材料包 | 对公规则改用 `samples/兴业资管_对公成稿B.docx` + 对应材料包 |
| **QC 基线** | 88.5(带下游 regex) | 新规则应保持或超越 |
| **决策援引** | CLAUDE.md §12、§3.1;protocol v1.1 §1.1 | 固定援引,同理 |

**决策模板**(建议 Rule 17/18 提案文直接套):

```
- 触发现象: <贴 LLM 真实输出样本 + 文件:行 citation>
- 备选 A(下游清洗) + 否决 → 引 CLAUDE.md §12
- 备选 B(prompt 硬规则) + 选定 → 引 §3.1
- 落点: v16_op_handlers.py Rule <N>
- 回归: 骨架型/对公样本 QC Δ + 错形命中 0 + 表达力未压制
- commit trailer Signal: READY-FOR-REVIEW
```

**注意事项**:
1. Rule 条目编号按 `_REWRITE_SYSTEM_PROMPT` 内顺序递增,不要与 FILL/PRESERVE 分支
   prompt 混编。
2. 新 Rule 落地前先回归骨架型(基线 90.0),再回归对公样本;两者都要 PASS。
3. 回归证据里**必须**同时给出:错形命中 0 + 正向短语总数未塌方,证明规则是外科
   手术而非一刀切。
4. 若新 Rule 需改动红区文件(section_generator / truth_fill / material_kb 等),
   先走 RFC,不要直接上(protocol v1.1 §1.1)。

---

**档案索引**:`docs/decisions/`

- `rule-16-year-prefix-治本.md` ← 本文件
- `rule-17-*-治本.md` ← 待占位(对公专项 · 业务方材料到位后启动)
- `rule-18-*-治本.md` ← 待占位
