# Codex Peer-Review Protocol v2 · 主 CLI ↔ Codex 协作硬规

**Status**: ratified · 2026-04-30 (Day 2 codex 拉闸事件后立)
**Triggered by**: Day 2 13:00+ codex bg review A4-riskctrl + A4-report 卡 60+ min × 2 轮 · 主 CLI manual fallback ship · 暴露协作模式 v1 缺陷 (无 timeout · 无 fallback · 无 reasoning gate)
**Owner**: 主 CLI (本协议执行) · PM (本协议拍板)

---

## 0. 真因复盘 (post-mortem · 2026-04-30 Day 2)

**现象**: codex bg review (`bpm32m8n6` + `be6itngom` + `bcxodv4b5`) 跑 60+ min 不出 verdict · main CLI 等不起 → kill + manual review fallback ship 5/5 V2。

**真因 (verified)**:
- Codex CLI healthy (`codex login status` Logged in via ChatGPT · simple PONG prompt 24s OK)
- Codex `~/.codex/config.toml`: `model = "gpt-5.5"` + `model_reasoning_effort = "xhigh"` (全局)
- 复杂 review prompt (6 issue · 多文件 diff · 100+ KB context) + xhigh reasoning → codex 进入"超深度思考"模式 60+ min 不出 verdict
- **不是 hang · 不是 quota · 是 codex 在真认真想但用太多时间**

**协作影响**: PM 等不起 60+ min · 主 CLI 工作流被阻 · A4 5 子 V2 ship 延迟 · 不可持续

---

## 1. 协议 v2 5 条硬规

### 1.1 Per-call reasoning effort override (强制)

**所有 codex bg review 必须 override reasoning effort 到 `medium` 或 `high`** · 不依赖全局 `xhigh` 配置:

```bash
codex exec -c 'model_reasoning_effort="medium"' --output-last-message <path> "<prompt>"
```

| Reasoning effort | 适用场景 | 期望时长 |
|---|---|---|
| `low` | hello world / health check / 单字段 verify | ≤ 1 min |
| `medium` | 标准 post-DONE review (3-6 issue · 1-3 file · ≤ 5KB diff) | ≤ 5 min |
| `high` | 复杂 review (6-10 issue · 多文件 · 5-50KB diff) | ≤ 15 min |
| `xhigh` | 仅 Phase 终审 / RFC 终判 / 主 CLI 拍板前最后核对 (主动 explicit invoke) | ≤ 30 min |

**默认 `medium`** · 不主动选 `xhigh`。

### 1.2 卡死监控 + manual fallback (PM 2026-04-30 ratify)

**PM 拍板: codex 慢 OK · 只要进程没死 · 主 CLI 真等 · 不要 30 min hard timeout 强 fallback**。

理由: codex deep-think (xhigh / high reasoning) 真有用 · verdict 质量 > 速度 · PM 等得起。Day 2 真问题不是慢 · 是没人 monitor + main CLI 没并行干别的事。

**真"卡死"判定 (3 选 1 才 fallback)**:
- (a) codex.exe 进程消失 (PowerShell `Get-Process codex` count = 0 · process crashed)
- (b) bg task status = "completed" (BashOutput) 但 verdict 文件 0 byte / 不存在 (codex CLI exit 但没写 output)
- (c) bg task status = "running" 持续 ≥ 90 min 且 codex.exe CPU usage 0% (真 deadlock · 用 PowerShell `Get-Process codex | Select-Object CPU`)

**正常慢 (允许等)**:
- bg task status = "running" + codex.exe alive + CPU usage > 0% (codex 真在算)
- 等 60-90 min OK · main CLI 同时干其他活 (cron tick 等 · 不空等)

**监控节奏**:
- 每 cron tick (5 min) check: `TaskOutput block=false` + codex.exe count
- 每 30 min check: `Get-Process codex | Select CPU` (verify CPU > 0%)
- 90 min 还没出 + CPU 0% → fallback manual

**不允许的反模式**:
- 等 2h+ 不监控 (Day 2 第 1 轮 bpm32m8n6 卡 2h 是 monitor 缺失 fault · 不是 codex fault)
- 不 fallback (有真 deadlock 信号还硬等 · 浪费 main CLI 时间)
- 见慢就 kill (codex 真在算 · CPU > 0% · 没死信号 · 不要预 kill)

### 1.3 Sequential not parallel (强制)

Codex bg **一次只 fire 1 个** · 不并发 · 不批量。

- 5 个 worker DONE 后 → 顺序 fire codex × 5 (前一个 verdict 出再 fire 后一个) · 不并发 fire
- 理由: Day 2 Day 1 时 5 codex.exe 并发抢 API · 加剧 hang 风险 · sequential 也方便 fallback (1 个卡 → 立即 manual · 不影响其他)

例外: PM 显式说"加速跑并行" · 当场拍板。

### 1.4 复杂 prompt 拆段 (推荐 · 不强制)

> 6+ issue review prompt → 拆 6 个 single-issue review · 每次 prompt 短 · codex 不 hang

适用: review 任务 issue ≥ 5 个 · 单 issue verify 独立 · 拆段不掉信息。

不适用: cross-issue dependency review (比如 architecture audit · issue 间互依赖)。

### 1.5 协作 verdict commit 标 review-mode (强制)

任何 codex review verdict 落地 commit 必须含 trailer:

```
REVIEW-MODE: codex | manual
REASONING-EFFORT: low | medium | high | xhigh
ELAPSED: <minutes>
```

理由: audit trail · 后续分析 codex 协作健康度 (manual fallback 比例 / codex elapsed 趋势) 靠 trailer 统计。

---

## 2. 主 CLI fire codex 标准流程 (新)

### 2.1 单 review fire 模板

```bash
# 1. health check (非首次 session 跳)
time codex exec --skip-git-repo-check --sandbox read-only \
  -c 'model_reasoning_effort="low"' \
  --output-last-message "/tmp/codex_health.md" "Output exactly: PONG"
# 期望 ≤ 60s · 不 OK → escalate PM 不 fire

# 2. fire review (按场景选 reasoning effort · 默认 medium)
codex exec --skip-git-repo-check --sandbox read-only \
  -c 'model_reasoning_effort="medium"' \
  --output-last-message "/tmp/codex_<task>.md" "<prompt>" 2>&1 | tail -5
  # &
  # run_in_background: true

# 3. 监控 (30 min hard timeout)
# - check verdict file 每 5 min
# - 30 min 还没出 → TaskStop + manual fallback
```

### 2.2 Manual fallback 模板

```python
# Codex 30 min timeout 后 · 主 CLI 必走的 fallback
1. 读 V1 codex review verdict (or original DONE doc · 列 issue 清单)
2. git show <V2-commit> --stat (看 file scope)
3. per issue: git show <V2-commit>:<file> | grep -n <key> · evidence-based verify
4. 写 verdict doc 落地 `docs/audit/codex-reviews/<WORKER>-V2-DONE.md`:
   - verdict: AGREE | DISAGREE
   - issue-N-fixed: yes/no/partial — evidence (file:line)
   - REVIEW-MODE: manual (codex bg timeout fallback)
5. commit verdict tracking on main:
   `chore(reset): CODEX-REVIEW-<WORKER>-V2-VERDICT-AGREE · manual review fallback`
```

### 2.3 Sequential A4 batch 模板 (5 worker DONE 后)

```
A4-credit DONE → fire codex (medium) → wait verdict ≤ 15 min → AGREE → cherry-pick → next
A4-alert DONE → fire codex (medium) → wait verdict ≤ 15 min → AGREE → cherry-pick → next
... (sequential · 1 by 1)
全 5 子 AGREE → push GitHub → ECS deploy 含 build (1 次)
```

**禁止**: 5 codex bg 并发 fire · 这是 Day 2 卡 60+ min 的诱因之一。

---

## 3. PM 视角 SLA (codex 协作 deliverability)

| 指标 | SLA | 违反 fallback |
|---|---|---|
| Codex health PONG | ≤ 60s | 跳过 codex · escalate PM |
| Standard review (medium) | ≤ 15 min target · 60 min PM 容忍 | 90 min + CPU=0 → manual |
| Complex review (high) | ≤ 30 min target · 90 min PM 容忍 | 90 min + CPU=0 → manual |
| Deep review (xhigh · 主动 invoke) | ≤ 90 min · PM 等得起 | 真死信号 (process disappear) 才 fallback |
| Manual review fallback | ≤ 10 min | 主 CLI 自己 review (Day 2 验过 baseline) |

**理论上 Codex 健康 + protocol v2 严守 + 主 CLI 持续 monitor → manual fallback 出现率应 ≤ 5%** (主要 codex CLI 真 crash / quota 问题)。Day 2 manual fallback 100% 是 protocol v1 失控 (无 monitor + 5 并发 + 全局 xhigh) 的多重 fault · 不是 codex fault。

**PM 2026-04-30 ratify**: "我能等 · 只要他没卡死就行" → 协议优先 codex verdict 质量 · 不预设 hard timeout · 主 CLI 真 monitor 真 fallback 才 manual。

---

## 4. 协议 v2 落地清单

| 项 | Owner | Status |
|---|---|---|
| 1. 本 doc commit | 主 CLI | ✅ (本 commit) |
| 2. 主 CLI 后续 codex 调用必加 `-c 'model_reasoning_effort="medium"'` | 主 CLI | 🟡 (本 doc ratify 后立即生效) |
| 3. 主 CLI 后续 codex bg fire 后必 30 min 监控 + auto fallback | 主 CLI | 🟡 (本 doc ratify 后立即生效) |
| 4. CLAUDE.md §3.7 加 active rule 3.7.4 (codex protocol v2) | worker-A1 / 主 CLI | 🟡 (待加) |
| 5. `~/.codex/config.toml` 是否改全局默认 `medium` | PM 拍板 | 🟡 (推荐改 · 但保 xhigh 作为 manual override 路径) |

---

## 5. Sign-off

- 主 CLI: 起草 (Day 2 codex 拉闸复盘 · 2026-04-30)
- PM: 待拍板 (本 doc commit 后 PM 看 review)
- worker-A1 (后续 SSOT lint enforcement 加 codex protocol check): 待 fire

**回写**: decisions-log Q-NNN entry "Codex peer-review protocol v2 ratified" · 含 PM 拍板时间 + reasoning effort 默认改值。

