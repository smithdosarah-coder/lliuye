# -*- coding: utf-8 -*-
"""liuye_service.config — env vars dataclass + resolver.

Per W1-backend brief §3 file 2 + W2-backend brief §4.1 + perfect-check fix #2 +
``liuye_service/CLAUDE.md`` §1 + ``CLAUDE.md`` §3.7.5.

W1 env vars (4):

- ``LIUYE_ENABLED``       : bool · default False · v3 必修 #37 LIUYE gate (False → router not mounted)
- ``LIUYE_DEMO_MODE``     : bool · default False · True → adapters read fixtures from LIUYE_FIXTURES_PATH
- ``LIUYE_LEDGER_JURISDICTION`` : str · default "HQ" · root §3.7.5 (allowed: 银 / 保 / 证 / HQ / BRANCH)
- ``LIUYE_FIXTURES_PATH`` : str · default ``./tests/fixtures/`` · SSOT per W1-backend §4.10 + W1-mock-test §8

W2 env vars (4 · live mode + per-adapter URL 覆写 D10 hybrid 彩排):

- ``LIUYE_BACKEND_BASE_URL``    : str · default ``http://localhost:8000`` · live mode 走真 backend
- ``LIUYE_BACKEND_CHANNEL_URL`` : str | None · default None · 优先于 BASE (D10 hybrid · channel→mock :8001)
- ``LIUYE_BACKEND_CREDIT_URL``  : str | None · default None · 优先于 BASE (D10 hybrid · credit→live :8000)
- ``LIUYE_BACKEND_REPORT_URL``  : str | None · default None · 优先于 BASE (D10 hybrid · report→live :8000)

We deliberately use a plain dataclass instead of pydantic.BaseSettings here
because:

1. ``shared.decision_ledger.schema.resolve_jurisdiction`` already does the
   env read for the ledger jurisdiction — we mirror that pattern here so
   downstream callers see one consistent env contract.
2. The audit_service / auth_service do not depend on pydantic-settings,
   and the BFF should not add a new env-loading framework for a handful of flags.
3. A dataclass keeps the test surface trivial (``Settings.from_env()``).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Reuse the jurisdiction allowlist + default from decision_ledger so we never
# drift from BE7 schema (root §3.7.5 active rule).
from shared.decision_ledger.schema import (  # noqa: E402
    ALLOWED_JURISDICTIONS,
    DEFAULT_JURISDICTION,
)

# Default fixtures path (relative to project root · W1-mock-test SSOT).
# Mock-test worker owns the fixture files in ``tests/fixtures/`` · backend
# adapters MUST NOT keep a second copy in ``liuye_service/fixtures/demo/``
# (drift risk per W1-backend §4.10).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent  # credit_report_agent_work/
_DEFAULT_FIXTURES_PATH = (_PROJECT_ROOT / "tests" / "fixtures").as_posix()


def _parse_bool(raw: str | None, *, default: bool) -> bool:
    """Parse boolean env var · default on missing/empty.

    Truthy: 1 / true / yes / on (case-insensitive)
    Falsy:  0 / false / no / off / empty
    """
    if raw is None:
        return default
    val = raw.strip().lower()
    if not val:
        return default
    return val in {"1", "true", "yes", "on"}


# W2 backend brief §4.1 default · live mode talks to real backend uvicorn :8000
_DEFAULT_BACKEND_BASE_URL = "http://localhost:8000"


@dataclass(frozen=True)
class Settings:
    """Immutable BFF configuration snapshot · resolved from env at import or boot.

    Use ``Settings.from_env()`` to materialize a snapshot. Frozen so that
    a long-running FastAPI process doesn't accidentally see flag changes
    mid-request (use ``set_default_settings`` in tests for overrides).
    """

    enabled: bool = False
    demo_mode: bool = False
    ledger_jurisdiction: str = DEFAULT_JURISDICTION
    fixtures_path: str = _DEFAULT_FIXTURES_PATH
    # W2 backend brief §4.1 + perfect-check fix #2 · live mode 走真 backend
    # + D10 hybrid 彩排 per-adapter URL 覆写
    backend_base_url: str = _DEFAULT_BACKEND_BASE_URL
    backend_channel_url: str | None = None
    backend_credit_url: str | None = None
    backend_report_url: str | None = None

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        """Read all env vars and return a frozen snapshot.

        Args:
            env: optional override map (test injection). Defaults to ``os.environ``.
        """
        src = env if env is not None else os.environ
        jurisdiction = (
            src.get("LIUYE_LEDGER_JURISDICTION", "").strip()
            or DEFAULT_JURISDICTION
        )
        if jurisdiction not in ALLOWED_JURISDICTIONS:
            # Mirror decision_ledger.resolve_jurisdiction error semantics —
            # fail loud so misconfig doesn't silently write to the wrong
            # bucket. Callers MAY catch + fall back to DEFAULT_JURISDICTION.
            raise ValueError(
                f"LIUYE_LEDGER_JURISDICTION must be one of "
                f"{sorted(ALLOWED_JURISDICTIONS)}, got {jurisdiction!r}"
            )
        fixtures = (
            src.get("LIUYE_FIXTURES_PATH", "").strip()
            or _DEFAULT_FIXTURES_PATH
        )
        # W2 4 backend URL · empty string → fall back to default (BASE) /
        # None (per-adapter), not a literal empty URL.
        base = (
            src.get("LIUYE_BACKEND_BASE_URL", "").strip()
            or _DEFAULT_BACKEND_BASE_URL
        )
        channel_url = src.get("LIUYE_BACKEND_CHANNEL_URL", "").strip() or None
        credit_url = src.get("LIUYE_BACKEND_CREDIT_URL", "").strip() or None
        report_url = src.get("LIUYE_BACKEND_REPORT_URL", "").strip() or None
        return cls(
            enabled=_parse_bool(src.get("LIUYE_ENABLED"), default=False),
            demo_mode=_parse_bool(src.get("LIUYE_DEMO_MODE"), default=False),
            ledger_jurisdiction=jurisdiction,
            fixtures_path=fixtures,
            backend_base_url=base,
            backend_channel_url=channel_url,
            backend_credit_url=credit_url,
            backend_report_url=report_url,
        )

    def resolve_backend_url(self, agent_id: str) -> str:
        """Per-adapter URL 覆写 (W2 brief §4.1 + perfect-check fix #2).

        Resolution order (first non-empty wins):

        1. ``LIUYE_BACKEND_{AGENT}_URL`` (e.g. ``LIUYE_BACKEND_CHANNEL_URL``)
           — D10 hybrid 彩排支持 (channel→mock :8001 + credit/report→live :8000)
        2. ``LIUYE_BACKEND_BASE_URL`` (default ``http://localhost:8000``)

        Returns the base URL only · per-adapter ``_ENDPOINT_MAP`` adds the
        path segment (e.g. ``/api/channel/run``).
        """
        per_adapter = getattr(self, f"backend_{agent_id}_url", None)
        return per_adapter or self.backend_base_url


# ---------------------------------------------------------------------------
# Process-wide singleton (lazy · mirrors decision_ledger.default_ledger pattern)
# ---------------------------------------------------------------------------

_default_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the process-wide Settings snapshot · resolves env on first call."""
    global _default_settings
    if _default_settings is None:
        _default_settings = Settings.from_env()
    return _default_settings


def set_default_settings(settings: Settings | None) -> None:
    """Test helper · inject or reset the singleton."""
    global _default_settings
    _default_settings = settings


__all__ = [
    "Settings",
    "get_settings",
    "set_default_settings",
]
