@echo off
REM ---------------------------------------------------------------------------
REM 一键启 Claude Code · 自动提示 resume
REM 行为:
REM   1. 显当前 git status (production HEAD + 最近 commit)
REM   2. 显最新 KT path + resume prompt 模板 (PM 复制粘贴)
REM   3. 启 wt new-tab + claude-env + Claude Code
REM 2026-05-07 改写 · 加 KT pre-check (handoff to next main CLI)
REM ---------------------------------------------------------------------------

echo.
echo ============================================================
echo   Claude Code · Main CLI Launcher
echo   Worktree: %~dp0
echo ============================================================
echo.

REM Git status (最新 commit + production HEAD)
echo [1] Git status:
pushd "%~dp0"
git log --oneline -3 2>nul
echo.
git log origin/main -1 --oneline 2>nul
popd
echo.

REM KT path + resume prompt
echo ============================================================
echo [2] 必读 KT (按顺序):
echo   - AGENT_IDENTITY.md
echo   - docs\handoff\HANDOFF_TO_NEXT_MAIN_CLI_2026-05-07.md  (latest close-out)
echo   - docs\reset\product-readiness-grounded-2026-05-07.md  (grounded debate)
echo   - docs\reset\phase-c-charter-2026-05-06.md             (Phase C charter)
echo.
echo [3] 新 CLI 第一句 paste:
echo.
echo   读 AGENT_IDENTITY.md 和里面列的所有文件 . resume 状态后等我指令.
echo.
echo ============================================================
echo.

REM 如果有 wt (Windows Terminal) 用 new-tab · 否则直接启 cmd
where wt >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [4] 启 Windows Terminal new-tab...
    wt -w 0 new-tab --title "claude-main" -d "%~dp0" -- cmd /k "%~dp0scripts\claude-env.bat"
) else (
    echo [4] wt not found . fallback to direct cmd...
    start "claude-main" cmd /k "cd /d %~dp0 && %~dp0scripts\claude-env.bat"
)
