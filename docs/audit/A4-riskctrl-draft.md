# Worker-A4-Riskctrl Onboarding · DRAFT (pre-A3-cherry-pick)

> **状态**: DRAFT v0 · 主 CLI plan-only 起草 · A3 channel pilot DONE + cherry-pick + 主 CLI GO 之前 worker 不动一行代码。
>
> **作者**: 主 CLI · 2026-04-29 · 与 A4-credit / A4-alert / A4-compli / A4-report 4 兄弟 worker 同批起草 · 共享 §0.5 wait gate
>
> **dispatch commit**: `25de8de · PHASE-A-A4-RISKCTRL-DISPATCHED` (已发出 · worker 物理 worktree 已 checkout `feat/phase-a4-riskctrl-adapter` · 仍处 wait 状态)

---

## 0. 复用 worktree (已建好)

- worktree: `D:\claude code\work-A4-riskctrl`
- 已 checkout branch: `feat/phase-a4-riskctrl-adapter` (派生 chore/l0-infra · A1+A2 V2 DONE 后)
- **resume 第一步**: cd 到 worktree · `git status` 确认 clean · 再读本 doc §0.5 wait gate 是否解锁
- **不需 git fetch / pull**:base branch 已含 A1+A2 V2 全产出 (5 契约 + shared/llm_caller + shared/sse_envelope + shared/prompts/contract)

---

## 0.5 ⚠️ HARD WAIT GATE (本 worker 红区硬规)

A4 子 worker 与 A3 不是简单并行 · charter §3 worker-A4 verbatim: **"5 子 worker 并行 · 依赖 A3 完"**。理由:

1. A4 是 A3 channel pilot 的**复制**——若 A3 模板未定型就开干 · 5 子 worker 各自实现一套 4 gate · merge 时 5 套差异要回退合并 · 是 reset 工程**最确定的塌方点**。
2. A3 改了 `workspace-state-protocol.md` 的实装范本 (panel 接 props / 5 panel sessionData 派生 / candidate drawer pattern) · 这套范本是 A4 复用唯一可信来源。
3. A3 的 `agent_channel/api.py` SSE done envelope 字段命名是 6 agent SSE 共形 spec (sse-envelope.md §1.5 7 event 名表 + workspace-state-protocol §4 done payload) 在 channel 域的具体投影 · A4 必须**镜像复制**而非自创。

### 0.5.1 解锁条件 (4 项全 yes 才进 §1)

| # | 条件 | 怎么验 |
|---|---|---|
| 1 | A3 worker DONE | `git log --grep "Signal: WORKER-A3-CHANNEL-PILOT-DONE"` 有命中 · 且 codex post-DONE peer review AGREE |
| 2 | A3 cherry-picked → chore/l0-infra | base branch 含 ChannelWorkspace.tsx 4 gate impl + agent_channel/api.py done envelope 完整 |
| 3 | 主 CLI GO signal | decisions-log Q-NNN-A4-RISKCTRL-GO 有 PM 拍 GO · 或主 CLI 发 commit `Signal: PHASE-A-A4-RISKCTRL-GO` |
| 4 | 本 worktree rebase 到 A3 后 base | `git rebase chore/l0-infra` 干净 (无冲突) · `cd web && npx tsc --noEmit` 0 error |

### 0.5.2 wait 期间允许活动

- 读本 doc · 读 §3 必读清单 · 读 A3 ChannelWorkspace 实装 (post-DONE)
- 读 codex 4 issue verdict (插入点 2) — 如 codex DISAGREE 改了 A3 模板 · 同步认知
- **写**: 只允许写 `docs/audit/A4-riskctrl-{draft,scratch}.md` · 不动 `agent_riskctrl/*` · 不动 `web/*` · 不动 `shared/*`
- **commit**: 只允许 trailer `Signal: WORKER-A4-RISKCTRL-WAITING` 的 audit-doc commit · 不允许任何 code commit

### 0.5.3 违 wait gate 后果

任何 code 文件改动 (agent_riskctrl/*.py · web/src/app/archive/riskctrl/* · web/src/lib/api/riskctrl.ts · web/src/lib/mock/agent-riskctrl-*) 在 A3 cherry-pick 完成前 · 主 CLI 见即 revert · 不问。Reset 工程 §13 ECS 同步纪律 + §14 状态文档实时更新 + 本 §0.5 共构红区硬闸 · 三者并列。

---

## 1. 任务 (verbatim from `docs/reset/phase-a-charter.md` §3 worker-A4)

| # | 交付 | 内容要点 |
|---|---|---|
| 1 | `RiskctrlWorkspace.tsx` 重构 4 gate · 复用 A3 模式 | started / selectedSession / liveData / selectedCandidate (后者在 riskctrl 域语义化为 selectedRule 或 selectedSampleSegment · 见 §4.1) |
| 2 | `agent_riskctrl/api.py` done event 加 envelope | 当前 `非 SSE` · 升级为 SSE · done payload 含 ruleset / ks / samples / rule_stats / metrics (见 §4.2) |
| 3 | Demo `/api/riskctrl/demo/run` 端点 | 单独 mount · 走 fixture `data/mock/workspace/riskctrl/scenarios/*.json` · prod 端点不 silent fallback |
| 4 | Playwright smoke ≥3 spec | mock-switch / live-search (DSL gen) / sample-segment-detail-drawer |
| 5 | (兼任 · 5 子之一) 共享 hook 抽出 | `useWorkspaceRun.ts` + `WorkspaceBanner.tsx` + `EmptyWorkspace.tsx` + `sseWorkspaceClient.ts` (PM 拍板由哪一子 worker 兼任 · 见 §6.2) |
| 6 | `agent_riskctrl/llm_judge.py` 迁 A2 路径 | LLMJudge._get_client() 改用 `shared.llm_caller.LLMCaller` · 不再直 `from llm import LLMClient` |
| 7 | export 三件套 endpoint 草 | `/api/riskctrl/export_docx` + `_xlsx` + `_pdf` · 与 A6 worker export contract 共形 (audit Cat 13) |

**Phase A 验收硬线 #4** (`docs/reset/phase-a-charter.md` §1): "5 agent thin adapter 完 · Riskctrl 迁 4 gate + result-driven · Playwright smoke 通过"

---

## 2. 当前状态盘点 (audit Cat 3 / 4 / 7 / 13 verbatim)

### 2.1 Frontend ↔ Backend contract 三处 mismatch (red flag)

| # | 现象 | 文件:行 | 后果 |
|---|---|---|---|
| 1 | 前端用 `streamSse` 调 dsl_gen · 后端注释 "非 SSE" 一次性 JSON | `web/src/lib/api/riskctrl.ts:54` vs `agent_riskctrl/api.py:50` | EventSource 等不到 message · UI 永远 spinning · LiveFailError 误报 |
| 2 | 字段名不一致 · 前端 `rule_text` · 后端 `strategy_intent` | `web/src/lib/api/riskctrl.ts:50` vs `agent_riskctrl/api.py:85` | 422 Unprocessable Entity (Pydantic missing field) |
| 3 | backtest body 形态完全错位 · 前端 `{instruction, uploaded_files}` · 后端 `{ruleset, csv_path, label_column?, bad_threshold?}` | `web/src/lib/api/riskctrl.ts:69-73` vs `agent_riskctrl/api.py:170-183` | 422 + 后端无法解析 ruleset · backtest 一直跑不通 |
| 4 | export_docx endpoint 不存在 · 仅前端 stub + 404 容忍 | `web/src/lib/api/riskctrl.ts:80` · 后端无 mount | UI 显 "导出端点 /api/riskctrl/export_docx 待 Stage D 后端实装" stale 字面 |

**根因**: 前端按 v3.x SSE 契约写 · 后端 v4.0 改 JSON 单 turn (注释 "Stage C v4.0 · onboarding W-C2-A2") · 双方各自迭代未对齐。A4 worker = 本次拉齐机会。

### 2.2 Workspace state 散乱 (audit Cat 2)

`web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx:98-122` 当前持 13 个 useState:

```
started · trigger · recent · preset · scanned · scanRunning · scanError ·
rulesetId · exportInfo · liveFail · retryHandler · (composer 内 value/hint)
```

不符 `workspace-state-protocol.md` §2 强制 4 gate · 与 channel `ChannelWorkspace.tsx` 当前散乱状态同病。

### 2.3 LLM caller 直 import root llm (audit Cat 7 第 3 处)

`agent_riskctrl/llm_judge.py:123` 直 `from llm import LLMClient` · 是 A2 onboarding §2 列出 4+1 套 caller 的第 3 处 · A2 V2 ACK 已写明 deprecation path:
> caller 3 (llm_judge): `LLMCaller(agent_id="riskctrl", endpoint="judge").simple_chat`

`agent_riskctrl/api.py:141` 同样直 `from llm import LLMClient` · 同迁。

### 2.4 Mock session 单 const (audit Cat 5 + workspace-state-protocol §3)

`web/src/lib/mock/agent-riskctrl-session.ts` 是单 const `RISKCTRL_SESSION` · 不符 §3 强制 ≥3 sessions array · 切下拉无效 (RecentPanel:805-815 的 `<select>` 仅装样子 · onChange 没接 setSelectedSession)。

---

## 3. 必读 (前置上下文 · 按顺序)

| 文件 | 用途 |
|---|---|
| `RESET_MASTER_PLAN.md` | umbrella |
| `docs/reset/north-star.md` §1.4 + §3.2 | 6 Agent 闭环 + LLM caller 修正方向 |
| `docs/reset/phase-a-charter.md` §3 worker-A4 + §1 硬线 #4 | 任务 + 验收 |
| `docs/contracts/workspace-state-protocol.md` v1.1 (A1 V2 产) | §2 4 gate + §3 mock array + §4 SSE done envelope + §5 detail drawer + §7 7 步 migration 模板 |
| `docs/contracts/sse-envelope.md` v1.0 §1.5 (A1 V2 产) | 7 event 名 normative table + done payload schema |
| `docs/contracts/agent-naming-ssot.md` v1.0 (A1 产) | riskctrl 命名 · 不再用旧 forge 别名 (audit Cat 8 余波) |
| `docs/contracts/llm-prompt-contract.md` v1.0 (A1 产) | 8 段 template · llm_judge 重写 prompt 时 align |
| `docs/contracts/agent-forge-spec.md` (旧名 · A6 worker 可能迁 agent-riskctrl-spec.md) | Riskctrl 业务边界 · DSL + 回测语义 |
| `docs/audit/conflict-register-v1.md` | 你 owner: cat 3 (riskctrl 行) + cat 4 (riskctrl SSE) + cat 7 (llm_judge) + cat 13 (export 三件套) |
| `docs/audit/sub-agent-step2-round1/architecture.md` Cat 4 | backend SSE schema 6 agent done payload 形态 verbatim |
| `docs/audit/sub-agent-step2-round1/instruction.md` Cat 7 | 4+1 caller list verbatim · llm_judge:123 + api.py:141 双处 |
| `shared/llm_caller/__init__.py` (A2 V2 产) | LLMCaller 主入口 · simple_chat / make_text_caller / make_json_caller |
| `shared/sse_envelope.py` (A2 V2 产) | make_done / make_stage / make_error helper · A4 backend SSE 化时直消费 |
| `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (A3 DONE 后) | **复用模板** · 你 4 gate 实装直照搬 · 不自创 |
| `agent_channel/api.py` (A3 DONE 后) | **SSE done envelope 模板** · 你 backend 实装照搬字段命名风格 (snake_case) |
| `agent_riskctrl/api.py` 全文 | 现状 · 你重写起点 |
| `agent_riskctrl/llm_judge.py` 全文 | 现状 · 你 §6 迁移起点 |
| `web/src/lib/api/riskctrl.ts` 全文 | 现状 · 你 frontend client 重写起点 |
| `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx` 全文 | 现状 · 你 frontend workspace 重写起点 |
| `web/src/lib/mock/agent-riskctrl-session.ts` (单 const) | 你迁 array · 改名 `agent-riskctrl-sessions.ts` (复数) |

---

## 4. 改造方案 (4 gate · SSE envelope · llm_judge · export)

### 4.1 4 gate 改造

按 `workspace-state-protocol.md` §2 复用 A3 模板 · riskctrl 域语义投影:

```tsx
const [started, setStarted] = useState<boolean>(false);
const [selectedSession, setSelectedSession] = useState<string>(
  RISKCTRL_MOCK_SESSIONS[0].id,
);
const [liveData, setLiveData] = useState<RiskctrlSession | null>(null);
const [selectedRuleOrSegment, setSelectedRuleOrSegment] = useState<
  { kind: "rule"; id: string } | { kind: "segment"; key: string } | null
>(null);
```

**与 channel 命名 diff**: `selectedCandidate` → `selectedRuleOrSegment` (riskctrl 不针对单客户 · RiskctrlWorkspace.tsx:531-532 已注 "CustomerSelector 不适用" · 业务对象是规则节点 + 样本分档 segment)。

`sessionData` 派生:
```tsx
const sessionData = liveData
  ?? RISKCTRL_MOCK_SESSIONS.find(s => s.id === selectedSession)
  ?? RISKCTRL_MOCK_SESSIONS[0];
```

5 panel 全接 props:
- `RiskHero({ sessionData })` · 替 `const s = RISKCTRL_SESSION` (line 521)
- `RiskIndicatorRow({ sessionData })` · 替 line 550
- `QueryPanel({ sessionData })` · 替 line 673
- `RulesPanel({ sessionData, onSelectRule })` · 加 onClick · setSelectedRuleOrSegment
- `RiskOutputPanel({ sessionData, rulesetId, exportInfo, onExportDocx, onSelectSegment })` · 加 SampleView segment onClick

13 个散 useState 收敛为 4 gate + 3 仅 UI 状态 (composer 局部 / pinhandle / drawer · 不进顶层契约)。其余 (rulesetId / exportInfo / scanRunning / scanError / liveFail / retryHandler) 全部下沉为 `liveData.meta` 子字段 · 不再独立 useState。

Mock session: `web/src/lib/mock/agent-riskctrl-sessions.ts` (新建复数) · ≥3 session:
- `sess_credit_v15`: KS 0.42 / 通过 32% (绿区 · 简单档)
- `sess_aml_kyc`: KS 0.31 / 通过 18% (关注区 · 中等档)
- `sess_fraud_high`: KS 0.28 / 通过 8% (红区 · 极端档 · 反 5 原则 §3.5 难度分层)

3 session 间 ruleset / ks.points / samples / rule_stats 实质不同 · 禁 deep-copy 改名。

### 4.2 agent_riskctrl SSE done envelope 设计

依 `docs/contracts/sse-envelope.md` §1.5 7 event 名 normative table + `workspace-state-protocol.md` §4 done payload spec · riskctrl 域投影:

**两端点都升 SSE** (前端已用 `streamSse` · 反方向对齐):

```
POST /api/riskctrl/dsl_gen     · SSE
POST /api/riskctrl/backtest    · SSE
POST /api/riskctrl/export_docx · 同步 binary blob (非 SSE · 见 §4.4)
POST /api/riskctrl/export_xlsx · 同步 binary blob
POST /api/riskctrl/export_pdf  · 同步 binary blob
POST /api/riskctrl/demo/run    · SSE · 走 fixture · prod 与 demo 物理隔离 endpoint
```

**dsl_gen SSE event 序列** (event 名 verbatim from sse-envelope §1.5):

```
event: stage   · payload: {stage:"parse_intent",   pct:10}
event: stage   · payload: {stage:"build_prompt",   pct:25}
event: stream  · payload: {delta:"...LLM partial..."}    (含 LLM token 流 · LLMCaller 透传)
event: stage   · payload: {stage:"validate_dsl",   pct:80}
event: done    · payload: {ruleset, ruleset_id, source:"llm"|"mock", csv_columns?}
(失败) event: error · payload: {code, message, retryable}
```

**backtest SSE event 序列**:

```
event: stage  · payload: {stage:"load_csv",        pct:15}
event: stage  · payload: {stage:"hit_rules",       pct:40}
event: stage  · payload: {stage:"calc_ks",         pct:70}
event: done   · payload: {
  metrics: {totalRecords, approved, rejected, manualReview, approvalRate, badRate, ks, labelColumnUsed},
  ks: {ksPeak, auc, passRate, badRate, points: [{bin, tpr, fpr, ks}, ...]},
  samples: [{key, label, count, pct, badRate}, ...],
  rule_stats: [{ruleId, hit, fp, tn}, ...],
  session_id: "...",
}
```

**done payload 共形规则** (与 5 兄弟 agent 对齐 · channel/credit/alert/compli/report 同 schema 框架 · 仅 panel 字段名按 agent 域换):
- 顶层必含: `session_id` (str) · `metrics` (dict · 各 agent 自定 · KPI 卡用)
- panel 字段一律 snake_case · 前端 `normalize()` 转 camelCase (per ChannelWorkspace 模板)
- 错误走 `event: error` · 不静默 200 + empty payload (sse-envelope §3.6 PIPL fallback chain 规)

**Backend impl 要点**:

```python
# agent_riskctrl/api.py 重写后
from shared.sse_envelope import make_stage, make_done, make_error
from shared.llm_caller import LLMCaller

@app.post("/api/riskctrl/dsl_gen")
@audit_llm_call(agent_id="riskctrl", endpoint="/api/riskctrl/dsl_gen")
async def riskctrl_dsl_gen(req: DslGenRequest):
    return EventSourceResponse(_dsl_gen_stream(req))

async def _dsl_gen_stream(req: DslGenRequest):
    yield make_stage("parse_intent", pct=10)
    yield make_stage("build_prompt", pct=25)
    caller = make_json_caller(agent_id="riskctrl", endpoint="dsl_gen")
    async for chunk in caller.stream(system=SYSTEM_RULE_PARSER, user=user_prompt):
        yield {"event": "stream", "data": json.dumps({"delta": chunk})}
    yield make_stage("validate_dsl", pct=80)
    ruleset = parse_natural_language_rules(...)
    yield make_done(panels={"ruleset": ruleset.model_dump(), "ruleset_id": ...,
                            "source": "llm", "csv_columns": csv_columns},
                    metrics={}, downstream={}, session_id=...)
```

**字段名拉齐**: 前端 `rule_text` 改 backend 接受的 `strategy_intent` (对齐 backend Pydantic) · 或 backend 加 alias `Field(alias="rule_text")` 双兼 (推荐后者 · 对前端零改动 · 减 mismatch 阶段时间)。

**backtest body 拉齐**: 前端 `{instruction, uploaded_files}` 是 v3.x 残留 · 改为 `{ruleset, csv_path, label_column?, bad_threshold?}` 对齐 backend v4.0 · 同时前端 ts 类型同改。

### 4.3 llm_judge 迁 A2 路径

**Before** (`agent_riskctrl/llm_judge.py:116-131`):

```python
def _get_client(self) -> Any | None:
    if self._llm is not None:
        return self._llm
    if not self.api_key:
        return None
    try:
        from llm import LLMClient
        self._llm = LLMClient(
            provider=self.provider,
            api_key=self.api_key,
            cache_enabled=self.cache_enabled,
        )
        return self._llm
    except (ImportError, RuntimeError, ValueError, TypeError, OSError):
        return None
```

**After** (per A2 V2 ACK trailer caller 3 deprecation path):

```python
def _get_client(self) -> Any | None:
    if self._llm is not None:
        return self._llm
    if not self.api_key:
        return None
    try:
        from shared.llm_caller import LLMCaller
        self._llm = LLMCaller(
            agent_id="riskctrl",
            endpoint="judge",
            provider=self.provider,
            api_key=self.api_key,
            cache_enabled=self.cache_enabled,
        )
        return self._llm
    except (ImportError, RuntimeError, ValueError, TypeError, OSError):
        return None
```

`judge()` body line 164 `client.simple_chat(...)` 不动 · 因 A2 V2 fix-3 加了 `LLMCaller.simple_chat` adapter · API 一致。

**回归保障**:
- LLMJudge 业务 (3 维 Likert / status 枚举 / 失败降级) 一字不改
- `tests/agent_riskctrl/test_llm_dsl_gen.py` 跑通 · 加一条 caller-binding test 验 `isinstance(judge._llm, LLMCaller)`
- `compute_rule_interpretability(rules)` 公开 API 不变 · adapter 调用方 (evaluation runner) 零改

**`agent_riskctrl/api.py:141` 同迁** (caller 5 第 1 处):

```python
# Before
from llm import LLMClient
llm = LLMClient(provider=req.provider, api_key=req.api_key)
llm_json = llm.chat_json(system_prompt=..., user_content=..., temperature=0.3)

# After
from shared.llm_caller import make_json_caller
caller = make_json_caller(agent_id="riskctrl", endpoint="dsl_gen",
                          provider=req.provider, api_key=req.api_key)
llm_json = caller.chat_json(system=..., user=..., temperature=0.3)
```

### 4.4 export 三件套 endpoint 草

依 audit Cat 13 + worker-A6 export contract 共形 spec (A6 §1 交付 #7):

```
POST /api/riskctrl/export_docx · body: {ruleset_id, format?:"docx"} · 返 application/vnd.openxmlformats-officedocument.wordprocessingml.document
POST /api/riskctrl/export_xlsx · body: {ruleset_id, format?:"xlsx"} · 返 application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
POST /api/riskctrl/export_pdf  · body: {ruleset_id, format?:"pdf"}  · 返 application/pdf
```

**Docx 内容** (回测报告 · 与 RiskOutputPanel `tab=dsl/ks/sample` 三视图对应):
- §一 DSL 规则树 · IF/AND/OR/THEN 4 op · 缩进可视化
- §二 KS 双线 · 10 分位 · 含 TPR/FPR/KS 数据表 (matplotlib png 嵌入)
- §三 样本分布 · pass/review/block 三档 · count/pct/badRate
- §四 规则命中明细 · per-rule FP/TN/hit (取 `result.metrics.rule_stats`)
- 页眉/页脚: "AI 初版策略稿 · 未经风险总监审批不得上线" (与 RiskOutputPanel:1240-1241 page footer 同字)

**Xlsx 内容** (规则明细):
- Sheet 1 `Rules`: ruleId / name / description / conditions JSON / action / priority / hit / fp / tn
- Sheet 2 `KS Points`: bin / TPR / FPR / KS
- Sheet 3 `Samples`: key / label / count / pct / badRate

**Pdf 内容** (送审包): docx + per-rule 命中样本 5 条采样 + 审批人签字栏 (留白)

**失败处理**:
- ruleset_id 不存在 → 404 + `{event:"error", code:"ruleset_not_found"}` payload (即使非 SSE · 错误 body 沿用 envelope schema)
- 渲染异常 → 500 + `{event:"error", code:"render_failed", message, retryable:false}`
- 不静默 200 + empty blob (sse-envelope §3.6)

**Frontend 改动** (`web/src/lib/api/riskctrl.ts:80-110`):
- 删 404 容忍分支 · 后端必 deliver
- 加 `exportXlsx(rulesetId)` + `exportPdf(rulesetId)` 同形函数
- RiskOutputPanel:1185-1194 的 export button 改 dropdown · 三选一

### 4.5 Demo fixture shape (`data/mock/workspace/riskctrl/scenarios/*.json`)

§1 #3 + §5 step 9 引用但未定 schema · 此节固定 · demo endpoint 走 fixture · prod 端点失败时 banner 显错不静默 fallback。

**目录结构**:

```
data/mock/workspace/riskctrl/scenarios/
├── credit_v15.json        ← sess_credit_v15 fixture (绿区 · 简单档)
├── aml_kyc.json           ← sess_aml_kyc fixture (关注区 · 中等档)
└── fraud_high.json        ← sess_fraud_high fixture (红区 · 极端档)
```

**单 fixture json schema** (per scenario · 每条对应一次 demo run · 含 dsl_gen + backtest 双 SSE 完整流):

```json
{
  "scenario_id": "credit_v15",
  "session_id": "sess_credit_v15_demo_001",
  "endpoint": "dsl_gen",
  "stream": [
    { "event": "stage", "data": { "stage": "parse_intent", "pct": 10 } },
    { "event": "stage", "data": { "stage": "build_prompt", "pct": 25 } },
    { "event": "stream", "data": { "delta": "{ \"version\": \"1.0\", " } },
    { "event": "stream", "data": { "delta": "\"rules\": [..." } },
    { "event": "stage", "data": { "stage": "validate_dsl", "pct": 80 } },
    {
      "event": "done",
      "data": {
        "session_id": "sess_credit_v15_demo_001",
        "panels": {
          "ruleset": { "version": "1.0", "rules": [/*...verbatim from sess_credit_v15.ruleset*/] },
          "ruleset_id": "rs_credit_v15_demo",
          "source": "demo",
          "csv_columns": ["loan_id", "applicant_age", "income", "fico", "ltv", "label_default"]
        },
        "metrics": {},
        "downstream": {}
      }
    }
  ]
}
```

**backtest fixture 同形** (`endpoint: "backtest"` · stream 含 load_csv → hit_rules → calc_ks 三 stage · done payload 完整 metrics+ks+samples+rule_stats)。

**字段约束**:
- `scenario_id` 必须与 `agent-riskctrl-sessions.ts` 的 session id 1:1 (前端切下拉时按 id 索引 fixture)
- `source: "demo"` 写死 · 与 prod path `source: "llm"|"mock"` 区分
- stream 数组顺序 = SSE 实际发送顺序 · backend `/api/riskctrl/demo/run` 实装时 `for chunk in fixture.stream: yield chunk; await asyncio.sleep(0.3)` 模拟流速
- 不含 `event: error` (demo 永远 happy path · prod 错误 banner 走真 SSE)

**反模式硬线** (per CLAUDE.md §3.5 反结果导向 5 原则 · 环境边界):
- ❌ fixture 不含 LLM 真实 token 文本 · 不假装 LLM 在算 · `delta` 只放最终 ruleset JSON 的分片
- ❌ fixture 不含 `match_score` / `ks_value` 等 Agent 应自算的"答案字段" — 这里 KS / sample dist 是**已计算结果**因为 demo 不跑 LLM · 不违反原则 (riskctrl 不是检索系 Agent · 没有"自搜"语义)
- ❌ prod endpoint 失败时**禁止** silent fallback 到 fixture (UI banner: "live endpoint 失败 · 请重试或切 demo 模式")

---

## 5. 文件级改动清单 (per-file commit)

按 workspace-state-protocol §7 7 步 migration 顺序 · riskctrl 域投影 · 每步独立 commit + trailer:

| # | 文件 | 动作 | 验证 | trailer signal |
|---|---|---|---|---|
| 1 | `web/src/lib/mock/agent-riskctrl-sessions.ts` (新建) | 复制 `agent-riskctrl-session.ts` 内容 · 包 array · 写 ≥3 session · 难度分层 | tsc 0 error | `WORKER-A4-RISKCTRL-MOCK-ARRAY-DONE` |
| 2 | `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx` 顶层 | 加 4 gate · 删 13 散 useState · 改 sessionData 派生 | 切下拉 panel 全跟切 · tsc 0 error | `WORKER-A4-RISKCTRL-4GATE-DONE` |
| 3 | 5 panel function (Hero/IndicatorRow/Query/Rules/RuleOutput) | 改签名加 sessionData props · 删内层 `const s = RISKCTRL_SESSION` | tsc 0 error · 视觉无回归 | `WORKER-A4-RISKCTRL-PANELS-DONE` |
| 4 | `agent_riskctrl/api.py` SSE 化 + 字段拉齐 | 两端点改 EventSourceResponse · 接 shared/sse_envelope · Pydantic alias 兼容前端 rule_text | curl 看 SSE 流 · 两端点字段 422 消失 | `WORKER-A4-RISKCTRL-API-SSE-DONE` |
| 5 | `agent_riskctrl/llm_judge.py` + `agent_riskctrl/api.py:141` | LLMClient → LLMCaller / make_json_caller (caller 3 + 5 第 1 处) | pytest tests/agent_riskctrl/ 全 PASS · 加 caller-binding test | `WORKER-A4-RISKCTRL-LLM-MIGRATED` |
| 6 | `web/src/lib/api/riskctrl.ts` body 拉齐 | rule_text→strategy_intent · backtest body 改对齐 · 加 exportXlsx/Pdf | tsc 0 error · runDslGen / runBacktest 真 200 | `WORKER-A4-RISKCTRL-CLIENT-DONE` |
| 7 | `agent_riskctrl/exports.py` (新建) + api.py mount 三 endpoint | docx/xlsx/pdf 实装 · 错误走 envelope error event | curl 三 endpoint 返 binary · 失败 404/500 + envelope error | `WORKER-A4-RISKCTRL-EXPORT-DONE` |
| 8 | `web/src/lib/api/riskctrl.ts` SSE 接入 + Workspace `runRealDslGen` 改 done event 注入 liveData | done event 整体 setLiveData (而非散) | live mode panel 全切真数据 | `WORKER-A4-RISKCTRL-LIVE-WIRED` |
| 9 | `agent_riskctrl/demo.py` (新建) + `/api/riskctrl/demo/run` mount | 走 fixture · prod 路径 0 mock fallback | curl demo 端点返 SSE · prod 端点失败时显 banner 非 silent | `WORKER-A4-RISKCTRL-DEMO-DONE` |
| 10 | `web/tests/regression/riskctrl-*.spec.ts` 3 spec | mock-switch / live-dsl-gen / sample-segment-detail-drawer | Playwright 全 PASS | `WORKER-A4-RISKCTRL-PLAYWRIGHT-DONE` |
| 11 | `web/src/lib/mock/agent-riskctrl-session.ts` 旧单 const | 删 · grep 项目无 import 残留 | build 通 · 0 import error | `WORKER-A4-RISKCTRL-MOCK-LEGACY-DROPPED` |
| 12 | DONE commit (无 file change · signal only) | mesh 闭环 | — | `WORKER-A4-RISKCTRL-ADAPTER-DONE` |

---

## 6. PM 拍板 (worker 必须遵守)

1. 杜绝拖死 4 机制 (≤3500 词 onboarding · 单 issue ≤2 round · dissent 反增即 escalate)
2. Phase A/B 严切 (你严守 · 不沾 /today RM workbench · 不沾 Phase B 商业化)
3. **active decision 必回写 root CLAUDE.md** · 你改 `agent_riskctrl/*` + `web/src/lib/api/riskctrl.ts` 必同 commit 更 CLAUDE.md §3 / §10 / §11 对应行
4. 命名 SSOT (`agent-naming-ssot.md`) · 6 agent id 用 `riskctrl` 不再用 `forge` · workspace 文件名 path RBAC 都对齐
5. **§0.5 wait gate 不可跳** · 见本 doc §0.5

### 6.1 Riskctrl 命名遗产清理

A1 SSOT V2 选 `riskctrl` 为单 id · 但代码遗产仍含 `Forge` 字面 (RiskctrlWorkspace `RiskHero` line 528 `AGENT · 02 · FORGE` · `AI · Forge` etc) · 这些**留在 UI** (业务命名 / 用户可见) · 但 backend / API path / RBAC / module path 一律 `riskctrl`。**不要把 UI 文案 Forge 改成 Riskctrl** · 用户认知不变。

### 6.2 共享 hook 抽出 (5 子 worker 之一兼任)

charter §3 worker-A4 第 5 行: "(其中一个子 worker 兼任) 抽出共享 hook · `useWorkspaceRun.ts` + `WorkspaceBanner.tsx` + `EmptyWorkspace.tsx` + `sseWorkspaceClient.ts`"

PM 待拍 · 主 CLI 倾向 **A4-credit 兼任** · 因 credit 是 A6 → A3 决策链下游 · 它做 hook 抽出后 4 个兄弟 worker (channel/alert/compli/riskctrl/report) 直接消费。riskctrl worker **不主动接此活** · 等 PM Q-NNN 拍。如 PM 拍 riskctrl 兼任 · 本 doc §5 加步 3.5 / 5.5 / 8.5 三步 hook 抽出 + 4 兄弟 PR review。

---

## 7. 协作纪律 (red lines · 与 A1/A2/A5/A6/A7 一致)

- ❌ 不跨 worktree 改文件 (主 CLI · A1-A3 + A5-A7 + 4 兄弟 A4 各自 worktree 你不动)
- ❌ commit 不带 `Signal:` trailer
- ❌ 改 `web/` 不带 `PRESERVES: F-XXX` + `NEW-DOM: data-testid="..."` + `SMOKE-PASS: <spec>.spec.ts` trailer (CLAUDE.md §13 inventory 红线)
- ❌ active decision 不回写 CLAUDE.md
- ❌ §0.5 wait gate 解锁前动一行 code (本 doc 红区硬规)
- ❌ 直接 push origin
- ❌ `agent_riskctrl/llm_judge.py` 业务逻辑 (3 维 Likert / failure status / compute_rule_interpretability 接口) 任何变更 · 你只迁 transport 不动语义

---

## 8. ACK 协议 (per A2 onboarding §5 体例)

每 file 完一 commit · trailer `Signal: WORKER-A4-RISKCTRL-<STEP>-DONE` (step 名见 §5 表)。
全完 commit `Signal: WORKER-A4-RISKCTRL-ADAPTER-DONE` · trailer:

```
PHASE: A
WORKER: A4-riskctrl
FILES-CHANGED:
  - agent_riskctrl/api.py (SSE 化 + 字段拉齐)
  - agent_riskctrl/llm_judge.py (caller 3 迁 LLMCaller)
  - agent_riskctrl/exports.py (NEW · docx/xlsx/pdf)
  - agent_riskctrl/demo.py (NEW · /api/riskctrl/demo/run)
  - web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx (4 gate + 5 panel props)
  - web/src/lib/api/riskctrl.ts (SSE 真接 + body 拉齐 + 三件套 export)
  - web/src/lib/mock/agent-riskctrl-sessions.ts (NEW · array)
  - web/src/lib/mock/agent-riskctrl-session.ts (DROPPED)
  - web/tests/regression/riskctrl-mock-switch.spec.ts (NEW)
  - web/tests/regression/riskctrl-live-dsl-gen.spec.ts (NEW)
  - web/tests/regression/riskctrl-sample-segment-detail.spec.ts (NEW)
  - data/mock/workspace/riskctrl/scenarios/*.json (NEW · 3 fixture)
PRESERVES: F-RISKCTRL-* (列保留 inventory feature id · 见 docs/features-inventory.md)
NEW-DOM: data-testid="riskctrl-workspace,riskctrl-trigger-bar,riskctrl-dsl-editor,riskctrl-ks-chart,riskctrl-sample-dist,riskctrl-export-docx-btn,..."
SMOKE-PASS: riskctrl-mock-switch.spec.ts, riskctrl-live-dsl-gen.spec.ts, riskctrl-sample-segment-detail.spec.ts
HARDLINE-4-MET: yes (4 gate impl + result-driven panel + Playwright PASS)
A3-TEMPLATE-MIRRORED: yes (workspace-state-protocol §7 7 步 verbatim · 仅 panel 字段名按 riskctrl 域换)
LLM-CALLER-MIGRATED: 2 处 · llm_judge.py:123 + api.py:141 → shared.llm_caller.LLMCaller / make_json_caller
SSE-ENVELOPE-CONFORMS: yes (sse-envelope.md §1.5 7 event 名 · workspace-state-protocol §4 done payload)
EXPORT-CONTRACT-CONFORMS: yes (worker-A6 export contract 共形 · audit Cat 13 闭)
ACTIVE-DECISIONS-BACK-WRITTEN: <list CLAUDE.md 改了哪几行>
UNRESOLVED-QUESTIONS:
  - <列 PM 待拍事项>

Signal: WORKER-A4-RISKCTRL-ADAPTER-DONE
```

不在 chat 报"已完成" (CLAUDE.md 信号纪律)。

---

## 9. Codex 协作 (anti-bias)

- 主 CLI 已 fire codex pre-dispatch draft 并行 (插入点 1) · 你**不见 codex 草案** (落 `docs/audit/codex-drafts/A4-riskctrl.md`)
- DONE 后主 CLI fire codex post-DONE peer review (插入点 2) · 你不直接辩论 · 等主 CLI cherry-pick verdict
- codex DISAGREE 时主 CLI 回写本 worker 二次任务 · 走 Q-NNN-V2 流程

---

## 10. 不在你范围 (PM 拍板 · 别越界)

- ❌ `/today` RM workbench 重写 (Phase B-3 · 你不动 `web/src/app/today/*`)
- ❌ A6 handoff data contract (worker-A6 干 · 你只消费 `data/mock/handoff/*.json` fixture · 不改 schema)
- ❌ A5 Letterpress 真清 (worker-A5 干 · 你迁 `--t-riskctrl` 时若发现 globals.css legacy 段未删 · 走 decisions-log Q-NNN 报 A5 · 不自己 fix-forward)
- ❌ A7 PRD master + sub (worker-A7 干 · 你 unrelated)
- ❌ 4 兄弟 A4 worker 文件 (credit/alert/compli/report 各自 worktree · 你只读不改)
- ❌ Agent2 业务语义大改 (DSL 树结构 / KS 计算公式 / 3 维 Likert prompt) · 这些是 W-C2-A2 / P3F 8b 旧 onboarding 已固化 · A4 仅 thin adapter · 业务变更走单独 RFC

---

## 11. DONE signal 后主 CLI 后续

DONE → fire codex post-DONE review → AGREE 则 cherry-pick `feat/phase-a4-riskctrl-adapter` → chore/l0-infra → push GitHub → ECS sync (per CLAUDE.md §13.1 · 改 web/ 走完整 build 流程 5-10 min)。

---

## 12. Risks · Unknowns · Open Questions (worker resume 时优先 escalate)

下列项 draft 起草时**主 CLI 尚未拿到答案** · 你 resume + wait gate 解锁后看每条:
- ① 已闭 (条件已满足) → §1-§5 直接执行
- ② 未闭 (待 PM 拍 / 待 codex verdict) → 走 decisions-log Q-NNN 报 PM · 不自决

| # | 风险 / 未知 | 触发条件 | resume 时怎么办 |
|---|---|---|---|
| 1 | A3 codex post-DONE peer review **DISAGREE** · 改了 ChannelWorkspace 4 gate 实装范本 | 解锁后读 codex verdict cherry-pick 后是否含修改 | 若改 · 先重读修订版 ChannelWorkspace · 同步 §4.1 命名 / §4.2 done payload 结构再动手 |
| 2 | A6 worker (handoff data contract) export 三件套 schema 与 §4.4 不一致 | A6 cherry-pick 后看 `docs/contracts/agent-handoff-spec.md` 是否定 export 字段 | 不一致以 A6 spec 为准 · §4.4 草案需重写 · 报 Q-NNN-A4-RISKCTRL-EXPORT-V2 |
| 3 | LLMCaller `stream()` API 在 A2 V2 仅承诺 `simple_chat` / `chat_json` · §4.2 dsl_gen SSE 的 `caller.stream(...)` 调用是否存在 | resume 后读 `shared/llm_caller/__init__.py` + `shared/llm_caller/caller.py` 确认 `.stream()` 方法 | 若不存在 · 退回 `simple_chat()` 拿全文 · 后端模拟分块 yield (体感同 SSE · 不影响前端契约) |
| 4 | 共享 hook 兼任由谁 (§6.2 五子之一) PM 未拍 | resume 后查 decisions-log 是否有 Q-NNN-A4-SHARED-HOOK-OWNER | 若主 CLI 倾向 (A4-credit) 已拍 · riskctrl 不动 hook · 直消费 · 若拍 riskctrl 兼任 · §5 加步 3.5 / 5.5 / 8.5 三步 hook 抽出 |
| 5 | Forge UI 文案保留 (§6.1) 是否在用户演示中引发认知冲突 ("Forge" vs RBAC path "riskctrl") | 客户演示 (北部湾首演 + 6 Agent POC 落地) 已认 Forge 字面 | 不动 UI · 仅 backend / API path / RBAC 用 riskctrl · 演示无变化 (per CLAUDE.md §11 + project_6agent_poc_landed memory) |
| 6 | demo endpoint `/api/riskctrl/demo/run` 与 prod 端点共用 backend handler 还是物理隔离 | charter §3 worker-A4 第 3 行 "单独 mount · 走 fixture · prod 端点不 silent fallback" | **物理隔离** · `agent_riskctrl/demo.py` 新文件 · 不复用 `api.py` 的 `_dsl_gen_stream` · 避免误改污染 prod path |
| 7 | A5 worker (Letterpress 真清) 若 globals.css 的 `--t-riskctrl: 绛紫` token 被误删 | resume 后读 A5 cherry-pick 内容 · grep `--t-riskctrl` | 报 Q-NNN-A5-TOKEN-DROPPED · 不自己 fix-forward (per §10) |
| 8 | `agent_riskctrl/api.py` 现注释 "Stage C v4.0 · onboarding W-C2-A2" 的非 SSE 是**设计决定**还是历史遗留 | 旧 onboarding W-C2-A2 docs/onboarding/ 是否仍存 | 若 W-C2-A2 是 reset 前遗留 · 当前 reset 工程 SSE 化是 supersede · 直改 · 若 W-C2-A2 是当前有效 contract · 报 Q-NNN-A4-SSE-OVERRIDE 等 PM 拍 |
| 9 | `tests/agent_riskctrl/test_llm_dsl_gen.py` 是否存在 + 现 PASS 状态 | resume 后 `ls tests/agent_riskctrl/` + `pytest --collect-only tests/agent_riskctrl/` | 若不存 · §5 步 5 加 caller-binding test 时同步建测试 framework · 若存但 FAIL · 先 fix 再迁 (排除 caller 迁移引入 regression 嫌疑) |
| 10 | 前端 `streamSse` helper 是否已经处理 `event: stream` (LLM partial) · 还是仅认 `event: stage / done / error` | resume 后读 `web/src/lib/api/sse.ts` (或类似 helper · 由 A1 V2 抽出) 实装 | 若不识 stream event · 加 callback `onStreamDelta` · 与 A3 channel 同改 (channel 也用 LLM token 流) · 若已识 · 直接消费 |

**escalate 模板** (用于 ② 未闭项):

```
[Q-NNN-A4-RISKCTRL-<TOPIC>]
触发上下文: <verbatim 第几行 / 哪个 codex verdict / 哪条 decisions-log 缺>
影响范围: <§5 哪几步阻塞 / 是否影响 A3 模板 mirror>
建议方案: <2-3 选项 + ROI>
默认行为 (PM 不拍): <最保守路径 · 通常是"暂不动 + 等下游 worker 推进">
```

写入 `docs/handoff/decisions-log.md` · trailer `Signal: WORKER-A4-RISKCTRL-ESCALATE-Q<N>` · 不发 chat。

---

**Author**: 主 CLI · 2026-04-29
**Phase A Week 4-5 · 与 4 兄弟 A4 worker 并行 · 依赖 A3 channel pilot DONE**
**DRAFT v0.1 · A3 cherry-pick 完成后转正为 docs/onboarding/A4-riskctrl.md**

**Changelog**:
- v0 (2026-04-29 initial · committed db0bb87): §0-§11 全 11 节 · 共 470 行
- v0.1 (2026-04-29 wait-period refine): 加 §4.5 demo fixture shape (10 子项 + json schema) · 加 §12 risks/unknowns 10 项 + escalate 模板 · 总行数 ~600
