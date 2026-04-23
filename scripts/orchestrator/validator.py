"""Validator entrypoint for the orchestrator self-healing mesh.

Used as a git ``commit-msg`` hook (and as a standalone CLI) to enforce that
every commit message carries a properly formatted ``Signal: <NAME>`` trailer.

CLI usage:

    py validator.py <commit-msg-file>      # hook mode (git passes .git/COMMIT_EDITMSG)
    py validator.py --check-known <file>   # also enforce known-name registry
    py validator.py                        # read message from stdin

Exit codes:

    0  validation passed
    1  validation failed (errors written to stderr)
    2  usage error / file not readable
"""
from __future__ import annotations

import sys
from pathlib import Path

# orchestrator package lives under scripts/orchestrator/.
# When invoked as `py scripts/orchestrator/validator.py ...`, the importable
# parent is scripts/, so we inject that on sys.path.
_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent))

from orchestrator.lib import signal  # noqa: E402


USAGE = (
    "usage: validator.py [--check-known] [<commit-msg-file>]\n"
    "       (with no file argument, reads commit message from stdin)\n"
)


def _read_message(path: str | None) -> str:
    if path is None:
        return sys.stdin.read()
    p = Path(path)
    if not p.is_file():
        sys.stderr.write(f"validator: cannot read commit-msg file: {path}\n")
        sys.exit(2)
    return p.read_text(encoding="utf-8", errors="replace")


def main(argv: list[str]) -> int:
    args = list(argv)
    require_known = False
    if "--check-known" in args:
        require_known = True
        args.remove("--check-known")
    if "-h" in args or "--help" in args:
        sys.stdout.write(USAGE)
        return 0
    if len(args) > 1:
        sys.stderr.write(USAGE)
        return 2

    msg_path = args[0] if args else None
    message = _read_message(msg_path)

    ok, errors = signal.validate(message, require_known=require_known)
    if ok:
        return 0

    sys.stderr.write("commit-msg validation FAILED:\n")
    for err in errors:
        sys.stderr.write(f"  - {err}\n")
    sys.stderr.write(
        "\nFix: append a trailer line like\n"
        "    Signal: REVIEW-READY\n"
        "to your commit message body. See docs/contracts/shared-change-protocol.md.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
