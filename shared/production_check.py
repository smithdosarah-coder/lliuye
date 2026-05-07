"""Production startup fail-fast check

per Phase C grounded report Tier 0.1 (PM 5/7 拍板 · Codex R2 加):

设计:
- 起动时 check critical dependency
- LIUYE_RUNTIME_MODE=production 时 fail fast 缺关键 dep (不 silent 起来)
- LIUYE_RUNTIME_MODE=dev (默认) 允许降级 + warn

check 项:
1. shared/llm_caller 可 import + 至少 1 provider 有 API key (DeepSeek 或 DashScope)
2. shared/decision_ledger sqlite 可写
3. data/audit/ 目录可写
4. data/ledger/ 目录可写

使用 (api_server.py 加):
    from shared.production_check import run_startup_checks
    run_startup_checks()  # production 缺 dep 抛 RuntimeError · dev warn
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NamedTuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class CheckResult(NamedTuple):
    name: str
    ok: bool
    detail: str


def _check_llm_provider() -> CheckResult:
    """至少 1 境内 LLM provider 有 API key (PIPL fallback chain)."""
    deepseek = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())
    dashscope = bool(os.environ.get("DASHSCOPE_API_KEY", "").strip())
    if deepseek:
        return CheckResult("llm_provider", True, "DeepSeek API key 已配置")
    if dashscope:
        return CheckResult("llm_provider", True, "DashScope API key 已配置")
    return CheckResult(
        "llm_provider",
        False,
        "DEEPSEEK_API_KEY / DASHSCOPE_API_KEY 全缺 · LLM 调用全 fallback rule (per PIPL fallback chain)",
    )


def _check_audit_dir() -> CheckResult:
    audit_dir = PROJECT_ROOT / "data" / "audit"
    try:
        audit_dir.mkdir(parents=True, exist_ok=True)
        # 试写一个 sentinel
        sentinel = audit_dir / ".write_test"
        sentinel.write_text("ok", encoding="utf-8")
        sentinel.unlink()
        return CheckResult("audit_dir", True, str(audit_dir))
    except (OSError, PermissionError) as e:
        return CheckResult("audit_dir", False, f"写失败: {e}")


def _check_ledger_dir() -> CheckResult:
    ledger_dir = PROJECT_ROOT / "data" / "ledger"
    try:
        ledger_dir.mkdir(parents=True, exist_ok=True)
        sentinel = ledger_dir / ".write_test"
        sentinel.write_text("ok", encoding="utf-8")
        sentinel.unlink()
        return CheckResult("ledger_dir", True, str(ledger_dir))
    except (OSError, PermissionError) as e:
        return CheckResult("ledger_dir", False, f"写失败: {e}")


def _check_llm_caller_import() -> CheckResult:
    try:
        from shared.llm_caller import provider as _  # noqa: F401
        return CheckResult("llm_caller_import", True, "shared/llm_caller 可 import")
    except ImportError as e:
        return CheckResult("llm_caller_import", False, f"import 失败: {e}")


def _check_decision_ledger_import() -> CheckResult:
    try:
        from shared.decision_ledger import default_ledger  # noqa: F401
        # 试取 store
        ledger = default_ledger()
        return CheckResult("decision_ledger", True, f"sqlite at {ledger.db_path}")
    except (ImportError, AttributeError, RuntimeError, OSError) as e:
        return CheckResult("decision_ledger", False, f"init 失败: {e}")


CHECKS = [
    _check_llm_caller_import,
    _check_llm_provider,
    _check_decision_ledger_import,
    _check_audit_dir,
    _check_ledger_dir,
]


def run_startup_checks(*, raise_on_fail: bool | None = None) -> dict:
    """跑 startup checks · 返结果 dict.

    Args:
        raise_on_fail: None (默认 · production 抛 / dev warn) · True 强制抛 · False 只 warn

    Returns:
        { "mode": str, "ok": bool, "checks": [CheckResult], "failures": [str] }

    Raises:
        RuntimeError: production 模式有 critical fail · 抛中止 startup
    """
    mode = os.environ.get("LIUYE_RUNTIME_MODE", "dev").lower()
    is_production = mode == "production"
    if raise_on_fail is None:
        raise_on_fail = is_production

    results: list[CheckResult] = []
    for check_fn in CHECKS:
        try:
            r = check_fn()
        except Exception as e:  # noqa: BLE001 · safety net
            r = CheckResult(check_fn.__name__, False, f"unexpected: {e}")
        results.append(r)

    failures = [r.name for r in results if not r.ok]
    overall_ok = len(failures) == 0

    # Print to stderr for visibility
    print(f"[production_check] mode={mode} · ok={overall_ok} · {len(failures)} fail", file=sys.stderr)
    for r in results:
        marker = "✓" if r.ok else "✗"
        print(f"[production_check]   {marker} {r.name} · {r.detail}", file=sys.stderr)

    if not overall_ok and raise_on_fail:
        raise RuntimeError(
            f"Production startup check FAILED · {len(failures)} critical dep missing: "
            f"{', '.join(failures)} · Fix env / config or set LIUYE_RUNTIME_MODE=dev to bypass"
        )

    return {
        "mode": mode,
        "ok": overall_ok,
        "checks": [{"name": r.name, "ok": r.ok, "detail": r.detail} for r in results],
        "failures": failures,
    }


__all__ = ["run_startup_checks", "CheckResult"]
