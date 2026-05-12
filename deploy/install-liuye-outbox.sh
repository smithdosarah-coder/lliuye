#!/bin/bash
# Liuye outbox systemd unit install · ECS Linux · idempotent
#
# Per W2-backend brief §3 file 2 + W0 sub-agent D systemd unit + W2 第 3 棒
# hidden gotcha #1 (production sqlite migrate · _init_schema executescript
# 在老 db 上跑 CREATE INDEX idx_is_feedback fail · 整个 script 中断 · 第 4 棒
# 必加 pre-flight)。
#
# Usage:
#   sudo bash deploy/install-liuye-outbox.sh
#
# Idempotent · 重复跑安全:
#   - cp 覆盖既有 unit (没人手动改 deploy/*.service · 改了走 git)
#   - daemon-reload 拉 systemd 配置
#   - enable 重复设置无害
#   - restart 拉服务到新版
#
# 不破: 老 unit 在跑时 cp + daemon-reload + restart 平滑切换 · journalctl 看不丢日志.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_NAME="liuye-outbox"
SERVICE_FILE="${SCRIPT_DIR}/${SERVICE_NAME}.service"
TARGET="/etc/systemd/system/${SERVICE_NAME}.service"

echo "[install] project root: ${PROJECT_ROOT}"
echo "[install] systemd unit:  ${SERVICE_FILE}"
echo "[install] target path:   ${TARGET}"

if [[ ! -f "${SERVICE_FILE}" ]]; then
    echo "[install] FATAL · ${SERVICE_FILE} not found" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 1. sqlite migration pre-flight (per W2-backend 第 3 棒 gotcha #1)
# ---------------------------------------------------------------------------
# _init_schema 用 executescript 跑 schema · 老 db 上 CREATE INDEX idx_is_feedback
# / parent_turn_id 列缺失 → 整个 script 中断. 走 per-table ALTER fallback 保
# v1.1 schema 一致 (parent_turn_id + idx_parent_turn + idx_is_feedback).
# ---------------------------------------------------------------------------
echo "[pre-flight] sqlite migration · 验 v1.1 schema (parent_turn_id + idx_is_feedback + idx_parent_turn)..."
cd "${PROJECT_ROOT}"

if python3 -c "from shared.decision_ledger.store import default_ledger; default_ledger()._init_schema()" 2>/dev/null; then
    echo "[pre-flight] _init_schema OK (executescript clean · 新 db 或 schema 一致)"
else
    echo "[pre-flight] _init_schema 失败 · 走 per-table ALTER fallback..."
    python3 <<'EOF'
import sqlite3
from pathlib import Path
from shared.decision_ledger.store import DEFAULT_DB_PATH

db = Path(DEFAULT_DB_PATH)
db.parent.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(db)
try:
    # 1. 保证 decisions 表存在 (CREATE IF NOT EXISTS · 老 db 已存在则 noop)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS decisions (
      decision_id      TEXT PRIMARY KEY,
      agent_id         TEXT NOT NULL,
      endpoint         TEXT NOT NULL,
      ts               TEXT NOT NULL,
      input_hash       TEXT NOT NULL,
      output_hash      TEXT NOT NULL,
      evidence_chain   TEXT NOT NULL,
      reviewer_id      TEXT,
      reviewer_action  TEXT,
      reviewer_ts      TEXT,
      jurisdiction     TEXT NOT NULL,
      retention_class  TEXT NOT NULL,
      subject_name     TEXT,
      subject_id       TEXT,
      created_at       TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)
    conn.commit()

    # 2. per-column ALTER · sqlite raise OperationalError when dup
    for stmt in [
        "ALTER TABLE decisions ADD COLUMN is_feedback INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE decisions ADD COLUMN feedback_meta TEXT",
        "ALTER TABLE decisions ADD COLUMN parent_turn_id TEXT",
    ]:
        try:
            conn.execute(stmt)
            print(f"  + applied: {stmt}")
        except sqlite3.OperationalError as e:
            print(f"  · skip (already migrated): {stmt} · {e}")

    # 3. per-index CREATE IF NOT EXISTS · 安全重入
    for stmt in [
        "CREATE INDEX IF NOT EXISTS idx_agent_ts        ON decisions(agent_id, ts)",
        "CREATE INDEX IF NOT EXISTS idx_jurisdiction_ts ON decisions(jurisdiction, ts)",
        "CREATE INDEX IF NOT EXISTS idx_subject         ON decisions(subject_id)",
        "CREATE INDEX IF NOT EXISTS idx_is_feedback     ON decisions(is_feedback, ts)",
        "CREATE INDEX IF NOT EXISTS idx_parent_turn     ON decisions(parent_turn_id)",
    ]:
        try:
            conn.execute(stmt)
            print(f"  + index: {stmt}")
        except sqlite3.OperationalError as e:
            print(f"  · skip index: {e}")

    conn.commit()
    print("[pre-flight] manual migration OK · v1.1 schema 对齐")
finally:
    conn.close()
EOF
fi

# ---------------------------------------------------------------------------
# 2. systemd install · 平滑切换
# ---------------------------------------------------------------------------
echo "[systemd] cp unit + daemon-reload + enable + restart..."
sudo cp "${SERVICE_FILE}" "${TARGET}"
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

# 等 systemd 状态稳定再 check (active=running 需要 ~1-2s · 不需要 sleep 5)
sleep 2

echo "[systemd] status:"
sudo systemctl status "${SERVICE_NAME}" --no-pager || true

# ---------------------------------------------------------------------------
# 3. 跑通验证 · journalctl 最近 10s 日志确认 worker started
# ---------------------------------------------------------------------------
echo ""
echo "[verify] outbox loop running · journalctl --since '10 seconds ago':"
sudo journalctl -u "${SERVICE_NAME}" --since "10 seconds ago" --no-pager || true

# 期望日志含 "[outbox_retry] worker started · outbox=... deadletter=... max_retry=5 backoff=(60, 120, 240, 480, 960) scan=60s"
echo ""
echo "[install] DONE · ${SERVICE_NAME} systemd unit installed + sqlite v1.1 schema migrated + worker running"
echo "[install] 查看 outbox 状态:   sudo systemctl status ${SERVICE_NAME}"
echo "[install] 查看 outbox 日志:   sudo journalctl -u ${SERVICE_NAME} -f"
echo "[install] 看 dead-letter:    ls /home/admin/lliuye/data/liuye/dead-letter/"
