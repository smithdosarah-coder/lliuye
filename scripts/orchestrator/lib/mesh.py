"""Read and parse docs/handoff/mesh.json - the worktree registry."""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

CURRENT_SCHEMA_VERSION = 1

# Legacy defaults; kept here so the behaviour without a `thresholds` block in
# mesh.json matches the hard-coded values watchdog used in v1.
DEFAULT_IDLE_SECONDS = 3600
DEFAULT_ABANDONED_SECONDS = 86400 * 3


def _default_thresholds() -> Dict[str, int]:
    return {
        "idle_seconds": DEFAULT_IDLE_SECONDS,
        "abandoned_seconds": DEFAULT_ABANDONED_SECONDS,
    }


@dataclass
class Worktree:
    name: str
    path: Path
    branch: str
    role: str  # "orchestrator" | "worker"
    description: str = ""
    onboarding: Optional[str] = None


@dataclass
class Mesh:
    project: str
    protocol_version: str
    worktrees: List[Worktree]
    upstream_remote: str
    decisions_log: str
    onboarding_dir: str
    contracts_dir: str
    arch_contracts: str
    last_updated: str
    schema_version: int = 1
    project_id: str = ""  # canonical machine slug for Signal-namespace scoping (Y1)
    # Watchdog tunables (Y2). Keys: idle_seconds, abandoned_seconds.
    thresholds: Dict[str, int] = field(default_factory=_default_thresholds)


def load(mesh_json_path: Optional[Path] = None) -> Mesh:
    """Load mesh.json from default location (walking up from cwd) or given path."""
    if mesh_json_path is None:
        mesh_json_path = _find_mesh_json()
    p = Path(mesh_json_path)
    if not p.exists():
        raise FileNotFoundError(f"mesh.json not found at {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))

    schema_version = raw.get("schema_version")
    if schema_version is None:
        warnings.warn(
            f"mesh.json at {p} missing `schema_version`; assuming 1. "
            f'Add `"schema_version": 1` to silence.',
            DeprecationWarning,
            stacklevel=2,
        )
        schema_version = 1

    worktrees = [
        Worktree(
            name=w["name"],
            path=Path(w["path"]),
            branch=w["branch"],
            role=w["role"],
            description=w.get("description", ""),
            onboarding=w.get("onboarding"),
        )
        for w in raw["worktrees"]
    ]
    project = raw["project"]
    # project_id falls back to `project` when absent so legacy mesh.json Just Works;
    # new multi-project installations should set an explicit slug.
    project_id = raw.get("project_id") or project

    # thresholds block is optional; missing keys fall back to the legacy defaults.
    raw_thresholds = raw.get("thresholds") or {}
    thresholds = _default_thresholds()
    for key in thresholds:
        if key in raw_thresholds:
            try:
                thresholds[key] = int(raw_thresholds[key])
            except (TypeError, ValueError):
                warnings.warn(
                    f"mesh.json thresholds.{key} is not an int "
                    f"({raw_thresholds[key]!r}); falling back to default "
                    f"{thresholds[key]}",
                    UserWarning,
                    stacklevel=2,
                )

    return Mesh(
        project=project,
        protocol_version=raw["protocol_version"],
        worktrees=worktrees,
        upstream_remote=raw["upstream_remote"],
        decisions_log=raw["decisions_log"],
        onboarding_dir=raw["onboarding_dir"],
        contracts_dir=raw["contracts_dir"],
        arch_contracts=raw.get("arch_contracts", ""),
        last_updated=raw.get("last_updated", ""),
        schema_version=int(schema_version),
        project_id=project_id,
        thresholds=thresholds,
    )


def find_worktree(mesh: Mesh, name: str) -> Optional[Worktree]:
    """Return the worktree with given name, or None."""
    for w in mesh.worktrees:
        if w.name == name:
            return w
    return None


def _find_mesh_json() -> Path:
    """Walk up from cwd looking for docs/handoff/mesh.json."""
    cur = Path.cwd().resolve()
    for _ in range(20):  # cap walk depth
        candidate = cur / "docs" / "handoff" / "mesh.json"
        if candidate.exists():
            return candidate
        if cur.parent == cur:
            break
        cur = cur.parent
    raise FileNotFoundError("Could not locate docs/handoff/mesh.json walking up from cwd")
