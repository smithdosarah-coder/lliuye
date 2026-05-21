#!/bin/bash
# CSS universal override v1/v2 命名 cover 检测 (B.3.4 follow-up · 2026-05-21)
#
# 防 idle-tight.css universal override 漏 v1/v2 命名 · 今天 report layout bug 真因.
# 历史: report/channel 用 v1 (rpt-body/rpt-main/rpt-side/rpt-aux),
#       credit/alert/compliance 用 v2 (rpt-grid/rpt-col--mid/rpt-col--left/rpt-col--right).
# universal override 必须 cover 两套 alias, 否则 workspace 不生效.
#
# 用法:
#   bash scripts/lint/css_universal_override_check.sh
#
# 集成:
#   - pre-commit hook (建议)
#   - CI on PR change to idle-tight.css
#
# 见: docs/contracts/css-naming-ssot.md

# 不用 set -e · grep 0 匹配 exit 1 与 set -e 不兼容 (即使 || true 也踩 pipefail)
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

IDLE_TIGHT="web/src/app/archive/_shared/idle-tight.css"

if [ ! -f "$IDLE_TIGHT" ]; then
  echo "[FATAL] $IDLE_TIGHT not found"
  exit 1
fi

# v2 ↔ v1 命名 alias 表 (跟 report-workspace.css :202-239 注释一致)
# bash 3 兼容 macOS · 不用 associative array · 用 parallel arrays
V2_NAMES=("rpt-grid" "rpt-col--mid" "rpt-col--left" "rpt-col--right")
V1_NAMES=("rpt-body" "rpt-main" "rpt-side" "rpt-aux")

fail=0
echo "=== CSS universal override v1/v2 coverage check ==="
echo "target: $IDLE_TIGHT"
echo ""

for i in "${!V2_NAMES[@]}"; do
  v2="${V2_NAMES[$i]}"
  v1="${V1_NAMES[$i]}"

  # idle-tight.css 里的引用次数
  v2_in_idle=$(grep "\.${v2}\b" "$IDLE_TIGHT" 2>/dev/null | wc -l | tr -d ' ')
  v1_in_idle=$(grep "\.${v1}\b" "$IDLE_TIGHT" 2>/dev/null | wc -l | tr -d ' ')

  # workspace tsx 里的实际使用
  v2_workspaces=$(grep -l "className=\"${v2}" web/src/app/archive/*/_components/*Workspace.tsx 2>/dev/null | wc -l | tr -d ' ')
  v1_workspaces=$(grep -l "className=\"${v1}" web/src/app/archive/*/_components/*Workspace.tsx 2>/dev/null | wc -l | tr -d ' ')

  printf "[%-15s ↔ %-10s] idle-tight: v2=%s v1=%s  workspaces: v2=%s v1=%s\n" \
    ".$v2" ".$v1" "$v2_in_idle" "$v1_in_idle" "$v2_workspaces" "$v1_workspaces"

  # 漏覆盖检测 1: workspace 用了 v1 但 idle-tight 只 cover v2
  if [ "$v1_workspaces" -gt 0 ] && [ "$v1_in_idle" -eq 0 ] && [ "$v2_in_idle" -gt 0 ]; then
    echo "  [✗ FAIL] $v1_workspaces workspace 用 v1 .$v1 但 idle-tight 漏 cover (只有 v2 .$v2)"
    echo "          fix: idle-tight.css 任何 .v-archive--canon .$v2 selector 加 .$v1 alias"
    fail=1
  fi

  # 漏覆盖检测 2: workspace 用了 v2 但 idle-tight 只 cover v1
  if [ "$v2_workspaces" -gt 0 ] && [ "$v2_in_idle" -eq 0 ] && [ "$v1_in_idle" -gt 0 ]; then
    echo "  [✗ FAIL] $v2_workspaces workspace 用 v2 .$v2 但 idle-tight 漏 cover (只有 v1 .$v1)"
    echo "          fix: idle-tight.css 任何 .v-archive--canon .$v1 selector 加 .$v2 alias"
    fail=1
  fi
done

echo ""
if [ "$fail" -eq 0 ]; then
  echo "[✓ PASS] idle-tight.css universal override v1/v2 命名 cover 完整"
  exit 0
else
  echo "[✗ FAIL] idle-tight.css universal override 漏 cover 命名"
  echo "        见 docs/contracts/css-naming-ssot.md · 改 idle-tight.css 必须同时引用 v1+v2 alias"
  exit 1
fi
