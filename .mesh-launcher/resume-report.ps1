# resume-report.ps1 · REPORT worker (Phase B agent 改造)
# per docs/handoff/phase-r3-worker-runbook.md §B

$ErrorActionPreference = "Stop"

$ROOT = "D:\claude code\credit_report_agent_work_mesh\report"
$AGENT = "report"
$BRANCH = "feat/allin-report"

Write-Host "[$AGENT-launcher] 启动 $AGENT worker · worktree=$ROOT · branch=$BRANCH"

if (-not (Test-Path $ROOT)) {
  Write-Host "[$AGENT-launcher] FATAL · worktree 不存在 · 跑: git worktree add $ROOT $BRANCH"
  exit 1
}

Set-Location $ROOT

git --version | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "[$AGENT-launcher] FATAL · git 不可用 · 重启 session"
  exit 1
}

Write-Host ""
Write-Host "[$AGENT-launcher] 当前状态:"
git status --short | Select-Object -First 20
Write-Host ""
Write-Host "[$AGENT-launcher] 最近 5 commit:"
git log --oneline -5
Write-Host ""

$FIRST_PROMPT = @"
REPORT resume: scope locked, checking signals. 读 AGENT_IDENTITY.md (本 worktree 身份 · 写域 agent_report/ + web/src/app/archive/report/) + docs/contracts/{entity-resolution,candidate-identity,signal-commit}-contract.md (3 核心契约) + docs/handoff/phase-r3-worker-runbook.md Phase B §B.2 (6 step 改造) + git log --oneline -10 · 然后写 RESUMED commit (含 verbatim 我等主 CLI GO)
"@

Write-Host "[$AGENT-launcher] 复制以下指令到 claude code:"
Write-Host "================================================="
Write-Host $FIRST_PROMPT
Write-Host "================================================="
Write-Host ""
Write-Host "[$AGENT-launcher] 启动 claude code..."

claude
