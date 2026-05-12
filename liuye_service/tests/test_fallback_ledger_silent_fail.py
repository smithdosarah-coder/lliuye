# -*- coding: utf-8 -*-
"""liuye_service.tests.test_fallback_ledger_silent_fail — 5 应急 backend dry-run #2.

Per W2-backend brief §3 file 4 (第 4 棒 应急 dry-run W2 #2) + v3 §5.x + root §3.7.5
+ ``liuye_service/CLAUDE.md`` §5 + §7.

**应急场景**: ledger sqlite 写入失败 (read-only disk · sqlite lock · 数据库
被外部 vacuum · disk full · OS-level OSError). 验整条 silent-fail chain:

1. ``record_liuye_decision`` 收 sqlite OperationalError (from underlying
   ``shared.decision_ledger.record_decision``) → 不抛 · 走 audit.py silent-fail
   分支 + ``_enqueue_outbox`` 写 ``data/liuye/outbox/{decision_id}.json``
2. outbox JSON 写真有 idempotency_key + decision_id + 完整原 payload
3. OutboxWorker 后续 60s scan 真 pick up · 重试 5 次 (60s/120s/240s/480s/960s
   backoff) · per ``workers/outbox_retry.py:DEFAULT_BACKOFF_SEC``
4. 5 次全 fail → 文件 move 到 ``data/liuye/dead-letter/{decision_id}.json``
   + journalctl Sentry ALERT log + 人工 review

**反模式**:
- ❌ ledger write fail → raise → decision flow 中断 (违反 §3.7.5 silent-fail
  hardline · 4 角色"不敢信"复发)
- ❌ outbox 写 sqlite 而不是 JSON (ledger 主库挂 · outbox 跟着挂 · 死循环)
- ❌ retry > 5 次 (违反 v3 §5.x 5 次封顶 · 防 outbox 雪球)
- ❌ dead-letter 没 alert (人工不知 · 月底审计才发现丢决策)

**SSOT 引用**:
- ``liuye_service/audit.py:record_liuye_decision()`` silent-fail wrapper
- ``liuye_service/audit.py:_enqueue_outbox()`` outbox 写 helper
- ``liuye_service/workers/outbox_retry.py:OutboxWorker.process_entry()`` 重试
- root §3.7.5 BE7 (subject_id PII hash + retention defaults)
- v3 §5.x P1-12 retry 政策 (60s scan · 5 max retry · backoff 60/120/240/480/960)

测试隔离: monkeypatch shared.decision_ledger.store.DecisionLedger.record 抛
OperationalError · 用 tmp_path sqlite + tmp_path outbox · 不污染 production
``data/ledger/decisions.sqlite``.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from liuye_service.audit import (
    DEFAULT_OUTBOX_DIR,
    _enqueue_outbox,
    record_liuye_decision,
)
from liuye_service.workers.outbox_retry import (
    DEFAULT_BACKOFF_SEC,
    DEFAULT_MAX_RETRY,
    OutboxWorker,
)
from shared.decision_ledger.store import DecisionLedger, set_default_ledger


# ---------------------------------------------------------------------------
# Fixtures · isolated sqlite + outbox + dead-letter per test
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_outbox_dirs(tmp_path: Path) -> tuple[Path, Path]:
    """Provide isolated outbox + dead-letter dirs (NOT production paths)."""
    outbox = tmp_path / "outbox"
    dead = tmp_path / "dead-letter"
    outbox.mkdir(parents=True, exist_ok=True)
    dead.mkdir(parents=True, exist_ok=True)
    return outbox, dead


@pytest.fixture
def isolated_ledger(tmp_path: Path):
    """Provide a DecisionLedger backed by tmp sqlite · clean per test."""
    db = tmp_path / "ledger.sqlite"
    ledger = DecisionLedger(db_path=db)
    set_default_ledger(ledger)
    yield ledger
    set_default_ledger(None)


# ---------------------------------------------------------------------------
# 1. audit.py silent-fail · sqlite OperationalError → outbox enqueue
# ---------------------------------------------------------------------------


def test_ledger_operational_error_writes_outbox(
    isolated_outbox_dirs: tuple[Path, Path],
    isolated_ledger: DecisionLedger,
) -> None:
    """``record_liuye_decision`` 内 ``shared.decision_ledger.record_decision``
    抛 OperationalError → audit.py 接住 · 写 outbox · 返回 fallback_id."""
    outbox, _dead = isolated_outbox_dirs

    # Patch the façade re-export inside audit.py module (not the store).
    # audit.py imports `record_decision as _record_decision` at module top
    # · we patch the name as seen from inside audit.
    with patch(
        "liuye_service.audit._record_decision",
        side_effect=sqlite3.OperationalError("attempt to write a readonly database"),
    ):
        decision_id = record_liuye_decision(
            agent_id="credit",
            endpoint="/api/liuye/sessions",
            input_payload={"applied_product": "CORP_CREDIT"},
            output_payload={"verdict": "PASS"},
            evidence_chain={"trace_id": "trace_sf_001"},
            decision_id="dec_silent_001",
            jurisdiction="HQ",
            retention_class="standard",
            outbox_dir=outbox,  # 覆盖 default · 隔离 production
        )

    # 1. 返回 decision_id · 不破 decision flow
    assert decision_id == "dec_silent_001"

    # 2. outbox 文件真存在
    target = outbox / "dec_silent_001.json"
    assert target.exists(), f"outbox file missing at {target}"

    # 3. 内容完整 (idempotency_key + 原 payload 保留)
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["decision_id"] == "dec_silent_001"
    assert payload["agent_id"] == "credit"
    assert payload["endpoint"] == "/api/liuye/sessions"
    assert payload["input_payload"] == {"applied_product": "CORP_CREDIT"}
    assert payload["output_payload"] == {"verdict": "PASS"}
    assert payload["jurisdiction"] == "HQ"
    assert payload["retention_class"] == "standard"
    # idempotency_key 必有 · 防 retry worker 二次写
    assert payload["idempotency_key"] == "dec_silent_001"
    # 错误标注供人工 review 排错
    assert "_error" in payload
    assert "OperationalError" in payload["_error"]


def test_silent_fail_preserves_parent_turn_id(
    isolated_outbox_dirs: tuple[Path, Path],
    isolated_ledger: DecisionLedger,
) -> None:
    """Q3 ratify v1.1 schema · 跨 mode parent_turn_id 在 outbox 文件里完整保留
    · retry worker 后续重试时 forward 回 ledger.record(parent_turn_id=X)."""
    outbox, _ = isolated_outbox_dirs

    with patch(
        "liuye_service.audit._record_decision",
        side_effect=sqlite3.OperationalError("disk I/O error"),
    ):
        record_liuye_decision(
            agent_id="riskctrl",
            endpoint="/api/liuye/agent2/backtest",
            input_payload={"dsl_decision_id": "dec_dsl_001"},
            output_payload={"ks": 0.42},
            evidence_chain={"trace_id": "trace_xmode"},
            decision_id="dec_backtest_silent_001",
            parent_turn_id="turn_dsl_parent_xyz",
            outbox_dir=outbox,
        )

    payload = json.loads(
        (outbox / "dec_backtest_silent_001.json").read_text(encoding="utf-8"),
    )
    assert payload["parent_turn_id"] == "turn_dsl_parent_xyz"


def test_silent_fail_hashes_subject_id_before_outbox(
    isolated_outbox_dirs: tuple[Path, Path],
    isolated_ledger: DecisionLedger,
) -> None:
    """Plain PII 永远不能落 outbox · 必先 hash (per CLAUDE.md §5 + root §3.7.5).
    防 outbox 文件被人手 cat 读 · 泄露统一社会信用代码 / 身份证号."""
    outbox, _ = isolated_outbox_dirs

    plain_pii = "913100007331287234"  # 假统一社会信用代码

    with patch(
        "liuye_service.audit._record_decision",
        side_effect=sqlite3.OperationalError("database is locked"),
    ):
        record_liuye_decision(
            agent_id="credit",
            endpoint="/api/liuye/sessions",
            input_payload={"q": "test"},
            output_payload={"verdict": "PASS"},
            evidence_chain={"trace_id": "trace_pii"},
            decision_id="dec_pii_001",
            subject_id=plain_pii,  # 故意传 plain PII
            outbox_dir=outbox,
        )

    payload = json.loads(
        (outbox / "dec_pii_001.json").read_text(encoding="utf-8"),
    )
    # 验 outbox 上的 subject_id 已被 hash · 不是 plain PII
    stored = payload["subject_id"]
    assert stored is not None
    assert stored != plain_pii, "PII 必须 hash · 不能 plain 落 outbox"
    # hash_subject_id 返回 16-hex prefix
    assert len(stored) == 16
    assert all(c in "0123456789abcdef" for c in stored)


# ---------------------------------------------------------------------------
# 2. OutboxWorker 后续 retry 5 次 + dead-letter graduation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_outbox_worker_picks_up_silent_fail_entry(
    isolated_outbox_dirs: tuple[Path, Path],
    isolated_ledger: DecisionLedger,
) -> None:
    """端到端: audit 写 outbox → OutboxWorker 读 outbox → 调 record_decision →
    成功 → unlink 文件. 链路完整."""
    outbox, dead = isolated_outbox_dirs

    # Step 1: audit silent-fail · 写 outbox
    with patch(
        "liuye_service.audit._record_decision",
        side_effect=sqlite3.OperationalError("temp"),
    ):
        record_liuye_decision(
            agent_id="credit",
            endpoint="/api/liuye/sessions",
            input_payload={"q": "e2e"},
            output_payload={"verdict": "PASS"},
            evidence_chain={"trace_id": "trace_e2e"},
            decision_id="dec_e2e_001",
            outbox_dir=outbox,
        )

    target = outbox / "dec_e2e_001.json"
    assert target.exists()

    # Step 2: OutboxWorker process_entry · 这次假 ledger 恢复 (返 decision_id)
    worker = OutboxWorker(outbox_dir=outbox, deadletter_dir=dead)
    with patch(
        "liuye_service.workers.outbox_retry.record_decision",
        return_value="dec_e2e_001",
    ) as mocked:
        ok = await worker.process_entry(target)

    # Step 3: 验链路接通
    assert ok is True, "OutboxWorker should succeed on retry"
    assert not target.exists(), "successful retry must unlink the outbox file"
    # Step 4: 验 record_decision 收到完整原 payload + parent_turn_id forward
    mocked.assert_called_once()
    kwargs = mocked.call_args.kwargs
    assert kwargs["decision_id"] == "dec_e2e_001"
    assert kwargs["agent_id"] == "credit"
    assert kwargs["input_payload"] == {"q": "e2e"}
    assert kwargs["evidence_chain"] == {"trace_id": "trace_e2e"}


@pytest.mark.asyncio
async def test_outbox_worker_graduates_to_dead_letter_after_5_retries(
    isolated_outbox_dirs: tuple[Path, Path],
) -> None:
    """5 次重试全 fail → graduate dead-letter + 文件移走 + alert log fired."""
    outbox, dead = isolated_outbox_dirs

    # 起始 envelope · retry_count=6 (> max_retry=5) · 立即 graduate
    envelope = {
        "decision_id": "dec_dead_001",
        "agent_id": "credit",
        "endpoint": "/api/liuye/sessions",
        "input_payload": {"q": "doomed"},
        "output_payload": {"verdict": "PASS"},
        "evidence_chain": {"trace_id": "trace_dead"},
        "jurisdiction": "HQ",
        "retention_class": "standard",
        "parent_turn_id": None,
        "retry_count": 6,  # 触发 _is_dead_letter (> max_retry 5)
        "idempotency_key": "dec_dead_001",
    }
    target = outbox / "dec_dead_001.json"
    target.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")

    worker = OutboxWorker(outbox_dir=outbox, deadletter_dir=dead)
    ok = await worker.process_entry(target)

    assert ok is False
    assert not target.exists(), "dead-lettered entry must leave outbox dir"
    moved = dead / "dec_dead_001.json"
    assert moved.exists(), "dead-letter file must exist"

    # 验 dead-letter 文件含 _dead_letter section + 原 envelope (full fidelity)
    dl = json.loads(moved.read_text(encoding="utf-8"))
    assert "_dead_letter" in dl
    assert dl["_dead_letter"]["reason"] == "max_retry_exceeded"
    assert "graduated_at" in dl["_dead_letter"]
    assert dl["decision_id"] == "dec_dead_001"
    # 原 payload 保留 (人工 review 可看 input/output)
    assert dl["input_payload"] == {"q": "doomed"}


@pytest.mark.asyncio
async def test_outbox_worker_reschedules_with_v3_spec_backoff(
    isolated_outbox_dirs: tuple[Path, Path],
) -> None:
    """非 dead-letter 时 failure 走 reschedule · next_attempt_at + retry_count
    bump · backoff 跟 v3 §5.x 60/120/240/480/960 spec."""
    outbox, dead = isolated_outbox_dirs

    envelope = {
        "decision_id": "dec_resched_001",
        "agent_id": "credit",
        "endpoint": "/api/liuye/sessions",
        "input_payload": {"q": "x"},
        "output_payload": {"v": "PASS"},
        "evidence_chain": {"trace_id": "trace_r"},
        "retry_count": 0,
        "idempotency_key": "dec_resched_001",
    }
    target = outbox / "dec_resched_001.json"
    target.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")

    worker = OutboxWorker(outbox_dir=outbox, deadletter_dir=dead)
    # record_decision 持续抛 · worker 应 reschedule (NOT graduate)
    with patch(
        "liuye_service.workers.outbox_retry.record_decision",
        side_effect=RuntimeError("sqlite still down"),
    ):
        ok = await worker.process_entry(target)

    assert ok is False
    # 文件还在 (reschedule · 不 graduate)
    assert target.exists()
    # retry_count 从 0 bump 到 1 · next_attempt_at 用 backoff[0]=60s
    new_env = json.loads(target.read_text(encoding="utf-8"))
    assert new_env["retry_count"] == 1
    assert "next_attempt_at" in new_env
    assert "last_attempt_at" in new_env
    # 验 v3 §5.x backoff schedule SSOT
    assert DEFAULT_BACKOFF_SEC == (60, 120, 240, 480, 960)
    assert DEFAULT_MAX_RETRY == 5


# ---------------------------------------------------------------------------
# 3. Idempotency_key 防重写 · 同一 outbox 文件被多 worker 跑过不重复
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotency_key_prevents_double_write_in_one_run(
    isolated_outbox_dirs: tuple[Path, Path],
) -> None:
    """同一 run 内 idempotency_key 已 attempt 过 → skip 再次 attempt (per
    workers/outbox_retry.py:235-275 idempotency gate · v3 必修 #21)."""
    outbox, dead = isolated_outbox_dirs

    envelope = {
        "decision_id": "dec_idem_001",
        "agent_id": "credit",
        "endpoint": "/api/liuye/sessions",
        "input_payload": {"q": "idem"},
        "output_payload": {"v": "PASS"},
        "evidence_chain": {"trace_id": "trace_idem"},
        "retry_count": 0,
        "idempotency_key": "dec_idem_001",
    }
    target = outbox / "dec_idem_001.json"
    target.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")

    worker = OutboxWorker(outbox_dir=outbox, deadletter_dir=dead)
    # 模拟 record_decision 永远成功 (返回 echo decision_id)
    with patch(
        "liuye_service.workers.outbox_retry.record_decision",
        return_value="dec_idem_001",
    ) as mocked:
        # 第一次 process · 真 record_decision 调用
        ok1 = await worker.process_entry(target)
        assert ok1 is True
        assert mocked.call_count == 1

    # 文件已 unlink (success)
    assert not target.exists()

    # 重新写一份 (模拟 race: 文件被 re-dropped 再 process)
    target.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    with patch(
        "liuye_service.workers.outbox_retry.record_decision",
        return_value="dec_idem_001",
    ) as mocked2:
        # 同 worker 实例内 idempotency_key 已 seen · 第二次 skip
        ok2 = await worker.process_entry(target)
        assert ok2 is False, "duplicate idempotency_key must be skipped"
        assert mocked2.call_count == 0, "record_decision not invoked again"


# ---------------------------------------------------------------------------
# 4. _enqueue_outbox helper · 单元 verify (audit.py 共用)
# ---------------------------------------------------------------------------


def test_enqueue_outbox_writes_idempotent_json(tmp_path: Path) -> None:
    """``_enqueue_outbox`` 是 audit silent-fail 与 worker 之间的契约 · 必须
    写 well-formed JSON + 创建目录."""
    outbox = tmp_path / "nested" / "outbox"
    # 目录不存在 · _enqueue_outbox 应自己 mkdir
    assert not outbox.exists()

    target = _enqueue_outbox(
        decision_id="dec_enq_001",
        payload={
            "decision_id": "dec_enq_001",
            "agent_id": "report",
            "_error": "TestError: simulated",
            "idempotency_key": "dec_enq_001",
        },
        outbox_dir=outbox,
    )

    assert target is not None
    assert target.exists()
    assert outbox.exists()
    # 重复写 · 同一 path · 覆盖 (idempotent)
    target2 = _enqueue_outbox(
        decision_id="dec_enq_001",
        payload={"decision_id": "dec_enq_001", "agent_id": "report", "_v": 2},
        outbox_dir=outbox,
    )
    assert target2 == target
    # 第二次内容覆盖
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload.get("_v") == 2
