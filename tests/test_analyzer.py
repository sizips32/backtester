import pytest
import pandas as pd
import numpy as np
from services.analyzer import calculate_portfolio_returns, calculate_risk_metrics

@pytest.fixture
def sample_hist_data():
    """테스트용 샘플 시계열 데이터를 생성합니다."""
    dates = pd.to_datetime(pd.date_range(start='2023-01-01', periods=100))
    data = {
        'STOCK_A': np.linspace(100, 150, 100) * np.random.normal(1, 0.05, 100),
        'STOCK_B': np.linspace(200, 180, 100) * np.random.normal(1, 0.08, 100)
    }
    return pd.DataFrame(data, index=dates)

@pytest.fixture
def sample_weights():
    """테스트용 샘플 가중치를 반환합니다."""
    return {'STOCK_A': 0.6, 'STOCK_B': 0.4}

def test_calculate_portfolio_returns(sample_hist_data, sample_weights):
    """포트폴리오 수익률 계산 함수를 테스트합니다."""
    portfolio_returns = calculate_portfolio_returns(sample_hist_data, sample_weights)
    
    assert isinstance(portfolio_returns, pd.Series)
    assert not portfolio_returns.isnull().any()
    # 수익률 계산은 pct_change() 때문에 1개 적은 row를 가짐
    assert len(portfolio_returns) == len(sample_hist_data) - 1

def test_calculate_risk_metrics(sample_hist_data, sample_weights):
    """리스크 지표 계산 함수를 테스트합니다."""
    portfolio_returns = calculate_portfolio_returns(sample_hist_data, sample_weights)
    risk_metrics = calculate_risk_metrics(portfolio_returns, risk_free_rate=0.02)
    
    assert isinstance(risk_metrics, dict)
    expected_keys = ["연간 기대 수익률", "연간 변동성", "샤프 비율", "소티노 비율", "최대 낙폭", "총 수익률"]
    for key in expected_keys:
        assert key in risk_metrics
        assert isinstance(risk_metrics[key], (float, np.floating))

    # 샤프 비율이 극단적인 값을 가지지 않는지 확인 (간단한 sanity check)
    assert -10 < risk_metrics["샤프 비율"] < 10
