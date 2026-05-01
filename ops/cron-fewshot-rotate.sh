#!/usr/bin/env bash
# Phase B Sprint 2 决策 2 · few-shot 周轮转 cron 脚本
#
# 触发: 每周日 02:00 UTC+8 (per dispatch)
# crontab 安装示例:
#   0 2 * * 0 cd /opt/lliuye && bash ops/cron-fewshot-rotate.sh >> /var/log/lliuye/fewshot-rotate.log 2>&1
#
# 流程:
#   1. py scripts/feedback_auto_pipeline.py (扫 30 天 / 高质量 / dedup / inject)
#   2. 若 prompts.py 有 diff → git commit signal FEW-SHOT-ROTATED-WEEKLY
#   3. push origin main (主 CLI 部署 ECS pull · 手动决定 · 不强 push)
#
# 红线:
#   - 不强 push (per CLAUDE.md §13 "git push 等用户")
#   - 失败 silent (cron log 留底 · 主 CLI 周一巡查)
#   - LIUYE_FEWSHOT_POC_ENABLED 默认 off · prompts inject 后仍需显式 export 才生效
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO_ROOT"

WEEK="$(date +%Y-W%V)"
LOG_PREFIX="[fewshot-rotate $WEEK]"

echo "$LOG_PREFIX start · $(date -Iseconds)"

# 1. run pipeline
if ! py scripts/feedback_auto_pipeline.py 2>&1; then
  echo "$LOG_PREFIX pipeline FAILED · keep prompts.py unchanged" >&2
  exit 1
fi

# 2. commit if prompts.py changed
if git diff --quiet -- 'agent_*/prompts.py'; then
  echo "$LOG_PREFIX no prompts.py change · skip commit"
  exit 0
fi

git add 'agent_*/prompts.py' 'data/fewshot/*.json' 2>/dev/null || true
git commit -m "$(cat <<EOF
chore(fewshot): FEW-SHOT-ROTATED-WEEKLY · $WEEK auto rotation

Source: scripts/feedback_auto_pipeline.py (last 30 days · rating>=4 + len>=100 +
        has_diff + dedup>0.85 + PII redacted)

LIUYE_FEWSHOT_POC_ENABLED still default off · 真生效需启动脚本 export.

Signal: FEW-SHOT-ROTATED-WEEKLY
REVIEW-MODE: cron-auto
WEEK: $WEEK
EOF
)"

echo "$LOG_PREFIX committed · main CLI 自行决定何时 push origin · $(date -Iseconds)"
