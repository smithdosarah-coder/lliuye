@echo off
REM ---------------------------------------------------------------------------
REM Claude 运行环境 helper：代理 + Git Bash 路径
REM 由 start_claude.bat 调用，不要直接双击运行
REM ---------------------------------------------------------------------------
set "https_proxy=http://127.0.0.1:7897"
set "http_proxy=http://127.0.0.1:7897"
set "ALL_PROXY=http://127.0.0.1:7897"
set "CLAUDE_CODE_GIT_BASH_PATH=D:\Git\usr\bin\bash.exe"
claude
