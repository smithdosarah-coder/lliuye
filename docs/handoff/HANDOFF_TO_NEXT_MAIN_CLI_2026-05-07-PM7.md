# HANDOFF · TO NEXT MAIN CLI · 2026-05-07-PM7 (产品体验 R3 v2 收敛后)

> **PM 指令**: 当前主 CLI context ~75-85% · R3 v2 12-14d + B/C 并行扛不住 · KT 100% 承接.
> 新窗口第一句 paste: **「读 AGENT_IDENTITY.md 和里面列的所有文件 · resume 状态后等我指令.」**

---

## 0. 一句话定位

**当前阶段**: 产品体验闭环修复 (R3 v2 · PM 7 问题 · ~12-14d)
**最新 commit**: `31d24d8` (PB#5 auth loader + deploy script 加 npm install)
**production**: `https://liuye.me/login` · 评级 C+ → R3 v2 ship 后预期 B/B+
**前一阶段**: PB#1-5 全 ship (SSOT + zod + SSE abort + agent_credit cleanup + Agent3 PIPL)

---

## 1. 必读 (按顺序 · ~20 min)

1. **`CLAUDE.md`** (项目规范 · 自动加载) — §3.5.1 #6 数据时效 · §13.1 改完即部署 · §15 SSOT 优先级
2. **`docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-07-PM7.md`** ⭐ (本 doc)
3. **`docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-07.md`** (上一次 handoff · PB#1 ship 后)
4. **`docs/reset/product-readiness-grounded-2026-05-07.md`** (Claude+Codex grounded R1+R2+R3 真辩论)
5. **`docs/handoff/decisions-log.md` tail -80** (Q-053 PB#2 governance · 最近 PM 拍板)
6. **`.tmp/codex-r2-leverage-output.md`** + **`.tmp/codex-r2-leverage-output-v2.md`** (双 Codex R2 · R3 v2 reconcile 依据)
7. **`.tmp/claude-r1-product-audit-output.md`** (Claude R1 · 产品体验 4 截图 audit)

---

## 2. R3 v2 完整方案 (PM 拍 · 立即开干)

### 背景 · PM 7 问题 (verbatim · 必 grounded)

1. 平台功能不完整 · 排版 BUG
2. 大面积空白
3. 排版不整齐
4. DEMO 和真实情况没区分
5. 前端 MOCK 数据 · 按键混乱 · 数据混乱
6. 前端交互导致后端无法验证
7. 画布功能 + 任务看板摆设

### R3 v2 plan (12-14d 真闭环成本 · 双 AI 真辩论收敛)

**P0 · 立即修 · 5.5-6.5d**

| # | 修啥 (说人话) | 工时 | 用 skill |
|---|---|---|---|
| 1 | 写脚本扫所有"假数据流入点" + 跑 Playwright 自动化截图对比 (改完不用人肉验) | 0.5d | webapp-testing |
| 2 | 后端给的"真假"标识 (sse_envelope `data_source` enum 已有) · 前端真用起来 — **PM #4 根因** | 1-1.5d | systematic-debugging |
| 3 | IM 发消息失败要让用户看见 (现在 silent 吞掉) — **PM #6 根因** | 1d | systematic-debugging |
| 4 | /today 假数字删 + 显空态/来源标 (repo 无 /api/today endpoint · 不强接) | 1d | (无 skill) |
| 5 | /warroom 任务看板真接后端 + 修 `rejected` 字段不一致 bug | 1.5-2d | dispatching-parallel-agents (后端+前端 2 sub-agent) |
| 6 | event-bus audit 改存数据库 (现仅内存 · 刷页丢) | 0.5d | (无 skill) |

**P1 · 本周 · 6.25-7.75d**

| # | 修啥 | 工时 | 用 skill |
|---|---|---|---|
| 7 | 6 workspace 默认空骨架 → "今天该做啥+最近活" — **PM #2 主战场** | 4-5d | dispatching-parallel-agents (派 **3 sub-agent** · 不是 6 散 · Codex 强反对 6 散) |
| 8 | PDF / 派单等 disabled 占位实装/删 — PM #1 | 1-1.5d | brainstorming |
| 9 | 顶部 "+ 4 按钮" 跟 view tab 重复 · 重新设计 — PM #5 | 0.5d | brainstorming |
| 10 | 加载转圈 / 演示条 / tag 排版 fix — PM #3 | 0.75d | frontend-design |

**P2 · 后做 · 2-3d**: 画布 PanelCanvas (拍删/真做) + 看板 CSS

**Hygiene · 0.75-1d**: `kill_codex_cli_safe.ps1` (防误杀 PM Codex App · 已 2 犯) + `audit_mock_badges.sh` + `audit_inline_style.sh`

### 双 AI 共识反对 Claude R2 v1 的 4 处 (R3 v2 已修正)

| # | Claude R2 v1 错 | Codex 改正 (双 sub-agent 一致) |
|---|---|---|
| 1 | "派 6 sub-agent 0.5-1d 6 workspace reframe" | 6 workspace 状态机各异 · 至少 2-3d · 改 **3 lane** |
| 2 | "mock badge 0.25d 派 codex 脏活" | 不是 UI 贴标 · 是 **data_source provenance SSOT 根因** |
| 3 | "silent fallback 删" | 一刀删丢可观测性 · 改 **fail-visible banner + retry** |
| 4 | "TodayContent 接 backend /api/today 1-2d" | repo 无该 endpoint · 真路径 = 空态 + 来源标 |

---

## 3. B + C 产品力升级 (主 CLI sequential ship 完 + 派 sub-agent 并行 · ~3d)

PM 提示: "修体验"和"升能力"在不同代码层 · 0 文件冲突 · 应**并行**。新主 CLI 在 R3 v2 12-14d 期间派 sub-agent 跑:

### B · Agent1 获客 (3 候选 · 各 0.5-1d)

| # | 升级 | 工时 | demo 直观看到 |
|---|---|---|---|
| **B1** | 候选评分 5 维度化 (LLM 只打分 · 代码加权 · 卡兹克借鉴) | 1d | 候选排序更准 · 可解释 |
| B2 | PITCH_GEN_PROMPT few-shot 扩 (现只 1 示例) | 0.5d | 第一通电话切入语 |
| B3 | Tavily 多 query 召回 | 1d | 候选量 3-5 → 8-15 |

### C · Agent2 策略 (3 候选)

| # | 升级 | 工时 |
|---|---|---|
| **C1** | DSL 生成支持复杂条件 (OR / 嵌套 / 时间窗口 / NOT) | 0.5d |
| C2 | 回测可视化 (KS 曲线 + per-rule FPR) | 1d |
| C3 | 误杀/漏杀真归因 | 1d |

**PM 拍板未定** — 主 CLI 建议 B1+C1 (1.5d 共 · 跟 R3 v2 P0 #1 同时启)。Codex 跑产品力可行性辩论尚未启 (新主 CLI 接 · 用 gpt-5.5 + xhigh default)。

---

## 4. ⚠️ 关键 reframe (新主 CLI 必守)

### 4.1 Codex 用法 reframe (PM 2026-05-07 拍 · 已改 ~/.claude/CLAUDE.md)

- ❌ **删除"Codex 只做脏活"路径** (实战证明 codex 30+ 处机械改 81-180s · 加 stuck 风险 · 不省时)
- ✅ Codex 真价值 = **深度独立审 + 双 AI 真辩论 (R1/R2 reconcile)** · per `feedback_codex_debate_default.md`
- ✅ **default model = `gpt-5.5` · reasoning = `xhigh`** (PM 2026-05-07 拍 · 除非 PM 显式说用别的 · per memory `reference_codex_default_config.md`)
- ✅ stuck fallback 链: `gpt-5.5 + xhigh` → `gpt-5.3-codex-spark + low` (81s 实战最稳)

### 4.2 mesh ⚠️ 必启 (前主 CLI 判断错 · 已纠正)

**前主 CLI 误判**: "用 sub-agent 不复活 mesh" — PM 2026-05-07-PM7 catch 戳穿: sub-agent 是 OS 子进程 · 完成报告**仍回主 CLI 上下文** · 新主 CLI 单 CLI + sub-agent 跑 R3 v2 12-14d 必爆 context (前主 CLI ~30 commits 已经爆了)。

**真"主 CLI 不被脏活稀释"** = **mesh worker** (独立 cmd 窗口 + 独立 git worktree + 独立 claude 实例 + git signal 通讯)。

**mesh 工具其实齐全** (前主 CLI 之前误信 codex 误判):
- `scripts/orchestrator/` 完整 P1-P5: validator (commit 钩) · scoreboard (状态) · watchdog (poll) · recovery (重启) · launcher (register)
- `mesh.json` 有 worktree registry
- 0 worker 只是 Sprint 2 后全 release · 不是工具问题

**新主 CLI 必启 mesh** (resume 后第一件):
1. 加载 multi-cli-mesh skill (skill 触发表 "多 CLI 并行项目 → multi-cli-mesh")
2. 按 R3 v2 任务划分 worker (建议: 3 worker = R3-frontend / R3-backend / R3-test)
3. `py scripts/orchestrator/launcher.py register <name> --path ... --branch ... --role ...`
4. 改 `C:/Users/Mr.S/Desktop/launch-all-LIUYE.bat` (现 4 cmd · 改成主 CLI + R3 worker)
5. 让 PM 双击 launch · 多 cmd 窗口起 · 主 CLI 通过 decisions-log Q-NNN 派活

### 4.3 误杀 PM Codex 桌面 App 教训 (今晚已 2 犯 · 第 3 次 = revert)

- 大写 `Codex.exe` = OpenAI 桌面 App · **绝不能碰**
- 小写 `codex.exe` = codex CLI · 唯一允许 kill
- **禁止**: `taskkill /F /IM codex.exe` · `Get-Process codex | Stop-Process` (Windows case-insensitive)
- **唯一允许**: 精确 PID + `(Get-Process -Id $pid).Path -like "*\codex-cli\*"` verify 后才 kill
- per memory `feedback_codex_kill_filter.md`

### 4.4 framing 防错 (今晚 PM catch 我 4 次)

| # | 我犯过的 framing 错 | 真因 |
|---|---|---|
| 1 | "客户走访时机" 当决策 anchor (1 周 / 2-3 周 / 4 周 三档) | PM 没拍走访时间窗口 · 我**虚构** |
| 2 | "升级最优秀的 Agent6" (评级单维度刷分) | 应该升**最弱的** · 不是最强的加风险 |
| 3 | "改 Agent5 合规审计深度" | 银行内部审计员看 · 不是客户 demo 路径 |
| 4 | "修体验 vs 升能力 sequential" | 0 文件冲突 · 真可并行 |

**新主 CLI 防错**:
- PM 必拍未拍的事 ≠ 已定 (走访时机 / agent 升级方向 / 演示窗口)
- 工程师视角 (评级 / 审计 / SSOT) ≠ 产品视角 (用户 demo / mock 真假 / 摆设)
- 两件事不同代码层时 · 默认假设可并行 · 不是 sequential

---

## 5. R3 v2 第 1 件 (PM 已 GO · 但未真做 · 新主 CLI 接)

**件 #1**: Playwright `*-pilot-4gate.spec.ts` 跑通 + 写 audit 脚本扫所有 mock 混入点

**现状**:
- 5 个 spec 已存在 (`web/tests/regression/{alert,channel,compliance,credit,report}-pilot-4gate.spec.ts`)
- `web/package.json:9` test:snap = `playwright test`
- audit 脚本未写 (`scripts/audit_mock_badges.sh` / `audit_pm7_mock_sources` 不存在)

**新主 CLI 第 1 件干**:
1. 跑 `cd web && npx playwright test web/tests/regression/*-pilot-4gate.spec.ts` 看是否绿
2. 写 audit 脚本 (rg 扫 `@/lib/mock/*` import + `seed*` 默认 · per Codex R1 file:line evidence)
3. 配 CI gate (改完自动跑 spec)

**预期工时**: 0.5d

---

## 6. PM 工作偏好 (per CLAUDE.md global · 必守)

- 不谄媚 · 不夸 PM 想法 · 不开头加"当然可以"
- 默认中文 · 代码/命令/变量名英文
- **结论先行** · 默认 terse · 多档分级 (🔴/🟡/🟢)
- commit 粒度 = TaskCreate 粒度 · 一件即 commit
- **方案先行** · 中等以上任务先出方案再动手
- **不再自加 UI 没问 PM** (PM 5/7 verbatim)
- **不动视觉** (Q-047 视觉冻结 baseline)

---

## 7. Codex 协作 (Q-043 v2 + PM 2026-05-07 reframe)

- **default**: `gpt-5.5` + `xhigh` + `read-only` (PM 拍)
- **stuck fallback 链**: `xhigh` → `medium` → `gpt-5.3-codex-spark + low` (81s 实战)
- **真双辩论流程** (PM 5/7 verbatim):
  1. Claude 独立 lock R1 (不告诉 codex 立场)
  2. Fire codex with ONLY 命题
  3. R1 互看 → discuss → R2 reconcile
- **派 codex 走 sub-agent + codex skill** (per CLAUDE.md "重任务起 Agent · 主上下文不被脏活稀释")

---

## 8. Resume 后第一组动作

```bash
cd "D:/claude code/credit_report_agent_work"
git log --oneline -20             # 最近 commit
git log origin/main -1 --oneline  # production HEAD
tail -80 docs/handoff/decisions-log.md   # 最近 PM 拍板
py -m pytest tests/shared/test_ssot_prompts.py -v   # PB#1+#2 防线 24/24
```

汇报样例:
```
Resume 完成 · KT 100% 承接.

我是: main CLI · main 分支 · D:/claude code/credit_report_agent_work
最新 commit: 31d24d8 (PB#5 auth loader + deploy script fix)
production: https://liuye.me/login · 评级 C+

R3 v2 plan (PM 7 问题 · 12-14d):
- P0 5.5-6.5d (件 #1-6 · 主 CLI 主线)
- P1 6.25-7.75d (件 #7-10 · 派 3 sub-agent 并行 workspace reframe)
- P2 2-3d
- Hygiene 0.75-1d
- B+C 升级 (Agent1 5 维度 + Agent2 复杂 DSL · 1.5d 并行)

关键已 ship: PB#1 8 段 SSOT · PB#2 6 Agent helper · PB#3 Agent3 PIPL · PB#5 zod+SSE abort
关键未启: R3 v2 件 #1 (Playwright + audit 脚本 · 0.5d)
Codex 产品力辩论 (gpt-5.5 + xhigh · 待新 CLI 派)

PM 拍 · GO 件 #1?
```

---

## 9. 危险区 (今晚踩过 · 新主 CLI 避免)

1. **broad kill codex** — 已 2 次误杀 PM Codex App · 第 3 次 = stop the line + revert
2. **虚构 framing anchor** — 走访时机 / 评级单维度 / sequential · 4 次被 PM catch
3. **xhigh + 长 prompt** — 实测 stuck (主 CLI 直 fire / sub-agent 都遇到) · 必走 sub-agent + 短 prompt + fallback 链
4. **mesh 误判 "工具空"** — 实际 P1-P5 自愈 + scoreboard.py + watchdog.py + 等都齐全 · 只是没人启 worker

---

## 10. ECS 部署 (per CLAUDE.md §13.1 · 改完即部署默认)

```bash
bash scripts/deploy_to_ecs.sh                # 完整 (含 web build · 5-10 min)
bash scripts/deploy_to_ecs.sh --skip-build   # 仅 backend restart
```

`scripts/deploy_to_ecs.sh` 已 PB#5 加 npm install step (防新 dep 漏装致 build fail)

---

**Authored**: Main CLI · 2026-05-07-PM7 (commit `31d24d8` close-out · KT 触发原因 = context ~75-85% + 4 framing 错累积)
**File status**: 入 git history (跟 commit 30ad5af 同模式)
**Signal**: HANDOFF-2026-05-07-PM7-PRODUCT-EXPERIENCE-R3V2-DONE
