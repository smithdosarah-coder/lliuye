#!/usr/bin/env bash
# Install the orchestrator commit-msg hook by pointing core.hooksPath at this
# directory. Centralised under version control instead of editing .git/hooks/.
#
# Usage: bash scripts/orchestrator/hooks/install.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
PROJECT_ROOT="${PROJECT_ROOT//\\//}"

# Compute hooksPath relative to repo root for portability across worktrees.
HOOKS_REL="scripts/orchestrator/hooks"

cd "$PROJECT_ROOT"

echo "[install] setting core.hooksPath -> ${HOOKS_REL}"
git config core.hooksPath "$HOOKS_REL"

# Make the hook executable (no-op on Windows but needed on POSIX).
chmod +x "${PROJECT_ROOT}/${HOOKS_REL}/commit-msg" 2>/dev/null || true

# ---- self-check --------------------------------------------------------------
VALIDATOR="${PROJECT_ROOT}/scripts/orchestrator/validator.py"

if command -v py >/dev/null 2>&1; then
    PY=py
elif command -v python3 >/dev/null 2>&1; then
    PY=python3
else
    PY=python
fi

TMPDIR_SELF="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_SELF"' EXIT

GOOD_MSG="${TMPDIR_SELF}/good.txt"
BAD_MSG="${TMPDIR_SELF}/bad.txt"

cat >"$GOOD_MSG" <<'EOF'
feat(orchestrator): wire commit-msg validator

Signal: REVIEW-READY
EOF

cat >"$BAD_MSG" <<'EOF'
feat(orchestrator): forgot the trailer

just a body.
EOF

echo "[install] self-check: legal trailer should exit 0..."
if "$PY" "$VALIDATOR" "$GOOD_MSG" >/dev/null 2>&1; then
    echo "  ok"
else
    echo "  FAIL: validator rejected a legal Signal trailer"
    exit 1
fi

echo "[install] self-check: missing trailer should exit 1..."
if "$PY" "$VALIDATOR" "$BAD_MSG" >/dev/null 2>&1; then
    echo "  FAIL: validator accepted a commit with no Signal trailer"
    exit 1
else
    echo "  ok"
fi

echo "[install] done. core.hooksPath = $(git config core.hooksPath)"
echo "[install] commit-msg hook will now reject commits without a Signal trailer."
