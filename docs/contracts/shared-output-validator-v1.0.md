# shared.output_validator · v1.0 (B.3.4 P0-R1 · 2026-05-11)

> **Source**: B.3.4 P0-R1 shared-extract worker · inventory verdict — 5 文件 95% 重复 · 264 LOC → ~90 LOC
> **Owner**: shared-extract worker (`feat/b34-shared-extract`)
> **Tier**: 1 · per CLAUDE.md §15 instruction SSOT
> **Distinct from**: `agent_report/quality_blocker.py` (Agent6 5 维 QC · 留 local)
> **Backing**: 复用既有 `shared/qc/placeholder_guard.py` (本 spec 是 5 Agent factory wrapper · 不动 placeholder_guard)

---

## 0. Why this exists

5 个 Agent (alert / channel / compliance / credit / riskctrl) 各自有 `output_validator.py` · 51-55 行 · `diff` 实测**唯一差异 = `AGENT="agent_xxx"` 常量 + docstring**。函数体逐字相同 · 都 import `shared.qc` 4 个函数 · 包了一层 thin wrapper 把 `agent` 参数硬编进去。

**痛点**: 1 处 bug 改 5 处 (KT 2026-05-10 retro 真根因 #2 · "6 助手同构重复") · 每次 placeholder_guard 接口微调 · 5 Agent 都得手改。

**抽离收益**:
- 264 LOC → 60 LOC shared + 5 × 5 LOC adapter (~85 LOC) · **省 ~180 LOC**
- 1 处 bug 改 5 处 → 1 处改完 5 Agent 自动同步
- 不动业务行为 · 不动 `shared.qc` 底层 · 风险低

---

## 1. Public API

### 1.1 Module path

```
shared/output_validator.py        # new · 单文件足够 (factory + 3 函数 ~60 LOC)
```

### 1.2 Factory

```python
from shared.output_validator import make_output_validator

# 5 Agent 各自调用 · agent_id 是 "agent_alert" / "agent_channel" / "agent_compliance" / "agent_credit" / "agent_riskctrl"
validator = make_output_validator(agent_id: str) -> OutputValidator
```

### 1.3 OutputValidator interface

```python
class OutputValidator:
    """Per-agent thin wrapper · 行为完全等价于现有 5 个 output_validator.py。"""

    agent_id: str

    def validate_text(self, text: str) -> None:
        """硬阻断: 命中即抛 PlaceholderViolation (per shared.qc.placeholder_guard)。"""

    def soft_clean(self, payload: Any) -> tuple[Any, list[str]]:
        """递归把字符串字段里的占位符替换为标记 · 返回 (cleaned, hit_kinds)。"""

    def assert_clean(self, text: str) -> None:
        """alias of validate_text · 兼容现有 import 习惯。"""
```

### 1.4 Backward-compat shim (per Agent · 5 LOC)

```python
# agent_alert/output_validator.py (改写 · 从 55 LOC 缩到 ~10 LOC)
"""agent_alert · 输出 QC 闸门 (shared.output_validator factory wrapper · B.3.4 P0-R1)"""
from shared.output_validator import make_output_validator
from shared.qc import PlaceholderViolation  # 保留 re-export · production 有 import 它的代码

_validator = make_output_validator("agent_alert")

AGENT = _validator.agent_id
validate_text = _validator.validate_text
soft_clean = _validator.soft_clean
assert_clean = _validator.assert_clean

__all__ = ["AGENT", "validate_text", "soft_clean", "assert_clean", "PlaceholderViolation"]
```

**关键**: 公共 symbols (`AGENT` / `validate_text` / `soft_clean` / `assert_clean` / `PlaceholderViolation`) 保留 · `from agent_alert.output_validator import validate_text` 这种现有 import 不破。

---

## 2. Invariants (跨 5 Agent 行为不变)

| # | Invariant | 由谁保障 |
|---|---|---|
| I1 | `validate_text("")` 不抛异常 (空字符串视为 clean) | shared.qc.assert_clean (现行行为) |
| I2 | `validate_text(text_with_placeholder)` 抛 `PlaceholderViolation` · `agent` 字段 = adapter 传入的 agent_id | factory closure |
| I3 | `soft_clean(dict|list|str)` 递归扫 · 命中替换为 `UNFILLED_MARKER` · 返回 `(cleaned, hit_kinds)` | shared.qc.scan + mark_unfilled |
| I4 | `soft_clean(non_str_non_container)` 原样返回 (int / float / None / bool 不变) | walk() 末分支 |
| I5 | `hit_kinds` 顺序 = 递归遍历顺序 · 同 kind 重复出现重复入列 (不去重) | 现行 walk() 行为 |
| I6 | 5 Agent 之外的调用方 (eval / replay / production) `from agent_alert.output_validator import validate_text` 不破 | adapter shim re-export |

---

## 3. Migration path (5 Agent 切过去)

per CLAUDE.md §3.7.7 (no big-bang) 渐进式落地:

### Phase 1 · shared/ 落地 (0.5 天)
- 写 `tests/shared/test_output_validator_contract.py` (8 测试覆盖 I1-I6 + factory) · CI red
- 实现 `shared/output_validator.py` · CI green
- **不切 5 Agent · 旧 5 个文件不动 · 行为不变**

### Phase 2 · 5 Agent 切 import (1 commit per Agent · 0.5 天)
- 顺序: `agent_alert` → `agent_channel` → `agent_compliance` → `agent_riskctrl` → `agent_credit`
- 每 Agent 改完跑 `pytest agent_xxx/tests/` · 0 regression 才进下一个
- 每 commit 独立 (可 revert)

### Phase 3 · cleanup (合 PR 时)
- 5 个 thin shim 是否要删 · 留 PM 拍板 (我推留 · production import path 不破)

---

## 4. Out of scope

- ❌ **agent_report/quality_blocker.py 不在 scope** · 5 维 QC 与本 placeholder validator 语义不同 · 留 Agent6 local
- ❌ **shared.qc.placeholder_guard 内部不改** · 本 spec 是上层 wrapper · 底层 invariants 不动
- ❌ **不删 5 Agent thin shim** · production 调用 path 保留 (如 PM 后续要删 · 单独 RFC)

---

## 5. Test contract (Phase 1 必须 pass)

```python
# tests/shared/test_output_validator_contract.py
def test_factory_returns_validator_with_agent_id(): ...   # I2
def test_validate_text_empty_string_is_clean(): ...        # I1
def test_validate_text_placeholder_raises(): ...           # I2
def test_soft_clean_dict_recursive(): ...                  # I3
def test_soft_clean_preserves_non_str(): ...               # I4
def test_soft_clean_hit_kinds_order(): ...                 # I5
def test_5_agent_shim_imports(): ...                       # I6 · import 5 个 thin shim 验 symbols 在
def test_behavior_equivalence_with_old_impl(): ...         # 关键 · 5 Agent 旧实现 vs 新 factory · 输入相同 → 输出相同
```

---

## 6. Risk register

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| `from agent_xxx.output_validator import X` production 调用挂 | 低 | 高 | thin shim 保留所有 public symbols + grep 验所有 import path |
| `PlaceholderViolation.agent` 字段语义变 | 极低 | 中 | I2 钉死 `agent` 字段值 = factory 传入的 agent_id (不变) |
| 5 Agent 行为出现差异 (如有 hidden 改动我没看到) | 中 | 高 | Phase 2 每 Agent commit 独立 · 跑 agent-specific test · regression 立刻 revert |
| circular import (shared/ → agent_xxx/ → shared/) | 低 | 中 | shared/output_validator.py 只 import shared.qc · 不 import agent_*/anything |

---

## 7. Backward-compat checklist

- [x] 5 Agent thin shim 保留 `AGENT` 常量
- [x] 保留 `PlaceholderViolation` re-export (Q-040 风格 · 不破 import)
- [x] 保留 `validate_text / soft_clean / assert_clean` 三函数 module-level
- [x] 保留 `__all__` 列表 (eval / replay 可能依赖)

---

## 8. Signal / commit trailer

- shared 落地 (Phase 1): `STEP-3-RED` (test) → `STEP-4-GREEN` (impl)
- 5 Agent 切 (Phase 2): `STEP-5-AGENT-<name>-MIGRATED`
- 全 done: `WORKER-SHARED-EXTRACT-READY-FOR-MERGE`

每 commit 必带:
```
KT-2026-05-10-COMPLIANT: yes
R1-R6-CHECKED: R1 (抽真重复 · 不强抽已 shared) + R2 (TDD red 先) + R6 (反同构重复)
TEST-COMMITTED-FIRST: yes
REVERSE-RATIO: <实测>
Worker: shared-extract
Refs: B.3.4-KT-R7
```
