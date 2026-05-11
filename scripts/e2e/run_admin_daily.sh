#!/usr/bin/env bash
# B.3.4 · P0-R5 · 主活 A · admin 真号 E2E cron 探针
#
# 跑 6 agent demo/run endpoint · admin 真号 cookie · SSE done ≤ 60s · result.items ≥ 1.
# 任 1 fail = stop-the-line (exit 1).
#
# 用法:
#   ADMIN_COOKIE=eyJhbGc... bash scripts/e2e/run_admin_daily.sh
#   # 或
#   echo 'ADMIN_COOKIE=eyJhbGc...' > .env.e2e   # gitignored
#   bash scripts/e2e/run_admin_daily.sh
#
# GHA: workflow daily-visual.yml admin-e2e job 通过 secrets.ADMIN_COOKIE 注入.
#
# Env vars:
#   ADMIN_COOKIE    JWT (just value · or full "zhongan_auth=<value>")  · REQUIRED
#   E2E_BASE_URL    默认 https://liuye.me
#   E2E_TIMEOUT     单次 SSE 最长等 (秒) · 默认 60
#   ENV_E2E_PATH    .env.e2e 替代路径 · 默认 ./.env.e2e
#
# Security:
#   - ADMIN_COOKIE 永不 log · 永不 echo · 永不写文件
#   - 失败 dump 限前 50 行 + cookie 已 redact
#   - .env.e2e per .gitignore 永不入 git

set -euo pipefail

# ---------- config ----------
BASE_URL="${E2E_BASE_URL:-https://liuye.me}"
TIMEOUT="${E2E_TIMEOUT:-60}"
ENV_FILE="${ENV_E2E_PATH:-.env.e2e}"

# .env.e2e 兜底 (per PM 路径 3)
if [ -z "${ADMIN_COOKIE:-}" ] && [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
fi

if [ -z "${ADMIN_COOKIE:-}" ]; then
  cat >&2 <<'BLOCKED'
[BLOCKED] ADMIN_COOKIE 缺 · 3 路径任 1 满足:
  1. export ADMIN_COOKIE=<jwt-value>
  2. echo 'ADMIN_COOKIE=<jwt-value>' > .env.e2e (本地 · gitignored)
  3. GHA secrets.ADMIN_COOKIE (CI · workflow 自动注)

如需取 cookie: 浏览器登录 https://liuye.me admin → DevTools Application →
  Cookies → 复制 zhongan_auth 值 (可 paste 完整 'zhongan_auth=<val>' 或仅 val)
BLOCKED
  exit 2  # 区别于 e2e fail (exit 1) · 配置缺失走 BLOCKED
fi

# 兼容用户 paste 完整 'name=value' 或仅 'value'
COOKIE_VALUE="${ADMIN_COOKIE#zhongan_auth=}"

# 依赖检查 (jq + curl)
for bin in curl jq; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "[FATAL] missing binary: $bin · apt install $bin" >&2
    exit 3
  fi
done

# ---------- 6 agent 矩阵 ----------
# 3 parallel array (Bash 不支持嵌套 array · 用 index 关联)
AGENTS=(channel credit alert compliance report riskctrl)
ENDPOINTS=(
  "/api/channel/demo/run"
  "/api/credit/demo/run"
  "/api/alert/demo/run"
  "/api/compliance/demo/run"
  "/api/report/demo/run"
  "/api/riskctrl/demo/run"
)
BODIES=(
  '{"scenario_id":"medium","rm_region":"华东"}'
  '{"sample_id":"corp_dingsheng_trade"}'
  '{"scenario_key":"baseline_100"}'
  '{"scenario_id":"online_loan","force_mock":false}'
  '{"sample_id":"DP001_龙峰精工"}'
  '{"seed_id":"credit_v15"}'
)

# ---------- helper ----------

# 从 SSE 流提 done event 的 data JSON
# stdin: SSE 全文 / stdout: done event data JSON (单行 · 或空)
extract_done_event() {
  awk '
    /^event: done$/ { found=1; next }
    found && /^data: / { sub(/^data: /, ""); print; found=0 }
  '
}

# done event JSON shape 因 agent 各异 · 通用 "selectable item" 探测
# 用 jq 找任意可枚举字段 length · 至少 1 个 ≥ 1 即视作 result 非空
# Agent-specific 字段 (per survey):
#   channel  → .candidates[]  (≥ 8 见 spec)
#   credit   → .scoring.sub_scores · .decision_graph.nodes
#   alert    → .clients · .traffic_light
#   compliance → .violations · .conflicts
#   report   → .pipeline · .sections
#   riskctrl → .ks · .dsl_rules
count_selectable() {
  local payload="$1"
  echo "$payload" | jq -c '
    [
      .candidates,
      .clients,
      .traffic_light,
      .violations,
      .conflicts,
      .sections,
      .pipeline,
      .pipeline_stages,
      .dsl_rules,
      .rules,
      .scoring.sub_scores,
      .decision_graph.nodes,
      .nodes,
      .items
    ]
    | map(select(. != null) | (if type == "array" then length else (keys | length) end))
    | if length == 0 then 0 else max end
  ' 2>/dev/null || echo "0"
}

# 单 agent 探: curl POST · stream · time it · validate done + items
# return 0 = PASS · 1 = FAIL
test_agent() {
  local agent="$1" endpoint="$2" body="$3"
  local url="${BASE_URL}${endpoint}"
  local start=$(date +%s)
  local resp_file
  resp_file=$(mktemp)
  trap 'rm -f "$resp_file"' RETURN

  # curl SSE · --max-time 兜底 · --no-buffer 即时刷
  local curl_exit=0
  curl --silent --show-error --no-buffer \
       --max-time "$TIMEOUT" \
       --connect-timeout 10 \
       -X POST "$url" \
       -H "Cookie: zhongan_auth=${COOKIE_VALUE}" \
       -H "Content-Type: application/json" \
       -H "Accept: text/event-stream" \
       -d "$body" \
       -o "$resp_file" 2>"${resp_file}.stderr" || curl_exit=$?

  local elapsed=$(($(date +%s) - start))

  if [ $curl_exit -ne 0 ]; then
    echo "[FAIL] ${agent} · curl exit=${curl_exit} · elapsed=${elapsed}s · base=${BASE_URL}"
    if [ -s "${resp_file}.stderr" ]; then
      echo "  stderr (前 5 行 · cookie 已 redact):"
      sed 's/zhongan_auth=[^[:space:]]*/zhongan_auth=<REDACTED>/g' "${resp_file}.stderr" | head -5 | sed 's/^/    /'
    fi
    rm -f "${resp_file}.stderr"
    return 1
  fi
  rm -f "${resp_file}.stderr"

  # 探 done event
  local done_payload
  done_payload=$(extract_done_event < "$resp_file" || true)
  if [ -z "$done_payload" ]; then
    echo "[FAIL] ${agent} · no done event in ${elapsed}s · path=${endpoint}"
    echo "  前 30 行 SSE 输出 (redacted):"
    sed 's/zhongan_auth=[^[:space:]]*/zhongan_auth=<REDACTED>/g' "$resp_file" | head -30 | sed 's/^/    /'
    return 1
  fi

  # 探 result.items
  local item_count
  item_count=$(count_selectable "$done_payload")
  if [ -z "$item_count" ] || [ "$item_count" = "0" ]; then
    echo "[FAIL] ${agent} · done event has 0 selectable items · elapsed=${elapsed}s"
    echo "  done payload (前 300 字符):"
    echo "$done_payload" | head -c 300 | sed 's/^/    /'
    echo ""
    return 1
  fi

  echo "[OK] ${agent} · done in ${elapsed}s · items=${item_count} · path=${endpoint}"
  return 0
}

# ---------- main loop ----------

echo "[START] admin 真号 E2E · 6 agent · base=${BASE_URL} · timeout=${TIMEOUT}s · cookie=<REDACTED>"
echo "[START] timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo ""

failures=0
results=()
for i in "${!AGENTS[@]}"; do
  agent="${AGENTS[$i]}"
  endpoint="${ENDPOINTS[$i]}"
  body="${BODIES[$i]}"
  if ! test_agent "$agent" "$endpoint" "$body"; then
    failures=$((failures + 1))
    results+=("${agent}:FAIL")
  else
    results+=("${agent}:PASS")
  fi
done

echo ""
echo "[SUMMARY] $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
for r in "${results[@]}"; do
  echo "  ${r}"
done

if [ "$failures" -gt 0 ]; then
  echo ""
  echo "[STOP-THE-LINE] ${failures}/6 agent admin E2E FAIL"
  echo "[STOP-THE-LINE] 触发 GHA Issue (label daily-visual,regression)"
  exit 1
fi

echo ""
echo "[GREEN] 6/6 agent admin E2E PASS"
exit 0
