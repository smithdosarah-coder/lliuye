# 候选 Unique Identity Contract v1.1 · 2026-05-09

> **状态**: ✅ Phase A frozen (Phase A common worker · 2026-05-09)
> **Tier**: 1 (red zone · per `docs/arch/instruction-source-of-truth.md` v1.0)
> **Owner**: common worker · 修改走 RFC
> **依赖**: `shared/entity_resolver/candidate_helpers.py` (14 单测) + `make_unique_id` (per entity-resolution-contract §2.3)
> **背景**: PM 2026-05-08 反复痛点 (左右气泡不联动) 真根因 = 后端 candidate 没 id 字段 → 前端 `find` 命中错误. 本 contract 防再犯.

---

## 1. 硬规

任何 agent 出 candidate / customer / record 列表时, **每条必含 `id` 字段** (`string`, unique within list).

「必含」的意思:
- 不允许字段缺失 (`undefined` / 不存在)
- 不允许空字符串 / `null` / `"未获取"` / `"[object Object]"` 等典型 regression placeholder
- 同 list 内不允许 id 重复 (后端调 helper 自动加后缀解决)

## 2. id 派生规则 (按优先级)

per `entity-resolution-contract.md §3` + `make_unique_id`:

| # | 条件 | id 格式 | 例 |
|---|---|---|---|
| 1 | USCC 通过 | `uscc_<USCC>` | `uscc_91440300708461136T` |
| 2 | 仅 name 有 | `name_<md5前12位>` | `name_a1b2c3d4e5f6` |
| 3 | 都缺 | `cand_<idx:03d>` | `cand_005` |
| 冲突 | 同 list 出现重复 id | 加 `_<idx>` 后缀 | `name_abc123_3` |

## 3. 6 Agent 适用 (Phase B 各 agent 自接)

| Agent | 列表对象 | id 字段位置 | helper 调用 |
|---|---|---|---|
| channel | candidate (look-alike 候选) | `candidate.id` | `ensure_list_unique_ids(candidates)` |
| report | 报告草稿 / 章节 | `section.id` | `ensure_candidate_id(section, idx, name_field='企业名')` |
| credit | 决策记录 | `decision.id` | `ensure_candidate_id(decision)` |
| alert | 在贷客户预警条目 | `alert.id` (按 client_entity_key) | `ensure_list_unique_ids(alerts)` |
| compliance | 政策命中条目 | `hit.id` | `ensure_candidate_id(hit, name_field='client', uscc_field='client_uscc')` |
| riskctrl | 回测样本 / DSL 规则 | `rule.id` | `ensure_list_unique_ids(rules, name_field='rule_name', uscc_field='')` |

## 4. 后端接入 contract

### 4.1 主入口 helper (per shared/entity_resolver/candidate_helpers.py)

```python
from shared.entity_resolver import (
    ensure_candidate_id,       # 单条 dict
    ensure_list_unique_ids,    # list[dict] · 全条加 id + 同 list 去重
    verify_candidate_ids,      # CI guard · 跑前 verify list 合规
)

# Use case 1: SSE event payload (channel realtime_stream)
candidates = [
    {"name": "腾讯", "uscc": "91440300708461136T"},
    {"name": "阿里巴巴"},
    {},  # 空候选 · 兜底 cand_002
]
ensure_list_unique_ids(candidates)
# [
#   {"name": "腾讯", "uscc": "...", "id": "uscc_91440300708461136T"},
#   {"name": "阿里巴巴", "id": "name_a1b2c3d4e5f6"},
#   {"id": "cand_002"},
# ]

# Use case 2: 单条 record (report 报告对象 emit)
record = {"企业名": "腾讯科技深圳", "USCC": "91440300708461136T"}
ensure_candidate_id(record, idx=0, name_field="企业名", uscc_field="USCC")

# Use case 3: CI guard (pytest)
violations = verify_candidate_ids(candidates)
assert violations == [], f"id regression: {violations}"
```

### 4.2 SSE event emit 必经 helper (硬规)

任何 agent 在 emit `candidate` / `customer` / `alert_item` event payload 前, 必调 `ensure_list_unique_ids` 或 `ensure_candidate_id`. 不允许直接 emit raw dict.

反模式 (REJECT):
```python
# ❌ 直 emit raw · 缺 id
yield {"event": "candidate", "data": {"name": "腾讯", "uscc": "..."}}
```

正模式:
```python
# ✅ 先 ensure_candidate_id
candidate = {"name": "腾讯", "uscc": "..."}
ensure_candidate_id(candidate, idx=current_idx)
yield {"event": "candidate", "data": candidate}
```

## 5. 前端契约

- 前端 `setSelectedXxx(id)` + `find(it.id === selected)` 永不返第一项 (除非真选第一)
- 任何 list 渲染 `<Card data-cand-id={c.id}>` 必非空 · 必非 regression placeholder
- 选中态来自 `id` 字段 (而非 list index) · index 在 list 重排时漂移

## 6. Playwright contract test 模板

每个 agent worker 在 `web/tests/regression/<agent>-candidate-id.spec.ts` 写一份:

```typescript
import { test, expect } from "@playwright/test";

test("<agent> emits candidates with non-empty unique id", async ({ page }) => {
  await page.goto("/archive/<agent>");
  await page.click('[data-testid="<agent>-start-btn"]');

  // 等待 SSE 流出至少 3 candidate
  await page.waitForSelector('[data-cand-id]', { state: "attached" });
  await page.waitForFunction(
    () => document.querySelectorAll("[data-cand-id]").length >= 3,
  );

  // Verify all candidates have non-empty unique id
  const ids = await page.$$eval("[data-cand-id]", (cards) =>
    cards.map((c) => c.getAttribute("data-cand-id")),
  );

  // 1. 全非空
  for (const id of ids) {
    expect(id).toBeTruthy();
    expect(id).not.toBe("未获取");
    expect(id).not.toBe("[object Object]");
    expect(id).not.toBe("null");
    expect(id).not.toBe("undefined");
  }

  // 2. 同 list unique
  expect(new Set(ids).size).toBe(ids.length);

  // 3. 格式合规 (uscc_X / name_X / cand_X)
  for (const id of ids) {
    expect(id).toMatch(/^(uscc_[0-9A-HJ-NPQRTUWXY]{18}|name_[a-f0-9]{12}(_\d+)?|cand_\d{3})$/);
  }
});
```

## 7. 失败处理

| 失败场景 | 行为 |
|---|---|
| id 派生失败 (name 空 + USCC 空) | 用 `cand_<idx>` 兜底 · 不抛异常 |
| id 重复 (同 list 出现 2 个相同 id) | helper 自动加 `_<idx>` 后缀 · log warn 不阻断 |
| 现有 id 是 regression placeholder (`"未获取"` / `"[object Object]"`) | helper 强制覆盖 · in-place 改 |
| 现有 id 是合法值 (manual_id_42) | helper 保留 · 不覆盖 |

## 8. 红线 (任一触发即 stop-the-line)

per CLAUDE.md §3.6 stop-the-line:

1. **后端 emit 不调 helper** · raw dict 直进 SSE · 缺 id 上线 → 前端 find 命中错误 (PM 2026-05-08 痛点)
2. **id regression placeholder** 出现在 production · `[object Object]` / `未获取` 即视作 P0
3. **前端 hardcode 第一项** 兜底 (`candidates[0]` 不基于 id 选中) · 是回到痛点的反模式

## 9. ABI 稳定性承诺

Phase A 冻结后 · 以下 API 不许 break:

- `ensure_candidate_id(candidate, *, idx, name_field, uscc_field, id_field, strict)` 签名
- `ensure_list_unique_ids(candidates, *, name_field, uscc_field, id_field, strict)` 签名
- `verify_candidate_ids(candidates, *, id_field)` 签名
- 输出 id 格式 (uscc_X / name_X / cand_X · 前端正则依赖)
- regression placeholder 黑名单 (`"未获取"` / `"[object Object]"` / `"null"` / `"undefined"` / 空字符串) · 不删

## 10. 单测覆盖 (14 cases · 3 类)

| 类 | 测试数 | 覆盖 |
|---|---|---|
| TestEnsureCandidateId | 6 | 加 / 保留 / 覆盖 regression / idx 兜底 / custom field |
| TestEnsureListUniqueIds | 3 | 全填 / 同 list unique / 冲突解决 |
| TestVerifyCandidateIds | 5 | 全合规 / 缺 id / 黑名单 / 重复 / 非 str |

跑通: `py -m pytest tests/shared/test_candidate_helpers.py -v` → 14 passed.

## 11. 已知 violator 跟踪

| Agent | Phase A 状态 | Phase B 责任 worker |
|---|---|---|
| channel | ✅ 已修 (commit `c074d43`) · Phase B verify 不回退 | channel 已并入主线 (本 worktree pre-Phase A) |
| report | 🔴 待接入 | report worker |
| credit | 🔴 待接入 | credit worker |
| alert | 🔴 待接入 | alert worker |
| compliance | 🔴 待接入 | compliance worker |
| riskctrl | 🔴 待接入 | riskctrl worker |

Phase B 各 worker 完成时 fire signal commit 必含 trailer:
```
PRESERVES: candidate-identity-contract
SMOKE-PASS: web/tests/regression/<agent>-candidate-id.spec.ts
```

## 12. 待 Phase B 各 agent 接入

- [ ] report `agent_report/api.py` SSE emit 入 ensure_*
- [ ] credit `agent_credit/api.py` SSE emit 入 ensure_*
- [ ] alert `agent_alert/api.py` SSE emit 入 ensure_*
- [ ] compliance `agent_compliance/api.py` SSE emit 入 ensure_*
- [ ] riskctrl `agent_riskctrl/api.py` rule emit 入 ensure_*
- [ ] 5 agent 各写一份 Playwright contract test (per §6 模板)
