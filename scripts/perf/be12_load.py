"""Sprint 5+ D4 · BE12 personal_insight 压测 scaffold

per xlsx v2 4.1 verbatim "BE12 latency_ms 端到端 P50 ≤ 5s · P95 ≤ 12s · Sprint 5+ D4 压测后基于真值公布 SLA"

Usage:
    py scripts/perf/be12_load.py --concurrency 5 --requests 50 --base-url http://localhost:8000

Output:
    data/perf/be12_baseline_<timestamp>.json — { p50, p95, p99, avg, min, max, error_rate, samples }

不真跑 production · 仅本地 / staging · 客户走访前跑出真值后填 xlsx 4.1
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import urllib.request
import urllib.error

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PERF_DIR = PROJECT_ROOT / "data" / "perf"
PERF_DIR.mkdir(parents=True, exist_ok=True)


SAMPLE_PAYLOAD = {
    "context": {
        "user_role": "rm",
        "rm_user_id": "wangzhe",
        "client_intent": "供应链金融 + 流贷",
    },
    "candidate": {
        "id": "perf-load-c-001",
        "name": "苏州精弘机械",
        "industry": "精密机械",
        "geo": "江苏苏州",
        "scale": "营收 1.1 亿",
        "signals": ["招投标", "工商", "纳税"],
        "products": ["设备融资租赁", "供应链金融"],
        "similarity": 0.92,
    },
}


def _fire_one(base_url: str, payload: dict[str, Any]) -> tuple[float, int, str | None]:
    """Fire 1 request, return (latency_seconds, http_status, error_msg).

    error_msg None on success.
    """
    url = f"{base_url}/api/channel/personal_insight"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-User-Id": "perf-test-bot",
        },
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            _ = resp.read()
            elapsed = time.time() - t0
            return (elapsed, resp.status, None)
    except urllib.error.HTTPError as e:
        elapsed = time.time() - t0
        return (elapsed, e.code, f"http_{e.code}")
    except (urllib.error.URLError, TimeoutError) as e:
        elapsed = time.time() - t0
        return (elapsed, 0, f"network_{type(e).__name__}")


def run_load(base_url: str, concurrency: int, requests: int) -> dict[str, Any]:
    """Run N requests with K concurrency · return aggregated stats."""
    print(f"[perf] base_url={base_url} concurrency={concurrency} requests={requests}")
    latencies: list[float] = []
    statuses: list[int] = []
    errors: list[str] = []

    t_start = time.time()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(_fire_one, base_url, SAMPLE_PAYLOAD) for _ in range(requests)]
        for i, fut in enumerate(as_completed(futures)):
            elapsed, status, err = fut.result()
            latencies.append(elapsed)
            statuses.append(status)
            if err:
                errors.append(err)
            if (i + 1) % 10 == 0:
                print(f"[perf] {i + 1}/{requests} done · last latency {elapsed:.2f}s status {status}")

    t_total = time.time() - t_start

    success_count = sum(1 for s in statuses if 200 <= s < 300)
    error_rate = (requests - success_count) / max(requests, 1)
    sorted_lat = sorted(latencies)

    def pct(p: float) -> float:
        if not sorted_lat:
            return 0.0
        idx = int(len(sorted_lat) * p / 100)
        idx = min(idx, len(sorted_lat) - 1)
        return sorted_lat[idx]

    result = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "base_url": base_url,
        "concurrency": concurrency,
        "requests": requests,
        "duration_total_s": round(t_total, 2),
        "samples": len(latencies),
        "success": success_count,
        "errors": len(errors),
        "error_rate": round(error_rate, 4),
        "latency": {
            "min": round(min(latencies), 3) if latencies else 0,
            "max": round(max(latencies), 3) if latencies else 0,
            "avg": round(statistics.mean(latencies), 3) if latencies else 0,
            "p50": round(pct(50), 3),
            "p90": round(pct(90), 3),
            "p95": round(pct(95), 3),
            "p99": round(pct(99), 3),
        },
        "error_samples": errors[:10],
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--requests", type=int, default=50)
    args = parser.parse_args()

    result = run_load(args.base_url, args.concurrency, args.requests)
    out_path = PERF_DIR / f"be12_baseline_{int(time.time())}.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print("=== BE12 Load Test Result ===")
    print(json.dumps(result["latency"], indent=2))
    print(f"error_rate: {result['error_rate']:.2%}")
    print(f"output: {out_path.relative_to(PROJECT_ROOT)}")
    print()
    print("xlsx v2 4.1 SLA target: P50 <= 5s · P95 <= 12s")
    p50 = result["latency"]["p50"]
    p95 = result["latency"]["p95"]
    p50_ok = p50 <= 5.0
    p95_ok = p95 <= 12.0
    print(f"P50 {p50}s {'PASS' if p50_ok else 'FAIL'} · P95 {p95}s {'PASS' if p95_ok else 'FAIL'}")


if __name__ == "__main__":
    main()
