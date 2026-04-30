# Phase A 真 exit BUG 修复完整记录 · 2026-04-30

> Codex periodic final audit (`b680pl1mo` · 2026-04-30) verdict: NO-GO · 4 BUG 必修。
> 本 doc 完整记录每个 BUG 修复过程 · 含问题描述 + file diff + verify + 时间戳 · 不缩写。
> 后续复盘 / 接手人可从本 doc 完整还原"今天到底做了什么"。

## 0. 元信息

- **触发**: PM 2026-04-30 ultrathink 选 Plan A · "先修 BUG 保证完整结构 → 修完打里程碑 → 再走优化方案 (真三方辩论 ≥ 3 轮) → 全程文档化不缩写"
- **顺序约束** (PM 要求):
  1. 先修 BUG · 主 CLI 自己干 · 不并行三方辩论 R2 v2
  2. 修完打 git tag 里程碑 · 留可退回点
  3. 里程碑 commit + push + ECS deploy 后 · 再 fire 三方辩论 R2 v2
  4. R2 v2 + R3 v2 真发生在 Gemini 界面 (PM 可 verify conversation 多 turn)
- **Audit 来源**: `docs/audit/PHASE-A-FINAL-AUDIT-2026-04-30.md` (commit 61aa614 · Codex 真扫 8 硬线 verdict)

## 1. BUG 列表 (Codex 真扫 verdict)

| # | 硬线 | 问题描述 (人话) | 严重度 | 状态 |
|---|---|---|---|---|
| BUG-A | #5 Letterpress purge | 前端代码 4 处注释残留"Letterpress (老主题名)"字面 · 违反 CLAUDE.md §7 红线 (老 token 不允许复活 · 字面也算复活风险) | 中 (CI 检测得到 · 但视觉无影响) | ✅ 已修 |
| BUG-B | #3 Channel pilot | 前端漏文件 `web/src/lib/api/channel.ts` (其他 5 Agent 都有 · 唯独 channel 没有) · backend Q-041 4 字段 SSE 真 emit · 但前端没 type 接 | 中 (前端 inline 散写 · 不一致) | ⏳ 待修 |
| BUG-C | #6 handoff schema | `agent-handoff-schemas.md` 当前只 4 主链 · Agent2 风控完全没在 schema · 没反向链 (合规 BLOCK 后授信重评 / 授信缺章节回报告 等) | 中 (Phase B 任务看板做时会因 contract 缺而 spike) | ⏳ 待修 |
| BUG-D | #8 lint enforcement | 自动检查脚本在 (`scripts/lint/check_agent_naming_ssot.py` 跑通 OK) · 但 GitHub Actions workflow 完全没接 (`.github/workflows/` 目录都不存在) · CI 不会自动跑 | 高 (后续 PR 引入新违规无法自动阻塞) | ⏳ 待修 |

---

## 2. BUG-A 修复完整记录 (Letterpress 字面残留)

### 2.1 问题描述 (人话)

前端代码里有 4 处注释残留"Letterpress"这个老主题的名字。这些注释是 Phase A 早期 worker-A5 做 letterpress purge 时留下的"历史下架记录" · 内容是"Letterpress 主题已下架" 这种说明。

Codex 严格 audit 把字面残留也算违反 letterpress purge 红线。理由:
- CLAUDE.md §7 写"老 tokens 已下架·不允许复活"
- 字面残留容易**误导后续 worker** — 后续接手的人看到 "Letterpress" 字面 · 可能误以为还在用 · 或想"复活"
- 应该 0 字面 · 不留任何 token 名字 (包括注释里)

### 2.2 修复了哪些文件

**文件 1**: `web/src/components/shell/ThemeSwitch.tsx`
- 修改位置: 第 7-14 行 (函数文档注释)
- 原内容 (第 9 行): `* Letterpress (crimson) / Nebula (紫粉) 已下架 — 用户判老 DEMO 视感 / 重 saturate。`
- 改成: `* 历史下架的老主题 (per CLAUDE.md §7 红线) · 不复活。`
- 同时第 7 行加了备注: `* 4 主题切换器（Canvas / Matcha / Dusk / Ink · platform shell-v2 lock 定稿）。`

**文件 2**: `web/src/app/globals.css`
- 修改位置 1: 第 17-21 行 (头部 doc 注释)
- 原内容 (第 18 行): `* Globals · Phase A5 post-Letterpress purge (2026-04-29)`
- 改成: `* Globals · Phase A5 post-purge (2026-04-29 · 老主题已下架 per CLAUDE.md §7)`
- 修改位置 2: 第 99-103 行 (历史 cleanup 注释)
- 原内容 (第 101 行): `驱动 (水墨宣纸→深墨 · 替代 v1 Letterpress · CLAUDE.md §7).`
- 改成: `驱动 (水墨宣纸→深墨 · 替代历史老主题 · per CLAUDE.md §7).`

**文件 3**: `web/src/app/tokens.css`
- 修改位置: 第 112 行 (Ink 主题 token block 上方注释)
- 原内容: `/* —— Ink (水墨 · 宣纸) · 2026-04-20 取代 Letterpress 进入切换器 —— */`
- 改成: `/* —— Ink (水墨 · 宣纸) · 2026-04-20 取代历史老主题进入切换器 —— */`

### 2.3 Verify 怎么做

跑 grep 全 `web/src` 树 · 看 0 个 `Letterpress` / `crimson` / `--color-brass` / `--color-ink` / `ink-brush-hr` 字面命中:

```bash
grep -rn "Letterpress\|crimson\|--color-brass\|--color-ink\|ink-brush-hr" "D:/claude code/credit_report_agent_work/web/src"
```

### 2.4 Verify 结果

```
(0 lines · 命中数 = 0)
```

✅ **0 残留** · BUG-A 修复完毕。

### 2.5 时间戳

- 修复 ThemeSwitch.tsx: 2026-04-30 (Edit tool · 单 1 处)
- 修复 globals.css: 2026-04-30 (Edit tool · 2 处)
- 修复 tokens.css: 2026-04-30 (Edit tool · 1 处)
- Verify grep: 2026-04-30
- 总耗时: ~10 min
- 修复者: 主 CLI (Claude Opus 4.7 · single session)

---

## 3. BUG-B 修复 (待修 · 加 web/src/lib/api/channel.ts)

待修复。计划见 §1 列表。

## 4. BUG-C 修复 (待修 · 补 handoff schema)

待修复。计划见 §1 列表。

## 5. BUG-D 修复 (待修 · 加 .github/workflows/lint-contracts.yml)

待修复。计划见 §1 列表。

---

## 6. Phase A 真 exit 里程碑 (4 BUG 全修后)

修完所有 4 BUG → 主 CLI fire Codex re-audit → 通过 → 打 git tag `phase-a-exit-bugfix-2026-04-30` (可退回点) → 写 `docs/audit/PHASE-A-EXIT-MILESTONE-2026-04-30.md` (含全 8 硬线 verdict + 回退命令) → push GitHub + ECS deploy 含 build。

之后才 fire 三方辩论 R2 v2 + R3 v2 (per PM 顺序 · 不并行)。
