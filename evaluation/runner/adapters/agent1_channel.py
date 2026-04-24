# -*- coding: utf-8 -*-
"""
evaluation.runner.adapters.agent1_channel — Agent1 全渠道获客评估 adapter

B1 首轮 scope:
  - 无 runtime dump · 无 look-alike 人工真值集
  - 所有 10 条指标 value=None, method=manual 或 heuristic, 标注 pending 原因
  - verdict → PARTIAL (base_evaluator 自动)

Phase 2 接入:
  - 消费 agent_channel.lead_finder runtime dump (候选清单 + 信号 + 证据)
  - 消费业务方提供的 look-alike 种子企业真值集 (retrieval_recall / ndcg@10)
  - Portrait match precision 走 LLM-judge 或人工抽检

Artifact 协议:
  run.artifacts[0] 为 runtime dump JSON (存在时用) · 格式预留:
    {
      "candidates": [{"entity_id": "...", "signals": [...], "evidence": [...], ...}],
      "seed_profile": {...},
      "gold_lookalike": [...],
      "gold_top10_ranking": [...],
      "tool_calls": {"total": ..., "success": ...}
    }
  run.artifacts 为空 → 全部 pending
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..base_evaluator import REPO_ROOT, BaseEvaluator
from ..registry import register_evaluator
from ..schemas import EvalRun, MetricOutcome


DEFAULT_RUNTIME = REPO_ROOT / "evaluation" / "manual" / "1_latest.json"
ORACLE_PATH = REPO_ROOT / "evaluation" / "manual" / "1_oracle.json"
STUB_PRECISION_AT_10 = 0.5   # onboarding Task C spec · oracle 未到位时 stub 值
STUB_RECALL_AT_10 = 0.5
STUB_SOURCE = "stub_awaiting_code_arch_b2"


@register_evaluator("channel")
class Agent1ChannelEvaluator(BaseEvaluator):
    agent_id = "channel"
    config_name = "agent1_channel.yaml"

    def _load_oracle_annotations(
        self,
        source: str = "code-arch-b2",
    ) -> dict[str, Any] | None:
        """B2 Task C · 加载 code-arch Batch 2 整合测试 oracle 标注.

        预期格式 (code-arch 交付契约):
          {
            "source": "code-arch-b2",
            "generated_at": "...",
            "queries": [
              {
                "query_id": "...",
                "top20_candidates": [
                  {"entity_id": "...", "rank": 1, "is_match": true},
                  ...
                ],
                "gold_lookalike": ["entity_id_1", ...]
              }
            ]
          }

        文件不存在 → None, adapter 走 stub_awaiting_code_arch_b2 分支.
        """
        if not ORACLE_PATH.exists():
            return None
        try:
            payload = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
            payload["_source_tag"] = source
            return payload
        except (json.JSONDecodeError, OSError):
            return None

    def load_artifacts(self, run: EvalRun) -> dict[str, Any]:
        if run.artifacts:
            art_path = Path(run.artifacts[0])
            if not art_path.is_absolute():
                art_path = REPO_ROOT / art_path
        elif DEFAULT_RUNTIME.exists():
            art_path = DEFAULT_RUNTIME
        else:
            return {
                "artifact_path": None,
                "error": "no runtime dump available",
                "candidates": [],
                "gold_lookalike": [],
                "gold_top10_ranking": [],
                "tool_calls": {},
                "oracle": self._load_oracle_annotations(),
            }

        try:
            payload = json.loads(art_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            return {
                "artifact_path": str(art_path),
                "error": f"load error: {e}",
                "candidates": [],
                "gold_lookalike": [],
                "gold_top10_ranking": [],
                "tool_calls": {},
                "oracle": self._load_oracle_annotations(),
            }

        # Oracle 优先: 若已到位, 用 oracle 覆盖 dump 的 stub gold (更权威)
        oracle = self._load_oracle_annotations()
        gold_lookalike = payload.get("gold_lookalike") or []
        gold_top10 = payload.get("gold_top10_ranking") or []
        if oracle and isinstance(oracle.get("queries"), list) and oracle["queries"]:
            q0 = oracle["queries"][0]
            if q0.get("gold_lookalike"):
                gold_lookalike = q0["gold_lookalike"]
            if q0.get("top20_candidates"):
                # gold_top10 = top 10 marked is_match=True
                gold_top10 = [
                    c["entity_id"] for c in q0["top20_candidates"][:10]
                    if c.get("is_match")
                ]

        return {
            "artifact_path": str(art_path),
            "candidates": payload.get("candidates") or [],
            "gold_lookalike": gold_lookalike,
            "gold_top10_ranking": gold_top10,
            "tool_calls": payload.get("tool_calls") or {},
            "oracle": oracle,
        }

    def compute_common_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        candidates: list[dict] = artifacts.get("candidates") or []
        tool_calls: dict = artifacts.get("tool_calls") or {}
        art_path = artifacts.get("artifact_path")
        has_data = bool(candidates)

        out: list[MetricOutcome] = []

        if has_data:
            # field_completeness: candidates with core keys (entity_id/name/signals/evidence)
            required = ("entity_id", "name", "signals", "evidence")
            filled = sum(
                1
                for c in candidates
                if all(c.get(k) not in (None, "", []) for k in required)
            )
            out.append(
                self.mark(
                    "field_completeness",
                    filled / len(candidates),
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{filled}/{len(candidates)} 候选带 entity_id+name+signals+evidence",
                    kind="common",
                )
            )
            # evidence_rate
            with_ev = sum(1 for c in candidates if c.get("evidence"))
            out.append(
                self.mark(
                    "evidence_rate",
                    with_ev / len(candidates),
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{with_ev}/{len(candidates)} 候选带 evidence",
                    kind="common",
                )
            )
            # hallucination_rate — entity_id 不可解析的占比 (runtime 侧应带 resolvable flag)
            unresolvable = sum(
                1 for c in candidates if c.get("resolvable") is False
            )
            out.append(
                self.mark(
                    "hallucination_rate",
                    unresolvable / len(candidates),
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{unresolvable}/{len(candidates)} entity_id resolvable=False",
                    kind="common",
                )
            )
            # task_completion_rate — 1.0 if any candidates returned
            out.append(
                self.mark(
                    "task_completion_rate",
                    1.0,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{len(candidates)} 候选产出 (≥ Top_N)",
                    kind="common",
                )
            )
        else:
            # 无数据 · 全部 pending
            for n in ("field_completeness", "evidence_rate", "hallucination_rate", "task_completion_rate"):
                out.append(self._pending(n, "common", "无 runtime dump · 待 agent_channel.lead_finder 埋点"))

        # tool_success_rate
        tc_total = tool_calls.get("total") or 0
        tc_success = tool_calls.get("success") or 0
        if tc_total > 0:
            out.append(
                self.mark(
                    "tool_success_rate",
                    tc_success / tc_total,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{tc_success}/{tc_total} 工具调用成功 (Tavily+企查查)",
                    kind="common",
                )
            )
        else:
            out.append(self._pending("tool_success_rate", "common", "无 tool_calls 元数据"))

        return out

    def compute_domain_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        candidates: list[dict] = artifacts.get("candidates") or []
        gold_lookalike: list[str] = artifacts.get("gold_lookalike") or []
        gold_top10: list[str] = artifacts.get("gold_top10_ranking") or []
        oracle: dict | None = artifacts.get("oracle")
        art_path = artifacts.get("artifact_path")

        out: list[MetricOutcome] = []

        # portrait_match_precision — B2 Task C: precision@10 (oracle 未到位走 stub)
        # 语义映射: onboarding "precision@10 = hit@10 / 10" 挂到 portrait_match_precision
        # (既有 rubric 指标, 含义对齐: Top10 候选中命中画像条件的占比 = precision@10)
        if oracle and gold_top10 and candidates:
            top10 = candidates[:10]
            hit = sum(1 for c in top10 if c.get("entity_id") in set(gold_top10))
            precision = hit / 10.0
            out.append(
                self.mark(
                    "portrait_match_precision",
                    precision,
                    method="deterministic",
                    evidence=[str(ORACLE_PATH)],
                    note=(
                        f"B2 Task C · precision@10 = {hit}/10 oracle 命中 "
                        f"(oracle source={oracle.get('_source_tag')})"
                    ),
                )
            )
        else:
            out.append(
                MetricOutcome(
                    name="portrait_match_precision",
                    value=STUB_PRECISION_AT_10,
                    target=self._lookup_target("portrait_match_precision", "domain") or "n/a",
                    passed=None,  # stub 不计入 verdict (base_evaluator 会按 passed=None 处理)
                    method="heuristic",
                    evidence=[],
                    note=(
                        f"{STUB_SOURCE} · stub precision@10={STUB_PRECISION_AT_10} · "
                        "待 code-arch Batch 2 BATCH-2-INTEGRATION-TEST-DONE 交付 "
                        f"{ORACLE_PATH.relative_to(REPO_ROOT)} oracle 标注后 re-run"
                    ),
                )
            )

        # signal_diversity — 可算 (候选中带 ≥ 2 种 signal type 的占比)
        if candidates:
            with_ge2 = 0
            for c in candidates:
                signals = c.get("signals") or []
                types = {s.get("type") for s in signals if isinstance(s, dict) and s.get("type")}
                if len(types) >= 2:
                    with_ge2 += 1
            out.append(
                self.mark(
                    "signal_diversity",
                    with_ge2 / len(candidates),
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{with_ge2}/{len(candidates)} 候选含 ≥ 2 种 signal.type",
                )
            )
        else:
            out.append(
                self._pending("signal_diversity", "domain", "无 runtime dump · 候选池为空")
            )

        # ndcg_at_10 — pending (需 gold ranking)
        out.append(
            self._pending(
                "ndcg_at_10",
                "domain",
                "pending: 需人工 gold top10 排序真值集 (Phase 2 业务方提供)",
            )
        )

        # retrieval_recall — B2 Task C: recall@10 = hit@10 / total_gold
        # (oracle 未到位走 既有 dump 自带 gold_lookalike 或 stub)
        if candidates and gold_lookalike:
            cand_ids = {c.get("entity_id") for c in candidates[:10]} if oracle else {c.get("entity_id") for c in candidates}
            # oracle 到位时严格按 Top10 recall@10; dump 模式保留原有全量召回语义
            hit = sum(1 for g in gold_lookalike if g in cand_ids)
            out.append(
                self.mark(
                    "retrieval_recall",
                    hit / len(gold_lookalike),
                    method="deterministic",
                    evidence=[str(ORACLE_PATH) if oracle else (art_path or "")],
                    note=(
                        f"{hit}/{len(gold_lookalike)} gold look-alike 被召回 · "
                        f"{'oracle@top10' if oracle else 'runtime-dump (stub gold)'}"
                    ),
                )
            )
        else:
            # oracle + dump 都没 gold → 纯 stub
            out.append(
                MetricOutcome(
                    name="retrieval_recall",
                    value=STUB_RECALL_AT_10,
                    target=self._lookup_target("retrieval_recall", "domain") or "n/a",
                    passed=None,
                    method="heuristic",
                    evidence=[],
                    note=(
                        f"{STUB_SOURCE} · stub recall@10={STUB_RECALL_AT_10} · "
                        f"待 code-arch Batch 2 oracle {ORACLE_PATH.relative_to(REPO_ROOT)} 落地"
                    ),
                )
            )

        # candidate_dedup_rate — 可算
        if candidates:
            ids = [c.get("entity_id") for c in candidates if c.get("entity_id")]
            unique = len(set(ids))
            raw = len(ids) or 1
            out.append(
                self.mark(
                    "candidate_dedup_rate",
                    unique / raw,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{unique}/{raw} 唯一 entity_id",
                )
            )
        else:
            out.append(
                self._pending("candidate_dedup_rate", "domain", "无 runtime dump · 候选池为空")
            )

        return out

    def _pending(self, name: str, kind: str, reason: str) -> MetricOutcome:
        return MetricOutcome(
            name=name,
            value=None,
            target=self._lookup_target(name, kind) or "n/a",
            passed=None,
            method="manual",
            note=reason,
        )
