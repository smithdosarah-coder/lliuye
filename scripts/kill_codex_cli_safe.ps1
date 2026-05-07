<#
.SYNOPSIS
  Safely terminate codex CLI processes · 严格只杀 *\codex-cli\* 路径下的 codex.exe.

.DESCRIPTION
  per memory `feedback_codex_kill_filter.md` + handoff §4.3:
    · 老 CLI 已 2 次 broad-kill 命中大写 Codex.exe (PM 桌面 OpenAI Codex App) · 第 3 次 = revert
    · `taskkill /F /IM codex.exe` Windows case-insensitive · 大小写都中
    · `Get-Process codex | Stop-Process` 同样不安全
    · 唯一允许: 精确 PID + Path 验证 *\codex-cli\* 才 kill · 否则 refuse

  本脚本默认 dry-run · 列出候选 + 给出 verdict (kill / skip / refuse)
  · `-Force` 才真 kill
  · skip 任何 path 不在 codex-cli 下的进程 (尤其大写 Codex.exe = OpenAI 桌面 App 必 skip)

.PARAMETER Force
  实际执行 kill · 默认 dry-run only

.PARAMETER WhatIf
  PowerShell 标准 dry-run 标记 · 跟 -Force 互斥

.EXAMPLE
  .\scripts\kill_codex_cli_safe.ps1
  # dry-run · 列候选

.EXAMPLE
  .\scripts\kill_codex_cli_safe.ps1 -Force
  # 真 kill · 仅 *\codex-cli\* 路径下的 codex.exe

.NOTES
  Author: main CLI · R3v2 件 #1 Hygiene
  Signal: KILL-CODEX-CLI-SAFE-V1
#>

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
  [switch]$Force
)

$ErrorActionPreference = 'Stop'

$CODEX_CLI_PATH_PATTERN = '*\codex-cli\*'

Write-Host "=== kill_codex_cli_safe ==="
Write-Host "Mode: $(if ($Force) { 'KILL' } else { 'DRY-RUN' })"
Write-Host "Filter: Path -like '$CODEX_CLI_PATH_PATTERN' (大写 Codex.exe = OpenAI 桌面 App · 永远 skip)"
Write-Host ""

# Get all codex.exe processes (Windows case-insensitive · 这步会带出大写 Codex.exe 等同名进程)
$candidates = Get-Process -Name 'codex' -ErrorAction SilentlyContinue

if (-not $candidates) {
  Write-Host "(no codex processes found)"
  exit 0
}

$killed = 0
$refused = 0
$skipped = 0

foreach ($proc in $candidates) {
  $pid = $proc.Id
  $name = $proc.ProcessName
  $path = $proc.Path

  # 1. Path empty (system process · 没权限读 path) → refuse
  if ([string]::IsNullOrEmpty($path)) {
    Write-Host "[REFUSE] PID=$pid Name=$name Path=<unknown · 没权限/protected> → skip"
    $refused += 1
    continue
  }

  # 2. ProcessName 大小写 = 'Codex' (OpenAI desktop app) → 永远 skip · 不 kill
  if ($proc.ProcessName -ceq 'Codex') {
    Write-Host "[SKIP-DESKTOP-APP] PID=$pid Name=$name Path=$path → 大写 Codex = OpenAI 桌面 App"
    $skipped += 1
    continue
  }

  # 3. Path not under *\codex-cli\* → skip (可能是其他同名 binary)
  if ($path -notlike $CODEX_CLI_PATH_PATTERN) {
    Write-Host "[SKIP-NOT-CLI] PID=$pid Name=$name Path=$path → 不在 codex-cli 下"
    $skipped += 1
    continue
  }

  # 4. 通过验证 · 候选 kill
  if ($Force -and $PSCmdlet.ShouldProcess("PID=$pid Path=$path", 'Stop-Process')) {
    try {
      Stop-Process -Id $pid -Force -ErrorAction Stop
      Write-Host "[KILLED] PID=$pid Path=$path"
      $killed += 1
    }
    catch {
      Write-Host "[FAILED] PID=$pid Path=$path · $_"
    }
  }
  else {
    Write-Host "[CANDIDATE] PID=$pid Path=$path → would kill (use -Force)"
  }
}

Write-Host ""
Write-Host "Summary: killed=$killed  candidates=$($candidates.Count - $skipped - $refused)  skipped=$skipped  refused=$refused"

if (-not $Force) {
  Write-Host ""
  Write-Host "[DRY-RUN] no process killed · re-run with -Force to actually terminate"
}
