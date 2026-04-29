# Anti-Bias 4 硬规

> Codex × Mesh 协作 + Round 1/2/3 双 AI 辩论 防偏向硬约束。

## 1. 独立草案 (Round 1)

**规则**: 双方 AI Round 1 各自 v1 时 · 不能见对方答案。

**实现**:
- 主 CLI fire codex 时 · prompt 中**不**包含 worker / claude 的 onboarding "建议" 段
- worker onboarding doc 也不预先写"主 CLI 建议方案"
- Codex 输出 v1 仅基于 task 描述 + repo 现状

**防什么**: 防"先看对方答案 → 顺着对方思路写 → 同质化"。

### 1.1 fresh main CLI 接手时的处理

前任 main CLI 跑过的 sub-agent / codex Round 1 输出 · 如果**未 commit 到 docs/audit/** · 一律视为不存在(compression 后无法 verbatim 还原 · 不可信)。

新 CLI 启动 Step 2 时必须**重派**(不复用前任 chat 高层总结)· 跑出 fresh 6 份输出 commit 到 docs/audit/。

这是 anti-bias rule 1 在长周期工程中的特例。

## 2. 强制输出 schema

**规则**: 每轮辩论必须用固定结构

```
改 (vs 我 Round 1): <list>
坚持: <list>
对方弱点: <list with file:line evidence>
吸收对方哪些点: <list>
v2 final: <revised answer>
```

**实现**: prompt template 强制 · 无 schema 输出视为 invalid · 重 fire。

**防什么**: 防 AI 写散文 · 散文容易自我说服。

## 3. 字数硬上限 ≤ 3500 词

**规则**: 任何一轮 AI 输出 ≤ 3500 词

**实现**: prompt 里 explicit 写 · 超字罚单 (主 CLI 截断)。

**防什么**: 防长答压短答 (长 ≠ 对 · 长容易掩盖弱论证)。

## 4. Dissent appendix 必须保留

**规则**: 任何 synthesis 必须有 dissent appendix · 列"双方仍不一致的 N 条"

**实现**: 主 CLI synthesize 时必填 dissent 段 · 0 条也要写"无 dissent"。

**防什么**: 防 synthesize 时把 minority view 默默吞掉 · 后期被遗忘的"我曾经反对的点"重新冒出来浪费工。

## 5. 单 issue 最多 2 轮辩论 (扩展规则)

**规则**: 一个 dissent item 第 2 轮还没收敛 → escalate PM

**实现**: dissent register 里每 item 标 round 数 · `round >= 2 && status == open` → 主 CLI 必须 PM intervention。

**防什么**: 防同一争议反复 N 轮拖死。

## 6. Dissent 数量监控 (扩展规则)

**规则**: 一轮结束后 dissent 不减反增 → escalate PM

**实现**: 主 CLI synthesize 后比较 v1 → v2 的 dissent 数 · 增加即 escalate。

**防什么**: 防辩论越聊分歧越大 (说明 framing 出问题 · 应该 PM 介入重 frame)。

---

**应用范围**: 任何 reset 工程内的双 AI 辩论 · Codex review · worker peer review · 全部 follow。
