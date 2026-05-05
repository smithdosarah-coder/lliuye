# -*- coding: utf-8 -*-
"""agent_compliance.policy_diff — difflib-based clause-level policy version diff.

Pure deterministic. Given two PolicyVersion ids (or two clause lists),
produce a list of `ClauseDiff` rows describing what changed: clauses
added, deleted, or modified (with similarity score and char-level hunks).

Why difflib?
  - Reproducibility: SequenceMatcher.ratio() is deterministic in CPython.
  - Auditability: 监管 / 审贷 / 合规官 needs to see "what got tightened"
    side-by-side with the regulator's wording — difflib produces
    pinpoint hunks rather than "the policy changed semantically".
  - Hard line: no LLM in the diff path (per onboarding red lines).

Matching strategy:
  1. Fast path: clauses sharing the same `article` label are paired by
     `paragraph_index`. Two clauses with identical text → unchanged
     (skipped from output). Different text → diff_type="change".
  2. Slow path: any clause unmatched after step 1 is fuzzy-matched
     across the *opposite* version using `difflib.SequenceMatcher.ratio`
     (threshold default 0.55). Match → "change" (article relocated).
     No match → "add" (new clause) or "delete" (removed clause).

Output is consumed by:
  - `agent_compliance.api.compliance_diff` (planned in BE4 #5)
  - `evaluation.runner.adapters.agent5_compliance` (conflict_recall by
    diff signal: a "change" or "add" against the prior version is what
    business cross_compare should pick up).
"""

from __future__ import annotations

import difflib
from dataclasses import asdict, dataclass, field
from typing import Iterable

from shared.policy_registry import PolicyClause, get_clauses

# Default fuzzy-match threshold for cross-article relocation. Tuned on the
# fixture pairs in tests/agent_compliance/test_policy_diff.py — values
# below 0.55 produced spurious matches between unrelated articles.
DEFAULT_FUZZY_THRESHOLD = 0.55

DIFF_TYPES = ("add", "delete", "change", "unchanged")


@dataclass
class ClauseDiff:
    """One row of a clause-level version diff.

    diff_type:
      - add        new in `to_clauses`, no match in `from_clauses`
      - delete     present in `from_clauses`, removed in `to_clauses`
      - change     paired old + new with similarity < 1.0
      - unchanged  paired old + new with similarity == 1.0
                   (omitted from default output; surfaced only via
                    `include_unchanged=True`)

    similarity in [0.0, 1.0]; 1.0 for unchanged, 0.0 for add/delete.

    hunks: list of human-readable change strings produced by
    `difflib.ndiff(old_text, new_text)`. Empty for add/delete (one side
    is None). Each hunk line starts with one of: '  ' / '- ' / '+ ' / '? '
    """

    diff_type: str
    old_clause_id: str | None
    new_clause_id: str | None
    old_article: str
    new_article: str
    old_text: str
    new_text: str
    similarity: float
    hunks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_clauses(clauses: Iterable[PolicyClause | dict]) -> list[dict]:
    """Coerce mixed inputs into plain dicts the diff loop can iterate over."""
    out: list[dict] = []
    for c in clauses or []:
        if isinstance(c, PolicyClause):
            out.append(asdict(c))
        elif isinstance(c, dict):
            out.append(c)
    return out


def _key(article: str, paragraph_index) -> tuple[str, int]:
    """Stable pair-key by (article, paragraph_index). Falls back to 0
    when paragraph_index is missing/None."""
    pi = 0 if paragraph_index is None else int(paragraph_index)
    return (str(article or ""), pi)


def _ratio(a: str, b: str) -> float:
    """Public wrapper around SequenceMatcher.ratio()."""
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a or "", b or "").ratio()


def _ndiff_hunks(old: str, new: str) -> list[str]:
    return list(difflib.ndiff((old or "").splitlines() or [""],
                              (new or "").splitlines() or [""]))


# ---------------------------------------------------------------------------
# Core diff
# ---------------------------------------------------------------------------


def diff_clauses(
    from_clauses: Iterable[PolicyClause | dict],
    to_clauses: Iterable[PolicyClause | dict],
    *,
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
    include_unchanged: bool = False,
) -> list[ClauseDiff]:
    """Compute a clause-level diff between two clause sets.

    Algorithm:
      1. Pair by (article, paragraph_index) — exact key.
         - Identical text → "unchanged".
         - Different text → "change", similarity = SequenceMatcher.ratio.
      2. For each unmatched clause on either side, run fuzzy match
         across the opposite side using ratio() ≥ fuzzy_threshold.
         Greedy best-match (highest ratio first); each clause is used
         at most once.
      3. Remaining unmatched in `from_clauses` → "delete".
         Remaining unmatched in `to_clauses`   → "add".

    Args:
        from_clauses: prior version (PolicyClause | dict)
        to_clauses:   later version
        fuzzy_threshold: minimum ratio to count as a relocation match
        include_unchanged: when True, "unchanged" rows are also emitted

    Returns: list[ClauseDiff].
    """
    src = _normalize_clauses(from_clauses)
    dst = _normalize_clauses(to_clauses)

    src_by_key = {_key(c.get("article"), c.get("paragraph_index")): c for c in src}
    dst_by_key = {_key(c.get("article"), c.get("paragraph_index")): c for c in dst}

    matched_src_ids: set[str] = set()
    matched_dst_ids: set[str] = set()
    out: list[ClauseDiff] = []

    # ----- Pass 1: exact-key match -----
    for key, src_c in src_by_key.items():
        dst_c = dst_by_key.get(key)
        if dst_c is None:
            continue
        old_text = src_c.get("text", "") or ""
        new_text = dst_c.get("text", "") or ""
        ratio = _ratio(old_text, new_text)
        matched_src_ids.add(src_c.get("clause_id", "") or "")
        matched_dst_ids.add(dst_c.get("clause_id", "") or "")
        if ratio >= 1.0:
            if include_unchanged:
                out.append(ClauseDiff(
                    diff_type="unchanged",
                    old_clause_id=src_c.get("clause_id"),
                    new_clause_id=dst_c.get("clause_id"),
                    old_article=src_c.get("article", ""),
                    new_article=dst_c.get("article", ""),
                    old_text=old_text,
                    new_text=new_text,
                    similarity=1.0,
                ))
        else:
            out.append(ClauseDiff(
                diff_type="change",
                old_clause_id=src_c.get("clause_id"),
                new_clause_id=dst_c.get("clause_id"),
                old_article=src_c.get("article", ""),
                new_article=dst_c.get("article", ""),
                old_text=old_text,
                new_text=new_text,
                similarity=round(ratio, 4),
                hunks=_ndiff_hunks(old_text, new_text),
            ))

    # ----- Pass 2: fuzzy match across remaining clauses -----
    src_remaining = [
        c for c in src
        if (c.get("clause_id", "") or "") not in matched_src_ids
    ]
    dst_remaining = [
        c for c in dst
        if (c.get("clause_id", "") or "") not in matched_dst_ids
    ]

    candidate_pairs: list[tuple[float, dict, dict]] = []
    for s in src_remaining:
        s_text = s.get("text", "") or ""
        for d in dst_remaining:
            d_text = d.get("text", "") or ""
            r = _ratio(s_text, d_text)
            if r >= fuzzy_threshold:
                candidate_pairs.append((r, s, d))
    # Highest similarity first; greedy resolution.
    candidate_pairs.sort(key=lambda x: -x[0])
    paired_src: set[int] = set()
    paired_dst: set[int] = set()
    for r, s, d in candidate_pairs:
        if id(s) in paired_src or id(d) in paired_dst:
            continue
        paired_src.add(id(s))
        paired_dst.add(id(d))
        out.append(ClauseDiff(
            diff_type="change",
            old_clause_id=s.get("clause_id"),
            new_clause_id=d.get("clause_id"),
            old_article=s.get("article", ""),
            new_article=d.get("article", ""),
            old_text=s.get("text", "") or "",
            new_text=d.get("text", "") or "",
            similarity=round(r, 4),
            hunks=_ndiff_hunks(s.get("text", "") or "", d.get("text", "") or ""),
        ))

    # ----- Pass 3: remaining = pure add / delete -----
    for s in src_remaining:
        if id(s) in paired_src:
            continue
        out.append(ClauseDiff(
            diff_type="delete",
            old_clause_id=s.get("clause_id"),
            new_clause_id=None,
            old_article=s.get("article", ""),
            new_article="",
            old_text=s.get("text", "") or "",
            new_text="",
            similarity=0.0,
        ))
    for d in dst_remaining:
        if id(d) in paired_dst:
            continue
        out.append(ClauseDiff(
            diff_type="add",
            old_clause_id=None,
            new_clause_id=d.get("clause_id"),
            old_article="",
            new_article=d.get("article", ""),
            old_text="",
            new_text=d.get("text", "") or "",
            similarity=0.0,
        ))

    return out


def diff_versions(
    from_version_id: str,
    to_version_id: str,
    *,
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
    include_unchanged: bool = False,
) -> list[ClauseDiff]:
    """Same as `diff_clauses` but pulls clauses from the registry."""
    return diff_clauses(
        get_clauses(from_version_id),
        get_clauses(to_version_id),
        fuzzy_threshold=fuzzy_threshold,
        include_unchanged=include_unchanged,
    )


def summarize_diff(diffs: Iterable[ClauseDiff]) -> dict:
    """Quick counters for UI / metrics.

    Returns: {add, delete, change, unchanged, total, avg_similarity}.
    avg_similarity is over `change` rows only (add/delete excluded; the
    average over add/delete would be a meaningless 0).
    """
    counters = {k: 0 for k in DIFF_TYPES}
    sims: list[float] = []
    for d in diffs or []:
        counters[d.diff_type] = counters.get(d.diff_type, 0) + 1
        if d.diff_type == "change":
            sims.append(d.similarity)
    counters["total"] = sum(counters.values())
    counters["avg_similarity"] = round(sum(sims) / len(sims), 4) if sims else 0.0
    return counters


__all__ = [
    "ClauseDiff",
    "DEFAULT_FUZZY_THRESHOLD",
    "DIFF_TYPES",
    "diff_clauses",
    "diff_versions",
    "summarize_diff",
]
