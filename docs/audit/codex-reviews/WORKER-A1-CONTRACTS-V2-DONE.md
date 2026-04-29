verdict: AGREE

issue-1-fixed: yes  
CI lint now exists and is wired: `.github/workflows/lint-contracts.yml:1`, `.github/workflows/lint-contracts.yml:38`, `scripts/lint/check_agent_naming_ssot.py:1`. I also ran it in the target worktree: `0 error · 1 warn`, PASS in non-strict mode. The remaining WARN is the known `compli/compliance` PM-pending split.

issue-2-fixed: yes  
The priority ladder now matches the requested order: `docs/contracts/* > root CLAUDE.md > scoped child CLAUDE.md > onboarding > decisions-log`, with only `docs/arch/instruction-source-of-truth.md` as a meta exception. See `docs/arch/instruction-source-of-truth.md:25-68` and `CLAUDE.md:321-338`.

issue-3-fixed: yes  
The heading now says `5 tier · ... + 1 meta 例外`, and code is explicitly `Tier 0 · 非文档`, not counted as a document tier. See `docs/arch/instruction-source-of-truth.md:25` and `docs/arch/instruction-source-of-truth.md:50`.

issue-4-fixed: yes  
`sse-envelope.md` now includes a normative event-name table covering the 7 event names and their payload sources. See `docs/contracts/sse-envelope.md:41-72`.

remaining concerns:
- `docs/contracts/agent-naming-ssot.md:240-242`: acceptance checklist is stale; it still says “§4 CI lint 规则定义 (实现待 worker-A2)” and “§4 CI lint 真落地 → Phase A 硬线 #8 met”, even though V2 added the script/workflow. This is documentation drift, not a blocker against the 4 V1 issues.
- `docs/contracts/agent-naming-ssot.md:166`: duplicate `### 4.2 后端 mount prefix 共形` section remains after the new V2 section.
- `docs/arch/instruction-source-of-truth.md:97` and `docs/arch/instruction-source-of-truth.md:128`: still refer to `Tier 1-3` for backwrite/stale rules, while `CLAUDE.md:336-338` says `Tier 1-2`. Minor consistency cleanup needed.