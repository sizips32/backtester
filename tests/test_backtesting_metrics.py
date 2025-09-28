import numpy as np
import pandas as pd

import backtesting


def test_calculate_metrics_handles_single_datapoint():
    dates = pd.to_datetime(["2024-01-02"])
    returns = pd.Series([0.01], index=dates)

    metrics = backtesting.calculate_metrics(returns)

    assert np.isnan(metrics["양의 수익 개월 비율"])
    assert np.isnan(metrics["월 평균 수익률"])
    assert np.isnan(metrics["월간 변동성"])
