# Session Handoff · 2026-04-24 · multi-cli-mesh Skill 升级方案交接

> 本文档是 /clear 前写给下一个主 CLI 的交接。核心事项：**skill 升级方案已定稿但未执行**，3 个决策点未拍板 → 下个 CC 的第一件事是**拉用户拍板**，不要空跑执行。

---

## 0. 一眼看 · Verdict

- **现状**：`~/.claude/skills/multi-cli-mesh/` 还是 **v2026-04-19 老版**（SKILL.md mtime 2026-04-19，scripts 里跑的还是老 `mesh_status.py` / `mesh_launch.py` / `mesh_watch.py`）
- **盲点**：昨晚 2026-04-23 21:50-22:28 产出的 **P1-P5 orchestrator 五件套 + mesh-status.json schema v2**（1534 行代码 + 6 份测试）**全部只在 repo `scripts/orchestrator/`，未回流到 skill**
- **下一步**：按本文档 §3 方案 12 步执行。**不要直接打包上传**——现在打包就是 2026-04-19 旧版 + 漏掉 5 模块核心。
- **Blocker**：用户有 3 个未拍板决策（§4），不答就没法执行

---

## 1. 昨天"5 个问题"是哪 5 个（用户原话复核锚点）

用户 2026-04-24 复盘时问："昨天最后要解决的 5 个问题确定都封装到新的 skills 里面了吗"。所指 5 个 = **orchestrator P1-P5 五件套**（scaffold commit `c219379 scaffold(orchestrator): foundation lib for P1-P5 modules` 明确列出）：

| # | 模块 | 解决的痛点 | 落地 commit | 文件/行 | **当前在 skill？** |
|---|---|---|---|---|---|
| 1 | **P1 Validator** | commit 没带 `Signal:` trailer → 批次动作失联、mesh 看板失真 | `f9fb1d9` | `validator.py` 80 行 + `hooks/commit-msg` 24 行 | ❌ **不在** |
| 2 | **P1 Scoreboard** | 主 CLI 看不到全局 mesh 状态；cc_monitor 没数据源 | `6d0be17` + `ea9a994`（JSON 集成）+ `220554b`（UTF-8 修复）+ `7ed0b31`（stuck_event schema v2） | `scoreboard.py` 309 行 | ❌ **不在**；skill 里的是老 `mesh_status.py`（只出 ASCII，无 JSON） |
| 3 | **P2 Watchdog** | worker 窗口挂了/卡住没人发现；长期闲置无探测 | `0bc4bc4` | `watchdog.py` 274 行 | ❌ **不在**；skill 里有老 `mesh_watch.py` 但功能远弱（无 stuck 分类、无 JSON events） |
| 4 | **P3 Recovery** | worker 卡住了怎么重启（且必须无自动执行风险） | `ddc7754` | `recovery.py` 194 行 | ❌ **不在** |
| 5 | **P5 Launcher** | 新 worktree 入驻 mesh 繁琐；identity + mesh.json 注册易漏 | `04a9462` | `launcher.py` 241 行 | ❌ **不在**；skill 里有老 `mesh_launch.py` 但无 register 能力 |

> **注**：commit 编号跳过了 P4（P1/P1/P2/P3/P5），是"5 模块 / 4 阶段"的产物，不是漏了一个模块。

**结论**：**5 问题 = 5 模块 = 0 个在 skill 里**。全部留在 repo `scripts/orchestrator/`，等下面 §3 第 1 步 `cp -r` 整包搬迁。

---

## 2. 附加盲点（5 模块之外的昨天沉淀）

handoff `session-2026-04-23-product-hardening-dispatch.md` 里还有一批 **tacit 规则**，是 mesh 协议层但口头约定，未落入 skill 任何 protocol 文档：

| 规则 | 来源 | 应落位 |
|---|---|---|
| 演示型前端 **4 硬闸**：GO + TaskCreate + 方案先行 + Authorized-By trailer | memory `feedback_red_zone_discipline` + 2026-04-23 handoff §2.4 | 新 `protocols/red-zone-gates.md` |
| **A-012.D SHA-immutable + E merge-only + signal-await** 三 worker 纪律 | memory `feedback_worker_phase_discipline` + `feedback_signal_await_semantics` | 新 `protocols/worker-phase-discipline.md` |
| **收到 signal 的 4 类响应 playbook**（ACK / DONE / RFC-RAISED / READY-FOR-REVIEW） | 2026-04-23 handoff §5 | 新 `protocols/signal-playbook.md` |
| **`mesh-status.json` schema v2 契约**（`stuck_event` / `stuck_summary` 字段，cc_monitor 消费方稳定性保证） | commit `7ed0b31` + `ea9a994` | 新 `references/mesh-status-json-schema.md` |
| **P1→P5 自愈分层架构**（Validator 输入 gate / Scoreboard 真相源 / Watchdog 探测 / Recovery 生成 / Launcher 入驻） | `scripts/orchestrator/__init__.py` docstring | 新 `references/self-healing-architecture.md` |

---

## 3. 完整升级方案（12 步，每步独立 commit）

### 目录 diff

```
multi-cli-mesh/
├── SKILL.md                          🔄 重写 v2
├── protocols/
│   ├── commit-signal-registry.md     🔄 扩增已知 Signal 名册（和 hooks/commit-msg 对齐）
│   ├── decision-log-protocol.md      ✓ 保留
│   ├── shared-change-protocol.md     ✓ 保留
│   ├── signal-playbook.md            ✨ 新
│   ├── worker-phase-discipline.md    ✨ 新
│   └── red-zone-gates.md             ✨ 新
├── scripts/
│   ├── orchestrator/                 ✨ 新 · 整包从 repo scripts/orchestrator/ 搬 1534 行
│   │   ├── validator.py              (80)
│   │   ├── scoreboard.py             (309)
│   │   ├── watchdog.py               (274)
│   │   ├── recovery.py               (194)
│   │   ├── launcher.py               (241)
│   │   ├── lib/{signal,mesh,identity,git_helpers}.py (393)
│   │   ├── hooks/{commit-msg, install.sh}
│   │   └── tests/test_*.py (6 份)
│   ├── tab_welcome_main.cmd          ✓ 保留
│   ├── tab_welcome_worker.cmd        ✓ 保留
│   ├── mesh_status.py                ❌ 删（被 scoreboard 超集）
│   ├── mesh_launch.py                ❌ 删（被 launcher 超集）
│   └── mesh_watch.py                 ❌ 删（被 watchdog 超集）
├── templates/                        ✓ 三份保留
├── checklists/
│   ├── open-window.md                🔄 路径改 scoreboard.py
│   ├── close-window.md               🔄 路径改 scoreboard.py
│   └── install-hooks.md              ✨ 新（怎么装 commit-msg hook）
└── references/
    ├── bootstrap.md                  🔄 路径重定向 + Watchdog/Recovery 启用章节
    ├── self-healing-architecture.md  ✨ 新
    └── mesh-status-json-schema.md    ✨ 新
```

### 实施顺序

| # | 动作 | 估工 | 备注 |
|---|---|---|---|
| 1 | `cp -r scripts/orchestrator/` → skill `scripts/orchestrator/` | XS | sys.path hack 自包含，开箱跑 |
| 2 | 跑 skill 内 `pytest scripts/orchestrator/tests/` | XS | 打包前验收基线 |
| 3 | 写 `protocols/signal-playbook.md` | S | 从 2026-04-23 handoff §5 搬 |
| 4 | 写 `protocols/worker-phase-discipline.md` | S | 合并 2 个 feedback memory |
| 5 | 写 `protocols/red-zone-gates.md` | S | 从 memory red_zone_discipline 搬 |
| 6 | 扩增 `protocols/commit-signal-registry.md` | S | 和 hooks/commit-msg 已知名单对齐 |
| 7 | 写 `references/self-healing-architecture.md` | M | P1→P5 分层图（文本） |
| 8 | 写 `references/mesh-status-json-schema.md` | S | 反推 commit `7ed0b31`/`ea9a994` |
| 9 | 写 `checklists/install-hooks.md` | XS | 3-5 步 |
| 10 | 更新路径引用（open-window / close-window / bootstrap） | XS | grep `mesh_status.py\|mesh_launch.py\|mesh_watch.py` 全替换 |
| 11 | 重写 `SKILL.md` v2 | M | 7 节结构 |
| 12 | 删/shim 3 老脚本（依决策点 2 定） | XS | 步骤 10 零遗漏后再动 |

---

## 4. 🚧 BLOCKING · 3 个决策点（下个 CC 第一件事就问用户）

| # | 问题 | 选项 | 我（2026-04-24）的建议 |
|---|---|---|---|
| 1 | repo `scripts/orchestrator/` 和 skill 搬过去后两份怎么同步？ | (A) repo 删，项目引 skill 路径 (B) 保留两份，skill canonical，人工同步 (C) symlink | 🟢 **B**：渐进，等下一次 skill eval 通过再收敛；A 引入循环依赖（项目跑起来需先装 skill） |
| 2 | 3 个老脚本（mesh_status/mesh_launch/mesh_watch）删还是留 deprecation shim？ | (A) 直接删 (B) 留 shim 打 deprecation warning | 🟡 **B**：前面 grep 到 ≥5 处硬编老路径（其他 worktree 的 identity / kickoff 文档），shim 减少一次性大改动 |
| 3 | skill 打包目标受众？ | (A) 私人用 (B) 公开 `~/.agents/skills/` 仓库 (C) 飞书团队分享 | **需用户明确**——影响打包格式（tar / git repo / SKILL.md only）+ 脱敏范围 |

---

## 5. 打包前验收 checklist（等方案 12 步跑完后核对）

- [ ] `pytest scripts/orchestrator/tests/` 全绿（6 份测试）
- [ ] `py scripts/orchestrator/scoreboard.py` 在一个全新 mesh 项目独立能跑（输出 markdown + mesh-status.json schema v2）
- [ ] `py scripts/orchestrator/launcher.py register test-wt --path /tmp/foo --branch feat/test --role worker` 生成正确 mesh.json 条目 + identity 脚手架
- [ ] SKILL.md `§2 何时触发` 表覆盖 5 场景（含 validator hook 装机 / watchdog 起新 worktree）
- [ ] 全 skill 树 `grep -r "mesh_status\.py\|mesh_launch\.py\|mesh_watch\.py"` = 0 命中（或仅 shim 自身）
- [ ] `references/mesh-status-json-schema.md` 覆盖 schema v2 `stuck_event` / `stuck_summary` 字段契约

---

## 6. 下个 CC 的第一步（playbook）

1. 读 `AGENT_IDENTITY.md` + 清单所有文件（含本文档，是清单项 13）
2. 跑 `git log --format='%h %s' -20 chore/l0-infra` 看最后 signal = `SKILL-UPGRADE-PLAN-STAGED`
3. **不要立即执行 §3**——先拉用户拍板 §4 的 3 个决策点
4. 拍板后跑 TaskCreate 列 12 步，按顺序执行，**每步独立 commit**（用户红线 4 硬闸）
5. 当前批次 Product Hardening Phase 1 Batch 1 的 4 worker 仍等 ACK（`mesh_status` / 新版 scoreboard 查），不受本 skill 升级影响——本升级是 orchestrator 内部工具，不触碰 worker 分支

---

## 7. 参照引用

- 昨天产出的 orchestrator 代码：`scripts/orchestrator/`（本 repo）
- 昨天 tacit 规则来源：`docs/handoff/session-2026-04-23-product-hardening-dispatch.md` §2.4 / §5
- 前次方案原文（2026-04-24 13:xx 对话）：本 session 上一轮我给用户的 "Skill 升级方案清单 · v2026-04-24"（已落本文档 §3）
- cc_monitor 消费契约：`D:\claude code\cc_monitor\` 独立项目，走 `docs/handoff/mesh-status.json` 耦合，**不进 skill**（它是 consumer，skill 只管 producer）

---

**签名**：chore/l0-infra @ 2026-04-24（用户 /clear 前写）
**接力 anchor commit**：本文件 commit 将附 `Signal: SKILL-UPGRADE-PLAN-STAGED`
