# -*- coding: utf-8 -*-
"""shared.policy_registry — versioned policy + clause sqlite store (BE4).

Per docs/contracts/agent-compliance-policy-registry.md v1.0.

Distinct from `agent_compliance.scan_engine` (matrix runtime) and from
`shared.decision_ledger` (cross-agent decision audit log):

  - scan_engine        = "given a policy text + business docs, run a scan"
  - decision_ledger    = "which decisions were made, by whom, what evidence"
  - policy_registry    = "what policies exist, what versions, what clauses"

The registry is the long-lived source of truth Agent5 reads when computing
policy_coverage / conflict_recall and when diffing two policy versions
(see `agent_compliance.policy_diff`).

Public surface:
  - ``PolicyDocument`` / ``PolicyVersion`` / ``PolicyClause`` dataclasses
  - ``PolicyRegistry`` sqlite-backed store (test-injectable)
  - ``register_policy_version(...)`` writer · idempotent · silent-fail
  - ``get_policy / get_version / list_versions / latest_version / get_clauses``
  - ``mark_superseded(...)`` link old → new for diff/audit
  - ``policy_id / version_id / clause_id / body_sha / canonical_hash`` helpers

Author: worker-B4-compliance · 2026-05-04 · BE4 Phase B Sprint 2.
"""

from __future__ import annotations

from .hashing import (
    body_sha,
    canonical_hash,
    canonical_json,
    clause_id,
    policy_id,
    version_id,
)
from .schema import (
    ALLOWED_ISSUERS,
    DEFAULT_ISSUER,
    POLICY_REGISTRY_SCHEMA_VERSION,
    PolicyClause,
    PolicyDocument,
    PolicyVersion,
)
from .store import (
    DEFAULT_DB_PATH,
    PolicyRegistry,
    RegisterResult,
    default_registry,
    get_clauses,
    get_policy,
    get_version,
    latest_version,
    list_versions,
    mark_superseded,
    register_policy_version,
    set_default_registry,
)

__all__ = [
    "ALLOWED_ISSUERS",
    "DEFAULT_DB_PATH",
    "DEFAULT_ISSUER",
    "POLICY_REGISTRY_SCHEMA_VERSION",
    "PolicyClause",
    "PolicyDocument",
    "PolicyRegistry",
    "PolicyVersion",
    "RegisterResult",
    "body_sha",
    "canonical_hash",
    "canonical_json",
    "clause_id",
    "default_registry",
    "get_clauses",
    "get_policy",
    "get_version",
    "latest_version",
    "list_versions",
    "mark_superseded",
    "policy_id",
    "register_policy_version",
    "set_default_registry",
    "version_id",
]
