#!/bin/bash
# scripts/deploy_to_ecs.sh
#
# 一键部署 production · main CLI 默认调用 · 不等 user 触发 (CLAUDE.md §13)
# 前提: 本地已 git push origin main (origin = github.com/smithdosarah-coder/lliuye)
#
# Usage:
#   bash scripts/deploy_to_ecs.sh        # 完整部署 (stash + pull + build + restart)
#   bash scripts/deploy_to_ecs.sh --skip-build  # 仅 pull + restart (后端改动用)
#
# 触发条件 (main CLI 自动判断):
#   - 改动涉及 web/ → 完整流程 (含 npm build)
#   - 改动仅涉及 .py / api_server.py → --skip-build (uvicorn auto-reload 或 lliuye-backend restart 即可)
#   - 改动仅 docs/ / CLAUDE.md / scripts/ → 不需要 ECS 部署
#
# 失败时:
#   - npm build fail → service 不重启 · prod 维持旧版本不掉线 · 报错给 user 看
#   - service status 非 active → 不 healthcheck · 直接报警

set -euo pipefail

ECS_USER="admin"
ECS_HOST="139.196.30.69"
ECS_KEY="$HOME/.ssh/id_ed25519_aliyun_demo"
ECS_REPO="/home/admin/lliuye"
HEALTH_URL_LOCAL="http://127.0.0.1/login"
HEALTH_HOST="liuye.me"
SKIP_BUILD=0

if [ "${1:-}" = "--skip-build" ]; then
  SKIP_BUILD=1
fi

ssh_run() {
  ssh -i "$ECS_KEY" -o StrictHostKeyChecking=accept-new "$ECS_USER@$ECS_HOST" "$@"
}

echo "=== 1. ECS dirty tree status ==="
ssh_run "cd $ECS_REPO && git status --short" || true

echo ""
echo "=== 2. stash dirty (auto · before pull) ==="
ssh_run "cd $ECS_REPO && \
  if [ -n \"\$(git status --short)\" ]; then \
    git stash push -u -m \"auto-stash before deploy \$(date -Iseconds)\" || true; \
  fi"

echo ""
echo "=== 3. pull origin main ==="
ssh_run "cd $ECS_REPO && git pull origin main"

if [ "$SKIP_BUILD" -eq 0 ]; then
  echo ""
  echo "=== 4. stop frontend service ==="
  ssh_run "sudo systemctl stop lliuye-frontend"

  echo ""
  echo "=== 5. npm run build (slow · 3-10 min) ==="
  ssh_run "cd $ECS_REPO/web && npm run build" 2>&1 | tail -30

  echo ""
  echo "=== 6. start frontend service ==="
  ssh_run "sudo systemctl start lliuye-frontend"
else
  echo ""
  echo "=== 4-6 跳过 (--skip-build) · 仅 restart backend ==="
  ssh_run "sudo systemctl restart lliuye-backend"
fi

sleep 4

echo ""
echo "=== 7. verify 4 service ==="
ssh_run "systemctl status nginx cloudflared lliuye-frontend lliuye-backend --no-pager 2>&1 | grep -E '^(.*\.service|.*Active:)'" | head -16

echo ""
echo "=== 8. healthcheck (本地直连 · 跳过 cloudflared) ==="
ssh_run "curl -sI -H 'Host: $HEALTH_HOST' $HEALTH_URL_LOCAL | head -3"

echo ""
echo "=== ✓ deploy complete · public URL: https://liuye.me/login ==="
