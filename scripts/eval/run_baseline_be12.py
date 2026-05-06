"""Sprint 6 D2 · BE12 evaluation baseline runner

per xlsx v2 1.2 verbatim "evidence 可追溯率 100% + 标签准确率 ≥ 80% · Sprint 6 跑 evaluation runner 后公布真值"

Usage:
    py scripts/eval/run_baseline_be12.py --yaml evaluation/agent1_personal_insight.yaml --samples 5

Output:
    data/eval/be12_baseline_<timestamp>.json — { metric_name, score, samples_n, timestamp, notes }

Scaffold first · 真跑需 LLM cost · Sprint 6 D2 真跑后 baseline 入 xlsx 1.2
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVAL_DIR = PROJECT_ROOT / "data" / "eval"
EVAL_DIR.mkdir(parents=True, exist_ok=True)


def load_yaml_config(yaml_path: Path) -> dict[str, Any]:
    """Load evaluation yaml · 容 yaml 不可用 fallback dict."""
    try:
        import yaml
    except ImportError:
        print("[warn] PyYAML 不可用 · 用 stub config")
        return {
            "name": "agent1_personal_insight",
            "metrics": ["evidence_rate", "tag_accuracy", "completion_rate", "latency_p50"],
        }
    if not yaml_path.exists():
        print(f"[warn] yaml not found: {yaml_path} · 用 stub config")
        return {
            "name": "agent1_personal_insight",
            "metrics": ["evidence_rate", "tag_accuracy", "completion_rate", "latency_p50"],
        }
    with yaml_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run_baseline_metric(metric_name: str, samples: int) -> dict[str, Any]:
    """Run 1 metric on N samples · scaffold (实际跑需接 BE12 + judge LLM).

    Sprint 6 D2 真跑会:
    1. Load test cases from data/eval/be12_test_cases.jsonl
    2. Call /api/channel/personal_insight per case
    3. Score by metric (evidence_rate / tag_accuracy / etc) using judge LLM
    4. Aggregate · return { score, samples_n, notes }
    """
    print(f"[eval] running metric={metric_name} samples={samples} (scaffold mode)")
    t0 = time.time()

    # Scaffold: return placeholder targets per xlsx v2 1.2 conservative wording
    placeholder_targets = {
        "evidence_rate": 1.0,  # Evidence-First 设计保证 100%
        "tag_accuracy": 0.80,  # xlsx v2 conservative target ≥ 80%
        "completion_rate": 0.85,
        "latency_p50": 4.5,  # seconds
        "latency_p95": 11.0,  # seconds
        "hallucination_rate": 0.02,  # QC blocker 设计低
        "tool_success_rate": 0.97,
    }
    score = placeholder_targets.get(metric_name, 0.0)
    elapsed = time.time() - t0

    return {
        "metric_name": metric_name,
        "score": score,
        "samples_n": samples,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "elapsed_s": round(elapsed, 3),
        "notes": (
            "scaffold mode · Sprint 6 D2 真跑后填真值 · 当前为 xlsx v2 conservative target"
            if score == placeholder_targets.get(metric_name, 0.0) else
            "real evaluation result"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--yaml",
        default="evaluation/agent1_personal_insight.yaml",
        help="Eval config yaml path (relative to project root)",
    )
    parser.add_argument("--samples", type=int, default=5)
    args = parser.parse_args()

    yaml_path = PROJECT_ROOT / args.yaml
    config = load_yaml_config(yaml_path)

    metric_names: list[str] = list(config.get("metrics") or [
        "evidence_rate", "tag_accuracy", "completion_rate", "latency_p50",
    ])

    results = []
    for m in metric_names:
        results.append(run_baseline_metric(m, args.samples))

    output = {
        "config_name": config.get("name", "be12_baseline"),
        "yaml_source": str(args.yaml),
        "samples_per_metric": args.samples,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "metrics": results,
    }

    out_path = EVAL_DIR / f"be12_baseline_{int(time.time())}.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print("=== BE12 Baseline (scaffold) ===")
    for m in results:
        print(f"  {m['metric_name']:24s} = {m['score']}")
    print(f"output: {out_path.relative_to(PROJECT_ROOT)}")
    print()
    print("xlsx v2 1.2 SLA targets:")
    print("  evidence_rate >= 100%")
    print("  tag_accuracy >= 80% (Sprint 6 D2 真跑后填真值)")
    print("  hallucination_rate <= 5%")


if __name__ == "__main__":
    main()
