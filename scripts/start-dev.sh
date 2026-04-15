#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# V14 成品演示 — 一键启动(Git Bash / WSL / macOS / Linux)
# 前台输出合并到一起,Ctrl+C 一键停。
# ---------------------------------------------------------------------------
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo
echo "===================================================================="
echo "  V14 Credit Report Agent — Dev Stack"
echo "  Project: $PROJECT_ROOT"
echo "===================================================================="
echo

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "[WARN] DEEPSEEK_API_KEY 未设置 — 真 pipeline 模式不可用,只能用 MOCK。"
  echo "       export DEEPSEEK_API_KEY=sk-xxxxx 后重跑。"
else
  echo "[OK]   DEEPSEEK_API_KEY 已设置"
fi
echo

PY_CMD="python"
command -v py >/dev/null 2>&1 && PY_CMD="py"

echo "[1/2] 启动后端 (agent_report :8002) ..."
$PY_CMD -m uvicorn agent_report.api:app --port 8002 --reload &
BACK_PID=$!

echo "[2/2] 启动前端 (web :3000) ..."
( cd web && npm run dev ) &
FRONT_PID=$!

cleanup() {
  echo
  echo "Stopping..."
  kill "$BACK_PID" "$FRONT_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM

echo
echo "===================================================================="
echo "  打开浏览器访问: http://localhost:3000/report"
echo "  后端健康检查  : http://127.0.0.1:8002/api/report/health"
echo "  Ctrl+C 停止所有进程。"
echo "===================================================================="
wait
