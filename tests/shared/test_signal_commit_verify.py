# -*- coding: utf-8 -*-
"""scripts/mesh/verify_signal_commit.py 单测.

per docs/contracts/signal-commit-contract.md §1-2.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "mesh" / "verify_signal_commit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_signal_commit", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["verify_signal_commit"] = mod
    spec.loader.exec_module(mod)
    return mod


verify_signal_commit = _load_module()


_VALID_READY = """\
chore(mesh): signal worker report ready for mesh merge ALLIN

完成摘要: report agent ALL IN 改造完成 · 删 mock UI + 真 source

改的文件清单:
- agent_report/api.py (+50/-30)
- web/src/app/archive/report/_components/ReportWorkspace.tsx (+200/-180)

测试 verify:
- pytest tests/agent_report/ → 32 passed
- web/tests/regression/report-candidate-id.spec.ts → 5 passed
- npx tsc --noEmit → 0 error

红线自检 (10 条):
1. ✅ 假 live · 2. ✅ 假分 · 3. ✅ 无证据 · 4. ✅ stub
5. ✅ 账本 · 6. ✅ 源健康 · 7. ✅ 回测 · 8. ✅ hash
9. ✅ 反馈链路 · 10. ✅ 落库一致

依赖合同:
- entity-resolution-contract v1.1
- candidate-identity-contract v1.1
- signal-commit-contract v1.1

base dashboard 行更新:
- record_id: rec123 · status: ready · latest_signal: <sha>

证据 (Playwright 截图 + 真测试日志):
- screenshots/report-allin-2026-05-09.png
- logs/pytest-2026-05-09.log

Worker: report
Phase: B
Refs: ALLIN-2026-05-08
Signal: READY
Root: aefa6907f7dc14fc8a35145ff7ec1fa4e5d353a
"""

_VALID_BLOCKED = """\
chore(mesh): signal worker credit ready for mesh merge ALLIN

Worker: credit
Phase: B
Refs: ALLIN-2026-05-08
Signal: BLOCKED
Root: aefa690
"""

_NON_SIGNAL_COMMIT = """\
feat(report): add new section generator

Worker: report
"""


class TestIsSignalCommit:
    def test_valid_signal(self):
        assert verify_signal_commit._is_signal_commit(_VALID_READY)

    def test_non_signal(self):
        assert not verify_signal_commit._is_signal_commit(_NON_SIGNAL_COMMIT)

    def test_almost_match_but_no(self):
        msg = "chore(mesh): signal worker report ready"  # 缺尾巴
        assert not verify_signal_commit._is_signal_commit(msg)


class TestVerifyReady:
    def test_valid_ready_no_violations(self):
        violations = verify_signal_commit.verify(_VALID_READY)
        assert violations == []

    def test_valid_ready_strict_body_no_violations(self):
        violations = verify_signal_commit.verify(_VALID_READY, strict_body=True)
        assert violations == []

    def test_blocked_minimal_no_violations_non_strict(self):
        violations = verify_signal_commit.verify(_VALID_BLOCKED)
        assert violations == []

    def test_non_signal_skip(self):
        violations = verify_signal_commit.verify(_NON_SIGNAL_COMMIT)
        assert violations == []


class TestSubjectViolations:
    def test_bad_subject_pattern(self):
        # 启发式 · 含 "signal worker" + "mesh" 但 subject 不严格匹配 (typo) → 报 subject 违规
        msg = "chore(mesh): signal worker report ready for mesh-merge ALLIN\n\nWorker: report\nPhase: B\nRefs: ALLIN-X\nSignal: READY\nRoot: abc1234\n"
        violations = verify_signal_commit.verify(msg)
        assert any("Subject 不符模板" in v for v in violations)

    def test_invalid_agent_name(self):
        msg = "chore(mesh): signal worker hacker ready for mesh merge ALLIN\n\nWorker: hacker\nPhase: B\nRefs: ALLIN-X\nSignal: READY\nRoot: abc1234\n"
        violations = verify_signal_commit.verify(msg)
        # subject regex 仅匹配 [a-z]+ · 但白名单挡
        assert any("不在白名单" in v for v in violations)


class TestTrailerViolations:
    def test_missing_trailer(self):
        msg = "chore(mesh): signal worker report ready for mesh merge ALLIN\n\nWorker: report\nPhase: B\nRefs: ALLIN-X\nSignal: READY\n"
        # 缺 Root:
        violations = verify_signal_commit.verify(msg)
        assert any("缺 trailer: Root:" in v for v in violations)

    def test_invalid_phase(self):
        msg = "chore(mesh): signal worker report ready for mesh merge ALLIN\n\nWorker: report\nPhase: X\nRefs: ALLIN-X\nSignal: READY\nRoot: abc1234\n"
        violations = verify_signal_commit.verify(msg)
        assert any("Phase 'X'" in v for v in violations)

    def test_invalid_signal(self):
        msg = "chore(mesh): signal worker report ready for mesh merge ALLIN\n\nWorker: report\nPhase: B\nRefs: ALLIN-X\nSignal: WIP\nRoot: abc1234\n"
        violations = verify_signal_commit.verify(msg)
        assert any("Signal 'WIP'" in v for v in violations)

    def test_invalid_refs(self):
        msg = "chore(mesh): signal worker report ready for mesh merge ALLIN\n\nWorker: report\nPhase: B\nRefs: SOMETHING-X\nSignal: READY\nRoot: abc1234\n"
        violations = verify_signal_commit.verify(msg)
        assert any("Refs 必以 'ALLIN-' 开头" in v for v in violations)

    def test_invalid_root_sha(self):
        msg = "chore(mesh): signal worker report ready for mesh merge ALLIN\n\nWorker: report\nPhase: B\nRefs: ALLIN-X\nSignal: READY\nRoot: not-a-sha\n"
        violations = verify_signal_commit.verify(msg)
        assert any("Root 必是 git sha" in v for v in violations)


class TestStrictBody:
    def test_strict_body_finds_missing_section(self):
        # _VALID_BLOCKED 缺 7 段
        violations = verify_signal_commit.verify(_VALID_BLOCKED, strict_body=True)
        assert len(violations) >= 7  # 7 段缺至少 7 个

    def test_non_strict_body_skips_section_check(self):
        # _VALID_BLOCKED 缺 7 段 · 但 non-strict 通过
        violations = verify_signal_commit.verify(_VALID_BLOCKED, strict_body=False)
        assert violations == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
