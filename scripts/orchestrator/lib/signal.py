"""Parse and validate Signal trailers from git commit messages.

Format (per docs/contracts/shared-change-protocol.md §八):

    Signal: <NAME>

The trailer must appear on a line starting with "Signal:" followed by
an uppercase identifier with optional dashes/colons. NAME is parsed loosely
(format strict, name registry warn-only) so the protocol stays extensible.

Multi-project namespace (Y1):
    Multiple mesh projects can share a host without trailer collisions.
    Each project carries its own ``project_id`` (mesh.json top-level field).
    ``validate(..., project_id=X)`` first checks the project-specific registry
    in ``PROJECT_REGISTRIES`` (extensible at import time), then falls back to
    the shared ``KNOWN_SIGNAL_PATTERNS``. The trailer grammar itself is
    unchanged — the project scope is implicit via the caller's mesh context.
"""
from __future__ import annotations

import os
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Strict format: "Signal: NAME" where NAME starts with uppercase
SIGNAL_LINE_RE = re.compile(
    r"^\s*Signal:\s*([A-Z][A-Z0-9\-:.]*)\s*$",
    re.MULTILINE,
)


# ---- registry loading (Y4) --------------------------------------------------

# Default registry ships alongside this module at orchestrator/commit-signal-registry.yaml.
# Projects may override the path via $MESH_SIGNAL_REGISTRY.
_DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "commit-signal-registry.yaml"

# Minimal YAML-subset parser: understands `- pattern` list items under an
# optional `patterns:` header, plus `#` comments and blank lines. Avoids a
# hard dependency on PyYAML; real YAML files that stick to this subset load
# identically with or without the library installed.
_LIST_ITEM_RE = re.compile(r"^-\s+(.*)$")


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def _parse_registry_text(text: str) -> List[re.Pattern]:
    out: List[re.Pattern] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith(":") and not line.startswith("-"):
            # Skip mapping keys like `patterns:`.
            continue
        m = _LIST_ITEM_RE.match(line)
        if not m:
            continue
        pattern = _strip_quotes(m.group(1).strip())
        if not pattern:
            continue
        try:
            out.append(re.compile(pattern))
        except re.error as exc:
            warnings.warn(
                f"commit-signal-registry: skipping invalid regex {pattern!r}: {exc}",
                UserWarning,
                stacklevel=3,
            )
    return out


def load_registry(path: Optional[Path] = None) -> List[re.Pattern]:
    """Load regex patterns from a registry file. Returns [] if file missing."""
    if path is None:
        env_override = os.environ.get("MESH_SIGNAL_REGISTRY")
        path = Path(env_override) if env_override else _DEFAULT_REGISTRY
    if not path.is_file():
        return []
    return _parse_registry_text(path.read_text(encoding="utf-8"))


def _initial_patterns() -> List[re.Pattern]:
    patterns = load_registry()
    if not patterns:
        warnings.warn(
            f"commit-signal-registry not found at {_DEFAULT_REGISTRY} "
            f"(and $MESH_SIGNAL_REGISTRY unset); `require_known=True` will "
            f"reject every Signal name until the registry is restored.",
            UserWarning,
            stacklevel=2,
        )
    return patterns


# Known signal name patterns (loaded at import; reload via `reload_registry()`).
KNOWN_SIGNAL_PATTERNS: List[re.Pattern] = _initial_patterns()


def reload_registry(path: Optional[Path] = None) -> int:
    """Reload the global registry from disk. Returns new pattern count."""
    global KNOWN_SIGNAL_PATTERNS
    KNOWN_SIGNAL_PATTERNS = load_registry(path)
    return len(KNOWN_SIGNAL_PATTERNS)


# Project-scoped pattern registries. Populated by downstream code or tests.
# Key = project_id from mesh.json; value = extra patterns recognised ONLY
# for commits originating in that project. Lookup is additive on top of the
# global KNOWN_SIGNAL_PATTERNS.
PROJECT_REGISTRIES: Dict[str, List[re.Pattern]] = {}


def register_project_patterns(project_id: str, patterns: List[re.Pattern]) -> None:
    """Register additional known-signal patterns for a specific project_id."""
    PROJECT_REGISTRIES.setdefault(project_id, []).extend(patterns)


def _match_known(trailer: str, project_id: Optional[str]) -> bool:
    """Return True if trailer matches any global or project-scoped pattern."""
    if any(p.match(trailer) for p in KNOWN_SIGNAL_PATTERNS):
        return True
    if project_id:
        for p in PROJECT_REGISTRIES.get(project_id, ()):
            if p.match(trailer):
                return True
    return False


@dataclass
class SignalParseResult:
    found: bool                    # True if any "Signal: X" line found
    trailer: Optional[str]         # The signal name extracted (e.g. "REVIEW-READY")
    line_count: int                # Number of Signal: lines in message (should be 1)
    is_known: bool                 # True if matches a known pattern (global + project)
    project_id: Optional[str] = None  # The mesh project_id passed in, if any


def parse(
    commit_message: str, *, project_id: Optional[str] = None
) -> SignalParseResult:
    """Parse a commit message and extract Signal trailer info.

    If ``project_id`` is given, known-name matching additionally consults the
    project-scoped registry entries registered via
    :func:`register_project_patterns`.
    """
    matches = SIGNAL_LINE_RE.findall(commit_message)
    if not matches:
        return SignalParseResult(False, None, 0, False, project_id)

    trailer = matches[-1]
    is_known = _match_known(trailer, project_id)

    return SignalParseResult(
        found=True,
        trailer=trailer,
        line_count=len(matches),
        is_known=is_known,
        project_id=project_id,
    )


def validate(
    commit_message: str,
    *,
    require_known: bool = False,
    project_id: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """Validate a commit message's Signal trailer.

    Returns (is_valid, list_of_errors).

    Format errors (missing trailer, malformed syntax, multiple trailers) always fail.
    Unknown trailer names produce an error only if require_known=True.

    ``project_id`` scopes the known-name lookup to a project registry (see
    ``PROJECT_REGISTRIES`` and :func:`register_project_patterns`).
    """
    errors: List[str] = []
    res = parse(commit_message, project_id=project_id)

    if not res.found:
        errors.append(
            "missing Signal trailer "
            "(expect a line like 'Signal: <NAME>' in commit message body)"
        )
        return False, errors

    if res.line_count > 1:
        errors.append(
            f"multiple Signal trailers found ({res.line_count}); only one allowed"
        )

    if require_known and not res.is_known:
        scope = f" in project {project_id!r}" if project_id else ""
        errors.append(
            f"unknown Signal name '{res.trailer}'{scope}; "
            f"see docs/contracts/shared-change-protocol.md for registry"
        )

    return len(errors) == 0, errors
