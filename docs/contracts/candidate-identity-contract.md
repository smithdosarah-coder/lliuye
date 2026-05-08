# 候选 Unique Identity Contract v1.0 · 2026-05-08

> **状态**: outline · 待 Phase A common worker 完善
> **Owner**: common worker
> **背景**: PM 2026-05-08 反复痛点 (左右气泡不联动) 真根因 = 后端 candidate 没 id 字段 → 前端 find 命中错误. 本 contract 防再犯.

---

## 1. 硬规

任何 agent 出 candidate / customer / record 列表时, **每条必含 `id` 字段** (string, unique within list).

## 2. id 派生规则 (按优先级)

1. **uscc_<USCC>** — USCC 18 位合法时
2. **name_<md5前 12 位>** — 仅 name 有时
3. **cand_<idx:03d>** — 兜底 (idx 在 list 中位置)

(跟 entity-resolution-contract §3 一致 · 复用 EntityKey 逻辑)

## 3. 6 Agent 适用

| Agent | 列表对象 | id 字段位置 |
|---|---|---|
| channel | candidate (look-alike 候选) | candidate.id |
| report | 报告草稿 / 章节 | section.id |
| credit | 决策记录 | decision.id |
| alert | 在贷客户预警条目 | alert.id (按 client_entity_key 派生) |
| compliance | 政策命中条目 | hit.id |
| riskctrl | 回测样本 / DSL 规则 | rule.id |

## 4. 前端契约

- 前端 `setSelectedXxx(id)` + `find(it.id === selected)` 永不返第一项 (除非真选第一)
- 任何 list 渲染 `<Card data-cand-id={c.id}>` 必非空 / 非 "未获取"
- 测试: Playwright 真验 (`document.querySelectorAll('[data-cand-id]').forEach(c => assert(c.dataset.candId !== '未获取'))`)

## 5. 失败处理

- id 派生失败 (name 空 + USCC 空) → 用 `cand_<idx>` 兜底 · 不抛异常
- id 重复 (同 list 内出现 2 个相同 id) → 后端 raise · 客户端 warn

## 6. 待 Phase A common worker 补完

- [ ] 6 agent realtime_stream / api.py 各自 emit 时 id 字段必填的 wrapper / decorator
- [ ] 共享 `make_unique_id(name, uscc, idx)` helper (基于 EntityResolver)
- [ ] Playwright contract test (per agent · 真 hit production 验 id 字段)
- [ ] 已知 violator: 现仅 channel ALL IN 已修 (commit c074d43) · 5 agent 待 Phase B 各自接入
