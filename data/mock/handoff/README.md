# Handoff Fixture · 6 Agent 主链路样例

每个 JSON 是一条主链路 handoff 载荷的**一个**真实形态样例。

| 文件 | 链路 | spec 节 |
|---|---|---|
| `agent1-to-6.json` | Agent1.candidate_company → Agent6.upload_intent | `docs/contracts/agent-handoff-schemas.md` §1 |
| `agent6-to-3.json` | Agent6.report_json → Agent3.decision_input | §2 |
| `agent3-to-4.json` | Agent3.decision → Agent4.client_pool_signal | §3 |
| `agent5-to-4.json` | Agent5.policy_event → Agent4 (alert 端 · target_agent="alert") | §4 |
| `agent5-to-6.json` | Agent5.policy_event → Agent6 (report 端 · target_agent="report") | §4 |

## 不是什么

- **不是** runtime 数据 — 真 handoff 文件按 §3.0 落 `data/handoff/<chain>/<session_id>/<id>.json` (在 `.gitignore` 内)
- **不是** test fixture — 给单测用的 fixture 落 `tests/fixtures/`
- **不是** 完整覆盖样本集 — 只给 1 个真实形态作 spec 锚点 · 验真覆盖留给各 worker
- **不是** 演示数据 — 演示在 `data/mock/<scenario>/` 各 agent 自己的 mock 池

## 是什么

每个 JSON 一份 · 用来:

1. 让 Phase A 7 worker 看到契约的真实形态 (而不是只看 schema 表)
2. 给 Phase B 端到端 demo chain (PM 拍板 Phase B-3) 提供初始 stub fixture
3. CI lint / contract test 校验 schema 时的"已知合法样本"

## 维护

`agent-handoff-schemas.md` schema 改 → 5 fixture (链路 1/2/3 各 1 + 链路 4 fan-out 拆 alert/report 共 2) 同步改 (主 CLI 把关)。
