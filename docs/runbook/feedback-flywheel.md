# 数据飞轮 · 第 4 环 Runbook（PM 操作手册）

**第 4 环 = 从 feedback 提取 few-shot 示例，注入 prompts.py**

对应 CLAUDE.md §6：静态知识 → 模型评估 → **动态经验(feedback)** → **提示词优化(few-shot)**。本轮关注后半段自动化链路。

**责任人**：AI 产品经理（刘野 / 代理人）
**节奏**：每周一固定时段；或 `/api/feedback/stats` 某 agent 累计 ≥ 20 条时临时触发

---

## 数据流

```
审贷员修改 Agent 输出
    ↓ /api/feedback (api_server.py)
data/feedback/YYYY-MM-DD.jsonl              （第 3 环产出）
    ↓ scripts/feedback_to_fewshot.py
data/fewshot/<agent>-candidates.json         （聚类后的候选）
    ↓ PM 人工 review（必有）
data/fewshot/<agent>-candidates.json         （review 后版本）
    ↓ scripts/inject_fewshot_to_prompts.py
agent_<name>/prompts.py  :: FEW_SHOT_EXAMPLES （注入后的版本）
    ↓ Agent LLM 调用自动消费
```

---

## 周一 SOP（约 20 分钟）

### Step 1. 聚合候选（机器）

```bash
py scripts/feedback_to_fewshot.py --since 2026-04-01 --min-count 2 --top-n 5
```

- `--since`：只看本周的 feedback（避免老反馈抢位）
- `--min-count 2`：至少 2 条相似才入选，剔除偶发个例
- `--top-n 5`：每 agent 最多 5 个 few-shot，太多会污染上下文

产物：`data/fewshot/{channel,credit,alert,compliance,report,riskctrl}-candidates.json`

### Step 2. Review 候选（人）

逐个 agent 打开 candidates JSON，检查 6 条：

- [ ] `reason` 是否写明白了"审贷员为什么改"；模糊的（如"不好"）→ **删**
- [ ] `preferred_output` 的金额/日期/公司名有没有 PII；有 → **脱敏**或删
- [ ] `sample_input` 与 `preferred_output` 的字段 key 对齐（同一字段在改什么）；不对齐 → **删**
- [ ] 这条反馈是"个性化偏好"还是"共性错误"；个性化 → **删**，共性才留
- [ ] 同一 agent 下是否有重复聚类键；合并 `count`
- [ ] 最终每 agent 留 **2-4 条**高信号 example（多于 4 条会撑 prompt token）

### Step 3. 注入（机器）

先 dry-run 看要改哪些 prompts.py：

```bash
py scripts/inject_fewshot_to_prompts.py --dry-run
```

确认无误：

```bash
py scripts/inject_fewshot_to_prompts.py
```

注入点在每个 `agent_<name>/prompts.py` **末尾**，由以下 marker 包围，幂等可重跑：

```python
# >>> FEW_SHOT_EXAMPLES · auto-injected · do not edit inside >>>
# generated_at: 2026-04-24T...
# agent: credit
# count: 3
FEW_SHOT_EXAMPLES = [ ... ]
# <<< FEW_SHOT_EXAMPLES · auto-injected · do not edit inside <<<
```

### Step 4. 验证（机器）

Agent 侧读 `FEW_SHOT_EXAMPLES` 并拼进 system prompt：跑一次对应 Agent 的 demo，肉眼看输出风格是否向反馈方向收敛。

如果发现注入错了 / 拉垮了输出 → **立即回滚**：

```bash
py scripts/inject_fewshot_to_prompts.py --revert
```

（marker 块会被原子抹除，prompts.py 回到注入前状态）

### Step 5. 归档

把当周的 `data/fewshot/*-candidates.json` 复制到 `data/fewshot/archive/YYYY-WW/` 做留痕。**原位置**应保持为最新版，供下次 inject 复用（仍可跑 --revert 再重跑 --inject）。

---

## 红线

- 🔴 **绝不自动 inject**：Step 2 的人工 review 不能省；脚本层已刻意拆成两步。
- 🔴 **Prompts 改动走 PR**：`inject_fewshot_to_prompts.py` 写盘后 **必须** commit 才算完。commit message 形如 `chore(prompts): inject fewshot 2026-W17 · credit=3, alert=2`。
- 🔴 **任何脱敏失误看到即回滚**：审贷员反馈里可能带客户真实名字/金额，review 阶段必须全部脱敏或删条，不要留在 prompts.py 里。
- 🟡 **max-shots**：单 agent ≤ 4 条，超了就 `--top-n 3`；上下文 token 是成本。
- 🟡 **滚动窗口**：默认 `--since` 取最近 4 周；超过 4 周前的 feedback 大多过期（业务/政策变了）。

---

## 故障排查

| 症状 | 可能原因 | 处置 |
|---|---|---|
| `candidates not found` 警告 | 先没跑 feedback_to_fewshot | 先跑 Step 1 |
| Step 1 跑完 `candidates` 为空 | `--min-count` 过严 / feedback 目录空 | 放宽到 `--min-count 1` 看看，仍空则 /api/feedback 没在收 |
| inject 后 LLM 输出变差 | few-shot 质量不行 / 示例偏差 | `--revert` 回滚，回 Step 2 重新 review |
| 注入 marker 重复出现 | 手改过 prompts.py 破坏了 marker | 人工删掉所有 marker 块后重跑 inject |

---

## 相关文件

- `scripts/feedback_to_fewshot.py`
- `scripts/inject_fewshot_to_prompts.py`
- `api_server.py:85-115` `/api/feedback` 端点
- `data/feedback/` JSONL 沉淀目录（**gitignored**，含真实审贷员反馈可能含 PII）
- `data/fewshot/` 候选 + archive 目录（**gitignored**）
- `agent_*/prompts.py` 注入目标
- `tests/fixtures/feedback/2026-04-23.jsonl` 10 条合成样本（用于冒烟测试，不入生产目录）

首次部署本脚本时想跑个 demo：

```bash
cp tests/fixtures/feedback/2026-04-23.jsonl data/feedback/
py scripts/feedback_to_fewshot.py --min-count 2
```
