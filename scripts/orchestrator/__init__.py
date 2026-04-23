"""Self-healing mesh orchestrator for credit_report_agent_work.

Modules (P1-P5):
    validator   - pre-commit Signal trailer enforcer
    scoreboard  - markdown render of mesh state
    watchdog    - 60s polling daemon
    recovery    - .bat generator for stuck workers
    launcher    - mesh.json register + AGENT_IDENTITY template

Foundation lib (this package):
    lib.mesh        - read+parse docs/handoff/mesh.json
    lib.signal      - parse+validate Signal trailers
    lib.git_helpers - per-worktree git ops
"""
__version__ = "0.1.0"
