#!/bin/bash
# create_lark_dashboard.sh · 创建 ALL IN mesh dashboard · per docs/working/lark-base-dashboard-schema.md
#
# 用法:
#   bash scripts/mesh/create_lark_dashboard.sh <BASE_APP_TOKEN> [--dry-run]
#
# 前置:
#   - PM 在飞书 base app 里建一个空 base · 把 app_token 给主 CLI
#   - lark-cli 已 auth login (per lark-shared skill)
#
# 一次创建:
#   - 1 张表 ALLIN_2026-05-08_Mesh_Dashboard
#   - 12 字段 (per §2 schema)
#   - 6 占位行 (common + 5 agent)

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "用法: bash $0 <BASE_APP_TOKEN> [--dry-run]"
  exit 1
fi

APP_TOKEN="$1"
DRY_RUN=""
if [[ "${2:-}" == "--dry-run" ]]; then
  DRY_RUN="echo [DRY] "
fi

TABLE_NAME="ALLIN_2026-05-08_Mesh_Dashboard"

echo "[create-dashboard] 创建 base table: $TABLE_NAME"
echo "[create-dashboard] app_token: $APP_TOKEN"
echo "[create-dashboard] dry-run: ${DRY_RUN:+yes}"
echo

# Step 1: 创建 table
$DRY_RUN lark-cli base table-create \
  --app-token "$APP_TOKEN" \
  --name "$TABLE_NAME" \
  --description "6 agent ALL IN mesh 状态看板 · per allin-final-exec-2026-05-08.md §6.2"

# 假设上一步返回 table_id 到 stdout · dry-run 时占位
if [[ -z "$DRY_RUN" ]]; then
  echo "[create-dashboard] WARN · 实际跑时 lark-cli table-create 返回 table_id · 后续步骤需该值"
  echo "[create-dashboard] 当前脚本仅 demo · 待 PM 提供 token 后主 CLI 实跑 · 收到 table_id 再调字段创建"
  echo
  echo "[create-dashboard] 待跑命令 (主 CLI 收到 table_id 后 inline · 替换 \$TABLE_ID):"
fi

cat <<'COMMANDS'
# Step 2: 加 12 字段
TABLE_ID="<from-step1>"

# 1 agent (text)
lark-cli base field-add --app-token "$APP_TOKEN" --table-id "$TABLE_ID" --name "agent" --type text
# 2 owner (person)
lark-cli base field-add --app-token "$APP_TOKEN" --table-id "$TABLE_ID" --name "owner" --type user
# 3 worktree (text)
lark-cli base field-add --app-token "$APP_TOKEN" --table-id "$TABLE_ID" --name "worktree" --type text
# 4 scope (text)
lark-cli base field-add --app-token "$APP_TOKEN" --table-id "$TABLE_ID" --name "scope" --type text
# 5 redline (text)
lark-cli base field-add --app-token "$APP_TOKEN" --table-id "$TABLE_ID" --name "redline" --type text
# 6 input_contract (text)
lark-cli base field-add --app-token "$APP_TOKEN" --table-id "$TABLE_ID" --name "input_contract" --type text
# 7 output_contract (text)
lark-cli base field-add --app-token "$APP_TOKEN" --table-id "$TABLE_ID" --name "output_contract" --type text
# 8 latest_signal (text)
lark-cli base field-add --app-token "$APP_TOKEN" --table-id "$TABLE_ID" --name "latest_signal" --type text
# 9 evidence_url (url)
lark-cli base field-add --app-token "$APP_TOKEN" --table-id "$TABLE_ID" --name "evidence_url" --type url
# 10 blocked_by (text)
lark-cli base field-add --app-token "$APP_TOKEN" --table-id "$TABLE_ID" --name "blocked_by" --type text
# 11 status (single-select doing/ready/merged/blocked)
lark-cli base field-add --app-token "$APP_TOKEN" --table-id "$TABLE_ID" --name "status" --type single-select \
  --options doing,ready,merged,blocked
# 12 updated_at (datetime)
lark-cli base field-add --app-token "$APP_TOKEN" --table-id "$TABLE_ID" --name "updated_at" --type datetime

# Step 3: 加 6 占位行 (common + 5 agent)
for ROW_FILE in scripts/mesh/dashboard-rows/*.json; do
  lark-cli base record-create \
    --app-token "$APP_TOKEN" \
    --table-id "$TABLE_ID" \
    --fields-file "$ROW_FILE"
done
COMMANDS

echo
echo "[create-dashboard] schema doc: docs/working/lark-base-dashboard-schema.md"
echo "[create-dashboard] 行 JSON: scripts/mesh/dashboard-rows/{common,report,credit,alert,riskctrl,compliance}.json"
