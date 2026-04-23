@echo off
setlocal
REM ---------------------------------------------------------------------------
REM V14 成品演示 — 一键启动 (Windows Terminal 双 tab 版本)
REM 单 wt 窗口内开两个 tab：
REM   1) agent_report FastAPI 后端 (http://127.0.0.1:8002)
REM   2) Next.js 前端              (http://localhost:3000)
REM 前端通过 next.config.ts 的 rewrites 把 /api/report/* 代理到 :8002
REM ---------------------------------------------------------------------------

set "PROJECT_ROOT=%~dp0.."

echo.
echo ====================================================================
echo  V14 Credit Report Agent — Dev Stack
echo  Project: %PROJECT_ROOT%
echo ====================================================================
echo.

REM ---- DEEPSEEK_API_KEY 检查（仅提示，不阻塞）----
if "%DEEPSEEK_API_KEY%"=="" (
  echo [WARN] DEEPSEEK_API_KEY 未设置 — 真 pipeline 模式不可用，只能用 MOCK。
  echo        设置方法：setx DEEPSEEK_API_KEY "sk-xxxxx" 然后重开 shell
  echo.
) else (
  echo [OK]   DEEPSEEK_API_KEY 已设置
  echo.
)

echo [1/2] 启动后端 (agent_report) — wt 新 tab...
wt -w 0 new-tab --title "agent_report :8002" -d "%PROJECT_ROOT%" -- cmd /k "py -m uvicorn agent_report.api:app --port 8002 --reload"

REM 让后端先起 2s（前端 dev server 启动期间会探查后端）
timeout /t 2 /nobreak >nul

echo [2/2] 启动前端 (Next.js) — wt 新 tab...
wt -w 0 new-tab --title "web :3000" -d "%PROJECT_ROOT%\web" -- cmd /k "npm run dev"

echo.
echo ====================================================================
echo  打开浏览器访问：http://localhost:3000/report
echo  后端健康检查  ：http://127.0.0.1:8002/api/report/health
echo.
echo  停止：在 wt 窗口里关掉对应 tab（Ctrl+Shift+W）
echo ====================================================================
echo.
endlocal
