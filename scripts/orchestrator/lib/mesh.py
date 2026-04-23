"""Read and parse docs/handoff/mesh.json - the worktree registry."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


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


def load(mesh_json_path: Optional[Path] = None) -> Mesh:
    """Load mesh.json from default location (walking up from cwd) or given path."""
    if mesh_json_path is None:
        mesh_json_path = _find_mesh_json()
    p = Path(mesh_json_path)
    if not p.exists():
        raise FileNotFoundError(f"mesh.json not found at {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
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
    return Mesh(
        project=raw["project"],
        protocol_version=raw["protocol_version"],
        worktrees=worktrees,
        upstream_remote=raw["upstream_remote"],
        decisions_log=raw["decisions_log"],
        onboarding_dir=raw["onboarding_dir"],
        contracts_dir=raw["contracts_dir"],
        arch_contracts=raw.get("arch_contracts", ""),
        last_updated=raw.get("last_updated", ""),
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
