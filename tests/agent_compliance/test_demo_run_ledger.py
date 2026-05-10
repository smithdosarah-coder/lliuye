# -*- coding: utf-8 -*-
"""Phase B.2 step 10 · /api/compliance/demo/run + ledger 上链 integration test.

验:
  - demo_loader.load_scenario('online_loan') 真读 manifest + sample 政策 + compliance-kb docx
  - _run_scan_engine_stream(force_mock=True, endpoint='/api/compliance/demo/run')
    → 真后端 pipeline 跑通 (mode=mock_forced 因 force_mock=True · 不调 Tavily/LLM)
    → done envelope 含 ledger.decision_id + persisted=True
    → ledger.query_agent('compliance') 能查到刚写入的 decision
  - extras (scenario_id / input_source / business_doc_sources) 顶层暴露
  - 监管原文 hash (red line #8) · ViolationReason.clause_text_hash 字段在 schema 内 (force_mock 因
    无 LLM 跑不出 violation · 这里只验 schema 路径不破)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_compliance.api import _run_scan_engine_stream  # noqa: E402
from agent_compliance.demo_loader import (  # noqa: E402
    DemoBatchError,
    list_scenarios,
    load_scenario,
)


def _parse_sse_events(events: list[str]) -> list[dict]:
    """SSE encoded events → list[dict] payload."""
    out: list[dict] = []
    for raw in events:
        for line in raw.splitlines():
            if line.startswith("data: "):
                try:
                    out.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    continue
    return out


class TestDemoLoader:
    def test_list_scenarios_returns_three(self):
        scenarios = list_scenarios()
        ids = {s["scenario_id"] for s in scenarios}
        assert ids == {"online_loan", "aml", "data_protect"}

    def test_load_online_loan_real_text(self):
        batch = load_scenario("online_loan")
        assert batch.scenario_id == "online_loan"
        assert "互联网贷款" in batch.policy_doc
        assert len(batch.business_docs) >= 3
        assert all(len(text) > 100 for text in batch.business_docs)
        assert isinstance(batch.policy_meta, dict)
        assert batch.policy_meta.get("doc_no")
        assert len(batch.business_doc_sources) == len(batch.business_docs)

    def test_unknown_scenario_raises_typed(self):
        with pytest.raises(DemoBatchError) as exc_info:
            load_scenario("nope")
        assert exc_info.value.code == "DEMO_SCENARIO_INVALID"


class TestDemoRunEnginePipeline:
    """Phase B.2 step 10 · /demo/run 走真 engine + ledger 上链."""

    def test_demo_run_emits_ledger_persist_stage(self):
        batch = load_scenario("online_loan")
        events = list(_run_scan_engine_stream(
            policy_doc=batch.policy_doc,
            business_docs=batch.business_docs,
            policy_meta=batch.policy_meta,
            force_mock=True,  # avoid LLM/Tavily in CI
            extras={"scenario_id": "online_loan", "input_source": "sample_batch"},
            endpoint="/api/compliance/demo/run",
        ))
        parsed = _parse_sse_events(events)
        ledger_stages = [
            e for e in parsed
            if e.get("stage") == "ledger_persist" or
               (e.get("event") == "stage" and e.get("stage") == "ledger_persist")
        ]
        assert ledger_stages, "missing ledger_persist stage event"
        assert ledger_stages[0].get("status") in {"done", "warn"}

    def test_done_envelope_extras_and_ledger(self):
        batch = load_scenario("online_loan")
        events = list(_run_scan_engine_stream(
            policy_doc=batch.policy_doc,
            business_docs=batch.business_docs,
            policy_meta=batch.policy_meta,
            force_mock=True,
            extras={
                "scenario_id": "online_loan",
                "input_source": "sample_batch",
                "business_doc_sources": batch.business_doc_sources,
            },
            endpoint="/api/compliance/demo/run",
        ))
        parsed = _parse_sse_events(events)
        done = [e for e in parsed if e.get("event") == "done"]
        assert done, "missing done envelope"
        env = done[-1]

        # extras 顶层
        assert env.get("scenario_id") == "online_loan"
        assert env.get("input_source") == "sample_batch"
        assert env.get("business_doc_sources") == batch.business_doc_sources

        # ledger 元信息顶层
        ledger = env.get("ledger")
        assert isinstance(ledger, dict)
        assert ledger.get("persisted") is True
        decision_id = ledger.get("decision_id")
        assert isinstance(decision_id, str) and len(decision_id) > 16

    def test_ledger_recovers_decision(self):
        from shared.decision_ledger import get_decision

        batch = load_scenario("aml")
        events = list(_run_scan_engine_stream(
            policy_doc=batch.policy_doc,
            business_docs=batch.business_docs,
            policy_meta=batch.policy_meta,
            force_mock=True,
            extras={"scenario_id": "aml", "input_source": "sample_batch"},
            endpoint="/api/compliance/demo/run",
        ))
        parsed = _parse_sse_events(events)
        env = [e for e in parsed if e.get("event") == "done"][-1]
        decision_id = env["ledger"]["decision_id"]

        entry = get_decision(decision_id)
        assert entry is not None
        assert entry.get("agent_id") == "compliance"
        assert entry.get("endpoint") == "/api/compliance/demo/run"
        # 银保监 archive 默认 (CLAUDE.md §3.7.5)
        assert entry.get("retention_class") == "standard"
        assert entry.get("jurisdiction") == "HQ"
        # subject_id 内部 hash 16-hex · 不存 plain 文号 (per §3.7.5 PII-safe)
        subject_id = entry.get("subject_id") or ""
        assert subject_id and len(subject_id) == 16
        assert all(c in "0123456789abcdef" for c in subject_id)
        assert "人行" not in subject_id
        # subject_name 仍是政策标题 (用户可读 · 非 PII)
        assert "反洗钱" in (entry.get("subject_name") or "")
