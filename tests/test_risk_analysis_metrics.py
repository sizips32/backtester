import pandas as pd

from risk_analysis import calculate_sortino_ratio


def test_calculate_sortino_ratio_positive_when_downside_exists():
    returns = pd.Series([0.01, -0.02, 0.015, 0.005, -0.01])

    ratio = calculate_sortino_ratio(returns, risk_free_rate=0.0)

    assert ratio > 0


def test_calculate_sortino_ratio_zero_without_downside():
    returns = pd.Series([0.01, 0.02, 0.015, 0.005])

    ratio = calculate_sortino_ratio(returns, risk_free_rate=0.0)

    assert ratio == 0
