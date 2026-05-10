# .mesh-launcher · 6 worker resume 脚本

per `docs/handoff/phase-r3-worker-runbook.md` Phase A §A.2 第 3 件交付物.

## 用法

每个脚本对应一个 worker · 在该 worker 的窗口里跑:

```powershell
.\resume-common.ps1       # Phase A common worker (基础设施冻结员)
.\resume-report.ps1       # Phase B report worker
.\resume-credit.ps1       # Phase B credit worker
.\resume-alert.ps1        # Phase B alert worker (Managed)
.\resume-riskctrl.ps1     # Phase B riskctrl worker (Managed · MAX_ROWS=50000)
.\resume-compliance.ps1   # Phase B compliance worker (Managed · 原文 hash 红线)
```

每个脚本会:
1. 验 worktree 路径存在 (路径在脚本顶部 `$ROOT` 常量)
2. 跑 git --version 健康检查 (per CLAUDE.md Shell 健康)
3. 显示 `git status` + 最近 5 commit 让 worker 看到状态
4. 打印首句指令 (复制粘贴到 claude code)
5. 启 `claude` (interactive · resume 已存 session)

## worktree 创建 (一次性 · 主 CLI 跑)

```powershell
$ROOT = "D:\claude code\credit_report_agent_work_mesh"
cd "D:\claude code\credit_report_agent_work_mesh\common"  # 主 worktree

# 6 worktree 各加一份
git worktree add "$ROOT\report" -b feat/allin-report
git worktree add "$ROOT\credit" -b feat/allin-credit
git worktree add "$ROOT\alert" -b feat/allin-alert
git worktree add "$ROOT\riskctrl" -b feat/allin-riskctrl
git worktree add "$ROOT\compliance" -b feat/allin-compliance
# common 已有 (本 worktree)
```

## 桌面入口

`launch-all-LIUYE.bat` (待 Phase A 第 5 件交付物 · 桌面脚本) 一次启 7 个 cmd 窗口 ·
每个 cd 进对应 worktree + 跑该脚本.

## 设计意图 (per Q-054 mesh protocol)

- **物理隔离**: 每个 worker 一个 worktree · git history 独立
- **首句锁定**: resume 后第一句指令固定 · 防 worker 自行偏题
- **commit 即 signal**: worker 完成靠 signal commit (per signal-commit-contract) · 不靠 chat
- **本地 AGENT_IDENTITY.md**: `.gitignore` 排除 · worktree 自带 · 主 CLI 不污染

## 红线

- 不要把脚本里的 `$ROOT` 写死的路径改 (路径硬编码是 mesh 设计 · 跨机器复用走改 .bat)
- 不要在脚本里加业务逻辑 (脚本仅 launcher · 业务在 claude code session 内)
- 不要 silent 跳过 health check (`git --version` 失败必 abort · per CLAUDE.md Shell 健康)
