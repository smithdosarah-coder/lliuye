"""Parse and validate Signal trailers from git commit messages.

Format (per docs/contracts/shared-change-protocol.md §八):

    Signal: <NAME>

The trailer must appear on a line starting with "Signal:" followed by
an uppercase identifier with optional dashes/colons. NAME is parsed loosely
(format strict, name registry warn-only) so the protocol stays extensible.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Strict format: "Signal: NAME" where NAME starts with uppercase
SIGNAL_LINE_RE = re.compile(
    r"^\s*Signal:\s*([A-Z][A-Z0-9\-:.]*)\s*$",
    re.MULTILINE,
)

# Known signal name patterns (warn-only; format is enforced strictly)
KNOWN_SIGNAL_PATTERNS: List[re.Pattern] = [
    # Phase-batch protocol
    re.compile(r"^PHASE-\d+-(ONBOARDING|DISPATCHED|ACK|APPROVED|REJECTED|REVIEW)$"),
    re.compile(r"^PHASE-\d+-BATCH-\d+-(DISPATCHED|ACK|REVIEW)$"),
    re.compile(r"^READY-FOR-PHASE-\d+-REVIEW$"),
    # Generic done markers
    re.compile(r"^(TASK|OPTION)-[\w-]+-DONE$"),
    re.compile(r"^[A-Z][\w-]*-DONE$"),
    # Q/A protocol
    re.compile(r"^Q-\d+-(RAISED|AMENDMENT)$"),
    re.compile(r"^A-\d+-(RESOLVED|ACK)$"),
    re.compile(r"^ROUTED-Q-\d+$"),
    # RFC protocol
    re.compile(r"^RFC-[\w-]+-(RAISED|APPROVED|REJECTED|HOLD)$"),
    # Emergency / patch
    re.compile(r"^EMERGENCY-[\w-]+-PATCHED$"),
    # Orchestrator phases (P0-WT-LAUNCHER-UPGRADED, P1-FOUNDATION-LIB-READY etc.)
    re.compile(r"^P\d+-[\w-]+$"),
    # Window lifecycle
    re.compile(r"^WINDOW-CLOSED(-CLEAN)?$"),
    re.compile(r"^MAINTENANCE-(MODE|DELIVERABLE)$"),
    # Mesh registry
    re.compile(r"^MESH-[\w-]+$"),
    # Pipeline checkpoints
    re.compile(r"^RUNNER-CONSUMED$"),
    re.compile(r"^RED-LINE-TRIGGERED$"),
    re.compile(r"^BASELINE-ANCHORED$"),
    # Review handoff
    re.compile(r"^REVIEW-READY$"),
    re.compile(r"^REBASED-CLEAN$"),
    re.compile(r"^GO-\d+$"),
]


@dataclass
class SignalParseResult:
    found: bool                    # True if any "Signal: X" line found
    trailer: Optional[str]         # The signal name extracted (e.g. "REVIEW-READY")
    line_count: int                # Number of Signal: lines in message (should be 1)
    is_known: bool                 # True if matches a known pattern


def parse(commit_message: str) -> SignalParseResult:
    """Parse a commit message and extract Signal trailer info."""
    matches = SIGNAL_LINE_RE.findall(commit_message)
    if not matches:
        return SignalParseResult(False, None, 0, False)

    trailer = matches[-1]
    is_known = any(p.match(trailer) for p in KNOWN_SIGNAL_PATTERNS)

    return SignalParseResult(
        found=True,
        trailer=trailer,
        line_count=len(matches),
        is_known=is_known,
    )


def validate(commit_message: str, *, require_known: bool = False) -> Tuple[bool, List[str]]:
    """Validate a commit message's Signal trailer.

    Returns (is_valid, list_of_errors).

    Format errors (missing trailer, malformed syntax, multiple trailers) always fail.
    Unknown trailer names produce an error only if require_known=True.
    """
    errors: List[str] = []
    res = parse(commit_message)

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
        errors.append(
            f"unknown Signal name '{res.trailer}'; "
            f"see docs/contracts/shared-change-protocol.md for registry"
        )

    return len(errors) == 0, errors
