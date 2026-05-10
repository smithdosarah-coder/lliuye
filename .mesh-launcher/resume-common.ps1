# resume-common.ps1 · COMMON worker (Phase A 基础设施冻结员)
# per docs/handoff/phase-r3-worker-runbook.md §A
# 启动后自动 cd worktree + 启 claude · 首句指令固定 · 等用户回车

$ErrorActionPreference = "Stop"

$ROOT = "D:\claude code\credit_report_agent_work_mesh\common"
$AGENT = "common"
$BRANCH = "feat/allin-common"

Write-Host "[$AGENT-launcher] 启动 $AGENT worker · worktree=$ROOT · branch=$BRANCH"

if (-not (Test-Path $ROOT)) {
  Write-Host "[$AGENT-launcher] FATAL · worktree 不存在 · 跑: git worktree add $ROOT $BRANCH"
  exit 1
}

Set-Location $ROOT

# 健康检查 (per CLAUDE.md Shell 健康)
git --version | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "[$AGENT-launcher] FATAL · git 不可用 · 重启 session"
  exit 1
}

# 显示当前状态
Write-Host ""
Write-Host "[$AGENT-launcher] 当前状态:"
git status --short | Select-Object -First 20
Write-Host ""
Write-Host "[$AGENT-launcher] 最近 5 commit:"
git log --oneline -5
Write-Host ""

# 首句指令 (用户复制粘贴 · 或直接 echo 到 stdin)
$FIRST_PROMPT = @"
COMMON resume: freezing shared contracts. 读 AGENT_IDENTITY.md (本 worktree 身份 · 写域 shared/ + docs/contracts/) + docs/contracts/{entity-resolution,candidate-identity,signal-commit}-contract.md (3 核心契约) + docs/working/allin-final-exec-2026-05-08.md §4.1 Phase A 任务清单 + docs/handoff/phase-r3-worker-runbook.md Phase A 段 + git log --oneline -10 · 然后写 RESUMED commit (含 verbatim 我等主 CLI GO)
"@

Write-Host "[$AGENT-launcher] 复制以下指令到 claude code (启动后):"
Write-Host "================================================="
Write-Host $FIRST_PROMPT
Write-Host "================================================="
Write-Host ""
Write-Host "[$AGENT-launcher] 启动 claude code..."

# 启 claude code · interactive mode · resume 已存 session
claude
