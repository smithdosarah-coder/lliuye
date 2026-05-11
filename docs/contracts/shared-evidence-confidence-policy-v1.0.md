# shared.evidence.confidence_policy · v1.0 (B.3.4 P0-R1 · 2026-05-11)

> **Source**: B.3.4 P0-R1 shared-extract worker · inventory verdict — alert BE5 已升 freshness × source · 其他 5 Agent 静态 confidence (0.5/0.75/0.9/0.95/1.0)
> **Owner**: shared-extract worker (`feat/b34-shared-extract`)
> **Tier**: 1 · per CLAUDE.md §15 instruction SSOT
> **Backing**: 抽 `agent_alert/signal_quality.py` 的纯数学部分到 shared/ · alert-domain taxonomy 留 alert local
> **Related**: CLAUDE.md §3.7 active rule "证据时效 SLA" + `shared/evidence_freshness.py` (已存在 SLA 表)

---

## 0. Why this exists

inventory 实测 (`grep -rn "confidence=" agent_*/evidence_pipeline.py`):

| Agent | confidence 算法 |
|---|---|
| **alert** | ✅ BE5 升级 · `quality_bundle()` · `freshness × source_confidence` 综合 |
| **channel** | ❌ 静态 · `1.0` / `0.9` / `0.8 if url else 0.5` / `0.95` |
| **compliance** | ❌ 静态 · `1.0` / `0.9` / `0.92` / `0.88` |
| **credit** | ❌ 静态 · `1.0` / `0.95` / `0.8` |
| **report** | ❌ 静态 · `1.0` / `0.9` / `0.95` |
| **riskctrl** | ❌ 静态 · `1.0` / `0.9` |

**痛点 1**: alert BE5 是真的 (有 `signal_quality.py` 完整一套 · 确定性 · 数据非代码) · 其他 5 Agent 是 magic number · **PM 2026-05-06 拍板第 6 原则 "数据时效 + 业务质量双轨验证"** (CLAUDE.md §3.5.1) 适用 6 Agent · 但只有 alert 真落地。

**痛点 2**: 5 Agent 自己各自 hardcode magic number · 一致性零 · 客户经理看 score 没法横向比较 (Agent4 的 0.95 vs Agent3 的 0.95 是不是同一回事)。

**痛点 3**: alert 的 `signal_quality.py` 也没把纯数学部分 (freshness 衰减 / confidence 合并公式) 与 alert-specific taxonomy (LAW/FIN/BIZ rule prefix · alert source_confidence.json 路径) 分开。其他 Agent 想 reuse 也不知道哪些能 reuse。

**抽离思路** (per R7 verdict — shared invariants + local adapters):
- 抽**纯数学**到 `shared/evidence/confidence_policy.py` · `freshness_score` + `compute_evidence_confidence` + 基础常量 (decay rate / floor / base confidence levels)
- 留**alert-specific taxonomy** 在 `agent_alert/signal_quality.py` (signal_kind classifier / evidence origin classifier / source_confidence table loader)
- 5 Agent 走 **flag-gate 渐进 opt-in** (per CLAUDE.md §3.7.7 禁 big-bang) · 默认 OFF · 各 Agent 自己 PR 开 flag

---

## 1. Public API

### 1.1 Module paths

```
shared/evidence/confidence_policy.py     # new · 纯数学 + 常量 + 公共 quality_bundle 接口
agent_alert/signal_quality.py            # 保留 · alert-specific taxonomy · 内部改用 shared.evidence.confidence_policy 的常量与函数
```

### 1.2 Pure math primitives (shared)

```python
# shared/evidence/confidence_policy.py
from typing import Any, Literal

SourceConfidence = Literal["high", "med", "low"]

# 公共常量 (跨 Agent invariant)
FRESHNESS_DECAY_PER_DAY: int = 10           # -10/day
FRESHNESS_MAX: int = 100                    # 当天 = 100
FRESHNESS_MIN: int = 0                      # ≥ 10 天前 = 0
DEFAULT_CONFIDENCE_LEVEL: SourceConfidence = "med"
DEFAULT_FLOOR: float = 0.10                  # 最低 confidence
CONFIDENCE_BASE: dict[str, float] = {
    "high": 0.95,
    "med": 0.70,
    "low": 0.45,
}

def freshness_score(observed_at: Any, ref: Any = None) -> int:
    """日衰减 freshness · 0-100 · 当天=100 · -10/day · clamp [0, 100]。

    Args:
        observed_at: 信号时间 (date / datetime / ISO str / epoch / None) · 不可解析返 0
        ref:         参考"今天" · 默认 datetime.now().date()
    """

def compute_evidence_confidence(
    freshness: int,
    source_confidence: SourceConfidence | str,
    *,
    floor: float = DEFAULT_FLOOR,
) -> float:
    """合并 freshness × source_confidence → [floor, 1.0] confidence。

    公式: base[level] × (0.5 + freshness/200) · clamp [floor, 1.0]
    - high + freshness 100 → 0.95
    - med  + freshness 50  → 0.525
    - low  + freshness 0   → 0.225 → max(floor=0.10, 0.225) = 0.225
    """

def quality_bundle(
    *,
    observed_at: Any = None,
    source_confidence_level: SourceConfidence | str = "med",
    ref_date: Any = None,
) -> dict[str, Any]:
    """一站算 freshness + confidence (纯数学版 · 不带 alert taxonomy)。

    返回:
        {
          "freshness_score": int 0-100,
          "source_confidence": "high" | "med" | "low",
          "confidence": float 0-1,
        }

    注: 不算 signal_kind (alert taxonomy · 留 agent_alert/signal_quality.py)
        不算 source_confidence lookup (各 Agent 表路径不同 · adapter 自己查表后传 level)
    """
```

### 1.3 Alert-specific 留 local

```python
# agent_alert/signal_quality.py (保留 · 内部改用 shared)
from shared.evidence.confidence_policy import (
    freshness_score,                 # alias re-export · 不破现有 import
    compute_evidence_confidence,
    CONFIDENCE_BASE,
    SourceConfidence,
)

# alert-specific 留这里
SIGNAL_KIND_LEGAL = "legal_signal"
SIGNAL_KIND_FINANCIAL = "financial_signal"
# ... LAW/FIN/BIZ/IND/REL/POL prefix taxonomy

def lookup_source_confidence(source_type: str = "", ...) -> SourceConfidence:
    """读 data/mock/workspace/alert/source_confidence.json (alert-specific 表)"""

def classify_signal_kind(rule_id: str, route: str | None = None) -> str:
    """LAW-/FIN-/BIZ- prefix → kind · alert taxonomy"""

def quality_bundle(...):
    """alert 自己版 · 调 shared.confidence_policy.quality_bundle() + alert classifier"""
```

---

## 2. Invariants (跨 Agent 行为不变 · alert 已 ship 不变)

| # | Invariant | 由谁保障 |
|---|---|---|
| I1 | `freshness_score(today) == 100` | 公式: `100 - 10×0` |
| I2 | `freshness_score(10_days_ago) == 0` | 公式: clamp at FRESHNESS_MIN |
| I3 | `freshness_score(future_date) == 100` (clock skew clamp) | `delta_days <= 0` 分支 |
| I4 | `freshness_score(unparseable_or_none) == 0` | `_coerce_to_date` 返 None → MIN |
| I5 | `compute_evidence_confidence(100, "high") == 0.95` (源高 + 当天 = 满分) | base × 1.0 |
| I6 | `compute_evidence_confidence(0, "low") == 0.225` (源低 + 旧 = 兜底之上 floor) | base × 0.5 |
| I7 | `compute_evidence_confidence(*, floor=0.5)` 永远 ≥ 0.5 (floor 生效) | `max(floor, raw)` |
| I8 | alert `quality_bundle()` 行为不变 (已 ship · BE5 sprint 验过) | shim/adapter 内部改但接口不变 |
| I9 | alert `signal_quality.freshness_score` import path 不破 | re-export from shared |
| I10 | 其他 5 Agent 在 flag OFF 状态下 confidence 行为完全不变 (静态值原样保留) | flag-gate 默认 false |

---

## 3. Flag-gate · 5 Agent opt-in (per CLAUDE.md §3.7.7)

```python
# 单 Agent opt-in 例 (channel)
import os
from shared.evidence.confidence_policy import quality_bundle as shared_qb

USE_SHARED_CONFIDENCE = os.getenv("LIUYE_AGENT_CHANNEL_SHARED_CONFIDENCE", "false").lower() == "true"

# evidence_pipeline 内
if USE_SHARED_CONFIDENCE:
    qb = shared_qb(observed_at=hit.published_at, source_confidence_level="high")
    confidence = qb["confidence"]
else:
    confidence = 1.0  # 旧 magic number · 默认行为
```

**Phase 2 灰度策略** (本 worker 只做到 canary 1 Agent):
- 候选 canary: `agent_channel` (低风险 · candidate metadata 路径已稳定 · 易 verify regression)
- canary 跑通后 · **不在本 worker scope 内推 6 Agent 全开** · 留给 PM 拍板下一 sprint
- alert 不动 (它已经在用 shared backing · 行为不变)

---

## 4. Out of scope

- ❌ 6 Agent 全切 confidence policy (本 worker 只 canary 1 个)
- ❌ alert `signal_quality.py` 删除 (内部 re-export 是必需的兼容层)
- ❌ alert `source_confidence.json` 表迁到 shared (各 Agent 可能有自己的源池 · 留 local 表)
- ❌ `evidence_freshness.py` (`shared/evidence_freshness.py` 已存在 · 是 SLA 表 · 不在本 spec scope · 但 future 可考虑合并)
- ❌ Agent6 / Agent3 confidence policy 的 BE5-style 升级 (跨 sprint)

---

## 5. Test contract (Phase 1 必 pass)

```python
# tests/shared/test_evidence_confidence_policy_contract.py
def test_freshness_today_is_100(): ...                # I1
def test_freshness_10_days_ago_is_0(): ...            # I2
def test_freshness_future_clamps_to_100(): ...        # I3
def test_freshness_unparseable_returns_0(): ...       # I4
def test_compute_high_today_is_max(): ...             # I5
def test_compute_low_old_floor_kicks_in(): ...        # I6
def test_compute_floor_clamp(): ...                   # I7
def test_quality_bundle_pure_no_alert_taxonomy(): ... # signal_kind 不在 returned dict
def test_alert_signal_quality_re_export_preserves_api(): ...  # I8 + I9 · alert behavior 0 change
def test_canary_flag_off_is_static(): ...             # I10 · flag OFF · 行为=旧静态
def test_canary_flag_on_uses_shared(): ...            # flag ON · 行为=shared math
```

---

## 6. Risk register

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| alert `quality_bundle` 行为微变 (浮点 round 差异) | 低 | 中 | I8 钉死接口 + 单独 alert regression test (调老逻辑 vs 新逻辑 100 input random verify) |
| canary Agent 行为变 (评分变 · 客户看到 score 变) | 中 | 中 | flag-gate 默认 OFF · 显式 env var 才开 · canary 单 Agent 验后再扩 |
| shared `quality_bundle` API 与 alert `quality_bundle` 名字冲突 | 中 | 低 | shared 版只算 freshness+confidence (无 signal_kind) · alert 版加 taxonomy · 两层 API 不同签名 |
| 6 Agent confidence 横向不可比 (旧静态 vs 新 shared math) | 已存在 | 中 | 本 spec 不解 · 留下 sprint 推 6 Agent 全切时 · 一次性可比 |

---

## 7. Backward-compat checklist

- [x] alert `from agent_alert.signal_quality import freshness_score` 不破 (re-export)
- [x] alert `quality_bundle({...alert kwargs})` 不破 (signature 不变)
- [x] 5 Agent 默认 flag OFF · confidence 静态值原样
- [x] `shared/evidence_freshness.FRESHNESS_SLA_DAYS` 不动 (SLA 表 · 与本 spec 正交)

---

## 8. Signal / commit trailer

- contract spec: `STEP-2-CONTRACT-DONE`
- shared 落地 (Phase 1): `STEP-3-RED` → `STEP-4-GREEN`
- alert re-export 切 (Phase 2a): `STEP-5-ALERT-RE-EXPORT`
- canary 1 Agent (Phase 2b): `STEP-5-CHANNEL-CANARY-OPT-IN`
- 全 done: `WORKER-SHARED-EXTRACT-READY-FOR-MERGE`

trailer 同 output_validator spec §8。
