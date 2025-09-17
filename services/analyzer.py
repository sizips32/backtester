import numpy as np

def calculate_portfolio_returns(hist_data, weights):
    """포트폴리오의 일일 수익률을 계산합니다."""
    # 일일 수익률 계산
    daily_returns = hist_data.pct_change().dropna()
    
    # 포트폴리오 수익률 계산
    portfolio_returns = (daily_returns * weights).sum(axis=1)
    
    return portfolio_returns

def calculate_risk_metrics(portfolio_returns, risk_free_rate=0.0):
    """포트폴리오의 위험 지표를 계산합니다."""
    # 연간화 상수
    annualization_factor = 252  # 거래일 기준
    
    # 연간 평균 수익률
    annual_return = portfolio_returns.mean() * annualization_factor
    
    # 연간 표준편차 (변동성)
    annual_volatility = portfolio_returns.std() * np.sqrt(annualization_factor)
    
    # 샤프 비율
    sharpe_ratio = (
        (annual_return - risk_free_rate) / annual_volatility 
        if annual_volatility > 0 else 0
    )
    
    # 최대 낙폭 (MDD)
    cumulative_returns = (1 + portfolio_returns).cumprod()
    rolling_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    # 누적 수익률
    total_return = cumulative_returns.iloc[-1] - 1
    
    # 소티노 비율 (하방 위험 고려)
    downside_returns = portfolio_returns[portfolio_returns < 0]
    downside_deviation = downside_returns.std() * np.sqrt(annualization_factor)
    sortino_ratio = (
        (annual_return - risk_free_rate) / downside_deviation 
        if downside_deviation > 0 else 0
    )
    
    return {
        "연간 기대 수익률": annual_return * 100,
        "연간 변동성": annual_volatility * 100,
        "샤프 비율": sharpe_ratio,
        "소티노 비율": sortino_ratio,
        "최대 낙폭": max_drawdown * 100,
        "총 수익률": total_return * 100
    }
