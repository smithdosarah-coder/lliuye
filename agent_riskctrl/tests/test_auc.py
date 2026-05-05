# -*- coding: utf-8 -*-
"""tests/agent_riskctrl/test_auc.py — V2 fix (codex critical 1) · AUC 实装 verify.

deterministic numpy AUC vs sklearn roc_auc_score 等价 (rank-based Mann-Whitney U).
不需 sklearn 装 · 用 closed-form AUC 公式手算验证.
"""
from __future__ import annotations

import pytest

from agent_riskctrl.metrics import calculate_auc


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdge:
    def test_empty_returns_zero(self):
        assert calculate_auc([], []) == 0.0

    def test_length_mismatch_returns_zero(self):
        assert calculate_auc([1, 0], [0.5]) == 0.0

    def test_all_positive_returns_zero(self):
        # n_neg = 0 → 0.0
        assert calculate_auc([1, 1, 1], [0.1, 0.5, 0.9]) == 0.0

    def test_all_negative_returns_zero(self):
        assert calculate_auc([0, 0, 0], [0.1, 0.5, 0.9]) == 0.0


# ===========================================================================
# 已知 closed-form AUC 验证
# ===========================================================================


class TestClosedForm:
    def test_perfect_separator(self):
        # All positives have higher score than negatives → AUC=1.0
        y_true = [0, 0, 0, 1, 1, 1]
        y_pred = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
        assert calculate_auc(y_true, y_pred) == 1.0

    def test_inverse_separator(self):
        # All positives have lower score → AUC=0.0
        y_true = [0, 0, 0, 1, 1, 1]
        y_pred = [0.9, 0.8, 0.7, 0.3, 0.2, 0.1]
        assert calculate_auc(y_true, y_pred) == 0.0

    def test_random_half(self):
        # Equal mix · perfect random ranking → AUC ≈ 0.5
        # 4 pos + 4 neg · pos ranks {2, 4, 6, 8} = 20 · n_pos*(n_pos+1)/2 = 10
        # AUC = (20-10) / (4*4) = 10/16 = 0.625 (not 0.5 due to interleave)
        # 真随机 · pos at all even positions → AUC=0.625
        y_true = [0, 1, 0, 1, 0, 1, 0, 1]
        y_pred = [1, 2, 3, 4, 5, 6, 7, 8]
        # ranks of pos = positions [2,4,6,8] · sum=20
        # AUC = (20 - 10) / (4*4) = 0.625
        assert calculate_auc(y_true, y_pred) == 0.625

    def test_ties_handled_average_rank(self):
        # 全 tie · pos vs neg average rank 一致 → AUC=0.5
        y_true = [0, 0, 1, 1]
        y_pred = [0.5, 0.5, 0.5, 0.5]
        assert calculate_auc(y_true, y_pred) == 0.5


# ===========================================================================
# AUC vs KS 关系 (KS-AUC 不等式)
# ===========================================================================


def test_auc_in_valid_range():
    """AUC 一定 ∈ [0, 1]."""
    import random
    random.seed(42)
    y_true = [random.choice([0, 1]) for _ in range(100)]
    y_pred = [random.random() for _ in range(100)]
    auc = calculate_auc(y_true, y_pred)
    assert 0.0 <= auc <= 1.0


def test_auc_symmetric():
    """flip y_pred · AUC = 1 - 原 AUC."""
    y_true = [0, 0, 1, 1]
    y_pred = [0.1, 0.4, 0.6, 0.9]
    auc1 = calculate_auc(y_true, y_pred)
    # flip: 反向 score
    y_pred_flip = [-x for x in y_pred]
    auc2 = calculate_auc(y_true, y_pred_flip)
    assert auc1 + auc2 == pytest.approx(1.0, abs=1e-9)


def test_auc_better_than_random_for_real_signal():
    """有真信号时 AUC > 0.5 · BE6 业务指标双轨实测预期."""
    # 80 良 + 20 坏 · 坏的预测分稍高
    y_true = [0] * 80 + [1] * 20
    y_pred = [0.3] * 80 + [0.7] * 20
    assert calculate_auc(y_true, y_pred) > 0.9


# ===========================================================================
# Sanity: round to 4 decimals
# ===========================================================================


def test_auc_rounded_to_4_decimals():
    y_true = [0, 1] * 100
    y_pred = [(i / 200.0) for i in range(200)]
    auc = calculate_auc(y_true, y_pred)
    # 4 位小数后无更多
    assert len(str(auc).split(".")[-1]) <= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
