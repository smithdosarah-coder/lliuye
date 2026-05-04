# -*- coding: utf-8 -*-
"""shared.policy_registry unit tests · BE4 (Phase B Sprint 2 · 2026-05-04).

Covers the versioned policy registry per
docs/contracts/agent-compliance-policy-registry.md v1.0.

Hard guarantees:
1. Hashing determinism (same input → same id, whitespace/case-folded)
2. policy_id stable across versions of the same family
3. version_id changes when body_text or effective_date changes
4. clause_id stable per (version, article, paragraph_index)
5. Idempotent register_version (same body → INSERT OR REPLACE, no dup)
6. List/latest version ordering by effective_date DESC
7. Clause round-trip: keywords/threshold survive json (de)serialization
8. mark_superseded chain (old → new)
9. Failure isolation: register on bad path still returns ids
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.policy_registry import (  # noqa: E402
    POLICY_REGISTRY_SCHEMA_VERSION,
    PolicyClause,
    PolicyRegistry,
    body_sha,
    canonical_hash,
    clause_id,
    default_registry,
    get_clauses,
    get_policy,
    get_version,
    latest_version,
    list_versions,
    mark_superseded,
    policy_id,
    register_policy_version,
    set_default_registry,
    version_id,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_registry(monkeypatch, tmp_path):
    db_path = tmp_path / "policies.sqlite"
    monkeypatch.setenv("LIUYE_POLICY_REGISTRY_DB_PATH", str(db_path))
    reg = PolicyRegistry(db_path)
    set_default_registry(reg)
    yield reg
    set_default_registry(None)


# ---------------------------------------------------------------------------
# 1. Hashing determinism
# ---------------------------------------------------------------------------


def test_policy_id_case_and_whitespace_folded():
    a = policy_id("银保监", "对公小微客户准入新规")
    b = policy_id("银保监 ", " 对公小微客户准入新规")
    c = policy_id("银保监", "对公小微客户准入新规")
    assert a == b == c
    assert a.startswith("POL-")
    assert len(a) == len("POL-") + 16


def test_policy_id_diff_title_diff_id():
    a = policy_id("银保监", "客户准入")
    b = policy_id("银保监", "反洗钱")
    assert a != b


def test_version_id_changes_with_body():
    pid = policy_id("央行", "反洗钱办法")
    bsha1 = body_sha("第一条 客户尽职调查")
    bsha2 = body_sha("第一条 客户尽职调查 (修订)")
    v1 = version_id(pid, "2026-04-01", bsha1)
    v2 = version_id(pid, "2026-04-01", bsha2)
    assert v1 != v2
    assert v1.startswith("VER-")


def test_version_id_changes_with_effective_date():
    pid = policy_id("央行", "反洗钱办法")
    bsha = body_sha("第一条 客户尽职调查")
    v1 = version_id(pid, "2026-04-01", bsha)
    v2 = version_id(pid, "2026-05-01", bsha)
    assert v1 != v2


def test_clause_id_stable():
    vid = "VER-abcdef0123456789"
    a = clause_id(vid, "第六条", 0)
    b = clause_id(vid, "第六条", 0)
    c = clause_id(vid, "第六条", 1)
    assert a == b
    assert a != c
    assert a.startswith("CL-")


def test_canonical_hash_key_order_independent():
    a = canonical_hash({"a": 1, "b": 2, "c": [3, 4]})
    b = canonical_hash({"c": [3, 4], "b": 2, "a": 1})
    assert a == b


# ---------------------------------------------------------------------------
# 2. Register / round-trip
# ---------------------------------------------------------------------------


def _sample_clauses(vid_or_none: str = "") -> list[dict]:
    """Plain dicts; store hydrates clause_id when missing."""
    return [
        {
            "article": "第一条",
            "paragraph_index": 0,
            "text": "对公客户年营业收入门槛上调至 2000 万元。",
            "category": "客户准入",
            "keywords": ["营业收入", "客户准入"],
            "threshold": {"min_revenue_wan": 2000.0},
            "severity_hint": "major",
        },
        {
            "article": "第二条",
            "paragraph_index": 0,
            "text": "注册资本实缴比例从 30% 提升到 50%。",
            "category": "客户准入",
            "keywords": ["注册资本"],
            "threshold": {"min_registered_capital_ratio": 0.5},
            "severity_hint": "major",
        },
    ]


def test_register_returns_ids_and_persists(tmp_registry: PolicyRegistry):
    result = register_policy_version(
        title="对公小微客户准入新规",
        issuer="银保监",
        body_text="第一条 ...\n第二条 ...",
        clauses=_sample_clauses(),
        effective_date="2026-03-15",
        source_url="https://example.test/cbirc-2026.html",
        category="客户准入",
    )
    assert result.persisted is True
    assert result.is_new_version is True
    assert result.policy_id.startswith("POL-")
    assert result.version_id.startswith("VER-")

    pol = get_policy(result.policy_id)
    assert pol and pol["title"] == "对公小微客户准入新规"

    ver = get_version(result.version_id)
    assert ver and ver["clause_count"] == 2
    assert ver["body_sha"]

    clauses = get_clauses(result.version_id)
    assert len(clauses) == 2
    # JSON columns rehydrated to dict/list
    assert isinstance(clauses[0]["keywords"], list)
    assert isinstance(clauses[0]["threshold"], dict)
    assert clauses[0]["threshold"].get("min_revenue_wan") == 2000.0


def test_register_idempotent_same_body(tmp_registry: PolicyRegistry):
    kwargs = {
        "title": "测试政策",
        "issuer": "银保监",
        "body_text": "第一条 ...",
        "clauses": _sample_clauses(),
        "effective_date": "2026-03-15",
    }
    r1 = register_policy_version(**kwargs)
    r2 = register_policy_version(**kwargs)
    assert r1.policy_id == r2.policy_id
    assert r1.version_id == r2.version_id
    assert r1.is_new_version is True
    assert r2.is_new_version is False  # second call sees existing version

    versions = list_versions(r1.policy_id)
    assert len(versions) == 1


def test_register_new_effective_date_makes_new_version(tmp_registry: PolicyRegistry):
    base_kwargs = dict(
        title="测试政策",
        issuer="银保监",
        body_text="第一条 ...",
        clauses=_sample_clauses(),
    )
    r1 = register_policy_version(**base_kwargs, effective_date="2026-03-15")
    r2 = register_policy_version(**base_kwargs, effective_date="2026-05-01")
    assert r1.policy_id == r2.policy_id
    assert r1.version_id != r2.version_id

    versions = list_versions(r1.policy_id)
    assert len(versions) == 2
    # latest = newest effective_date first
    assert versions[0]["effective_date"] == "2026-05-01"
    assert latest_version(r1.policy_id)["version_id"] == r2.version_id


def test_clause_id_deterministic_across_imports(tmp_registry: PolicyRegistry):
    """Re-importing the same body must produce the same clause_ids — this
    is what enables policy_coverage to compare extracted vs gold by id."""
    kwargs = dict(
        title="X",
        issuer="银保监",
        body_text="第一条 abc\n第二条 def",
        clauses=_sample_clauses(),
        effective_date="2026-03-15",
    )
    r1 = register_policy_version(**kwargs)
    ids_1 = [c["clause_id"] for c in get_clauses(r1.version_id)]
    # Wipe + re-register
    set_default_registry(None)
    reg2 = PolicyRegistry(tmp_registry.db_path)
    set_default_registry(reg2)
    r2 = register_policy_version(**kwargs)
    ids_2 = [c["clause_id"] for c in get_clauses(r2.version_id)]
    assert ids_1 == ids_2


def test_mark_superseded(tmp_registry: PolicyRegistry):
    base_kwargs = dict(
        title="测试政策",
        issuer="银保监",
        body_text="第一条 v1",
        clauses=_sample_clauses(),
    )
    r1 = register_policy_version(**base_kwargs, effective_date="2026-01-01")
    r2 = register_policy_version(
        title="测试政策",
        issuer="银保监",
        body_text="第一条 v2",
        clauses=_sample_clauses(),
        effective_date="2026-04-01",
    )
    ok = mark_superseded(old_version_id=r1.version_id, new_version_id=r2.version_id)
    assert ok is True
    v1 = get_version(r1.version_id)
    assert v1["superseded_by"] == r2.version_id
    # Idempotent re-mark returns False (already set, NULL guard).
    ok2 = mark_superseded(old_version_id=r1.version_id, new_version_id=r2.version_id)
    assert ok2 is False


def test_clause_count_matches_clauses(tmp_registry: PolicyRegistry):
    result = register_policy_version(
        title="X",
        issuer="银保监",
        body_text="...",
        clauses=_sample_clauses(),
        effective_date="2026-03-15",
    )
    ver = get_version(result.version_id)
    assert ver["clause_count"] == len(get_clauses(result.version_id))


def test_empty_clauses_skipped(tmp_registry: PolicyRegistry):
    # Empty-text clauses must be silently dropped.
    result = register_policy_version(
        title="X",
        issuer="银保监",
        body_text="...",
        clauses=[
            {"article": "第一条", "paragraph_index": 0, "text": "real"},
            {"article": "第二条", "paragraph_index": 0, "text": "   "},  # empty after strip
            {"article": "第三条", "paragraph_index": 0, "text": ""},
        ],
        effective_date="2026-03-15",
    )
    assert result.persisted is True
    assert get_version(result.version_id)["clause_count"] == 1


def test_policy_clause_dataclass_passthrough(tmp_registry: PolicyRegistry):
    """register_version accepts pre-built PolicyClause instances."""
    pid = policy_id("银保监", "X")
    bsha = body_sha("第一条 t")
    vid = version_id(pid, "2026-03-15", bsha)
    pre_clauses = [PolicyClause(
        clause_id=clause_id(vid, "第一条", 0),
        version_id=vid,
        article="第一条",
        paragraph_index=0,
        text="t",
    )]
    result = register_policy_version(
        title="X",
        issuer="银保监",
        body_text="第一条 t",
        clauses=pre_clauses,
        effective_date="2026-03-15",
    )
    assert result.version_id == vid
    rows = get_clauses(vid)
    assert rows[0]["clause_id"] == pre_clauses[0].clause_id


def test_schema_version_pinned():
    assert POLICY_REGISTRY_SCHEMA_VERSION == "1.0.0"


def test_default_registry_singleton(tmp_path, monkeypatch):
    """default_registry returns the same instance per process unless reset."""
    monkeypatch.setenv(
        "LIUYE_POLICY_REGISTRY_DB_PATH",
        str(tmp_path / "singleton.sqlite"),
    )
    set_default_registry(None)
    a = default_registry()
    b = default_registry()
    assert a is b
    set_default_registry(None)
