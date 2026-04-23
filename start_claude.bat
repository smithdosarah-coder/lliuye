@echo off
REM ---------------------------------------------------------------------------
REM 用 Windows Terminal 启动 Claude Code
REM 行为：在 wt 已开窗口里加一个新 tab；若 wt 未开则新开窗口
REM 代理 + Git Bash 配置由 scripts\claude-env.bat 在 tab 子 shell 中注入
REM ---------------------------------------------------------------------------
wt -w 0 new-tab --title "claude-main" -d "%~dp0" -- cmd /k "%~dp0scripts\claude-env.bat"
