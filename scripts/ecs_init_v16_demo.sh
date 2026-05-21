#!/bin/bash
# scripts/ecs_init_v16_demo.sh
#
# B.3.4 Bug B fix · 一次性 init · 保证 v16 demo 真后端跑通 prereq
#
# Prod 真因 (curl https://liuye.me/api/report/demo/run · 2026-05-11):
#   HTTP 503 · DEMO_CLASSIFIER_MISSING · outputs/v16_llm_classified.json 缺失
#
# 本脚本 idempotent:
#   - 若 outputs/v16_llm_classified.json 已存在 → skip · 0 退出
#   - 若缺失 → 真跑 v16_classifier.py (调 DeepSeek · ≤ 5 min)
#
# 前置:
#   - .env 含 DEEPSEEK_API_KEY (run_v16_classifier.py 已校验)
#   - outputs/v16_labeled_elements.json (192 element 采样 · 由 v16_step1_extract.py 产)
#   - samples/*.docx (3 份源模板 · 已 commit)
#
# Usage (deploy_to_ecs.sh hook · main CLI):
#   bash scripts/ecs_init_v16_demo.sh         # check + run if 缺
#   bash scripts/ecs_init_v16_demo.sh --force # 强制重跑 (覆盖现有 output)
#
# 失败 → exit 1 · /api/report/demo/run 仍会返 typed 503 banner (前端有 UX)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Python 解析器统一定义 · prefer .venv/bin/python (3.11+) > py launcher > system python3
# 2026-05-21 治本: 原 `command -v py || python3` fallback 在 Linux 上 py 不存在 →
# fallback 到系统 python3 (< 3.7 老版本) → v16_step1_extract.py 行 19
# `from __future__ import annotations` SyntaxError. .venv/bin/python 是 3.11 是正解.
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  PY="$PROJECT_ROOT/.venv/bin/python"
elif command -v py >/dev/null 2>&1; then
  PY=py
else
  PY=python3
fi
echo "[ecs_init] PY=$PY ($($PY --version 2>&1))"

CLASSIFIED_JSON="$PROJECT_ROOT/outputs/v16_llm_classified.json"
LABELED_JSON="$PROJECT_ROOT/outputs/v16_labeled_elements.json"
FORCE=0

if [ "${1:-}" = "--force" ]; then
  FORCE=1
fi

echo "=== ecs_init_v16_demo · check prereq ==="
echo "PROJECT_ROOT: $PROJECT_ROOT"
echo "CLASSIFIED:   $CLASSIFIED_JSON"

if [ "$FORCE" -eq 0 ] && [ -f "$CLASSIFIED_JSON" ]; then
  bytes=$(wc -c <"$CLASSIFIED_JSON")
  echo "[skip] classified.json 已存在 ($bytes bytes) · 跳过 (传 --force 强制重跑)"
  exit 0
fi

if [ ! -f "$LABELED_JSON" ]; then
  echo "[step 1/2] labeled_elements.json 缺失 · 跑 v16_step1_extract.py 生成"
  "$PY" v16_step1_extract.py
  if [ ! -f "$LABELED_JSON" ]; then
    echo "[FATAL] v16_step1_extract.py 跑完 labeled_elements.json 仍缺失 · 检查 samples/*.docx"
    exit 1
  fi
else
  echo "[step 1/2] labeled_elements.json 已存在 · 跳过"
fi

echo "[step 2/2] 跑 scripts/run_v16_classifier.py (调 DeepSeek · 预计 ≤ 5 min)"
"$PY" scripts/run_v16_classifier.py

if [ ! -f "$CLASSIFIED_JSON" ]; then
  echo "[FATAL] classifier 跑完但 classified.json 仍缺失 · 检查 DEEPSEEK_API_KEY + 网络"
  exit 1
fi

bytes=$(wc -c <"$CLASSIFIED_JSON")
echo "=== ✓ v16 demo prereq ready · classified.json $bytes bytes ==="
