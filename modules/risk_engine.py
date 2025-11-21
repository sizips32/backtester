"""
리스크 분석 엔진 모듈
VaR, CVaR, Sharpe Ratio 등 리스크 지표 계산 로직 담당
"""
import numpy as np
import pandas as pd
from typing import Optional, Union

class RiskEngine:
    """리스크 분석 엔진"""

    @staticmethod
    def calculate_var(returns: pd.Series, confidence_level: float = 0.95) -> float:
        """
        Value at Risk (VaR) 계산
        
        Args:
            returns: 수익률 시계열
            confidence_level: 신뢰수준 (0.0 ~ 1.0)
            
        Returns:
            VaR 값
        """
        if len(returns) < 2:
            return 0.0
        return np.percentile(returns, (1 - confidence_level) * 100)

    @staticmethod
    def calculate_cvar(returns: pd.Series, confidence_level: float = 0.95) -> float:
        """
        Conditional Value at Risk (CVaR) 계산
        
        Args:
            returns: 수익률 시계열
            confidence_level: 신뢰수준 (0.0 ~ 1.0)
            
        Returns:
            CVaR 값
        """
        if len(returns) < 2:
            return 0.0
        var = RiskEngine.calculate_var(returns, confidence_level)
        tail_returns = returns[returns <= var]
        return tail_returns.mean() if len(tail_returns) > 0 else 0.0

    @staticmethod
    def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """
        Sharpe Ratio 계산
        
        Args:
            returns: 수익률 시계열
            risk_free_rate: 무위험 수익률 (연간)
            
        Returns:
            Sharpe Ratio
        """
        if len(returns) < 2:
            return 0.0
        
        # 연간화
        annual_return = returns.mean() * 252
        annual_vol = returns.std() * np.sqrt(252)
        
        if annual_vol == 0:
            return 0.0
            
        # 초과 수익률 계산 (간소화된 방식: 연간 수익률 - 무위험 수익률)
        # 정확한 방식은 (returns - rf/252).mean() * 252 / (returns.std() * sqrt(252))
        # 여기서는 기존 로직과 유사하게 유지하되, 입력이 일간 수익률임을 가정
        excess_return = annual_return - risk_free_rate
        return excess_return / annual_vol

    @staticmethod
    def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """
        Sortino Ratio 계산
        
        Args:
            returns: 수익률 시계열
            risk_free_rate: 무위험 수익률 (연간)
            
        Returns:
            Sortino Ratio
        """
        if len(returns) < 2:
            return 0.0
            
        annual_return = returns.mean() * 252
        
        # 하방 편차 계산
        excess_daily_returns = returns - (risk_free_rate / 252)
        downside_returns = excess_daily_returns[excess_daily_returns < 0]
        
        if downside_returns.empty:
            return 0.0
            
        sortino_div = downside_returns.std() * np.sqrt(252)
        
        if sortino_div == 0:
            return 0.0
            
        # 분자는 연간 초과 수익률
        annual_excess_return = excess_daily_returns.mean() * 252
        return annual_excess_return / sortino_div

    @staticmethod
    def calculate_max_drawdown(returns: pd.Series) -> float:
        """
        Maximum Drawdown 계산
        
        Args:
            returns: 수익률 시계열
            
        Returns:
            MDD 값
        """
        cum_returns = (1 + returns).cumprod()
        rolling_max = cum_returns.expanding().max()
        drawdowns = cum_returns/rolling_max - 1
        return drawdowns.min()

    @staticmethod
    def calculate_calmar_ratio(returns: pd.Series, max_drawdown: Optional[float] = None) -> float:
        """
        Calmar Ratio 계산
        
        Args:
            returns: 수익률 시계열
            max_drawdown: 미리 계산된 MDD (없으면 계산)
            
        Returns:
            Calmar Ratio
        """
        annual_return = returns.mean() * 252
        if max_drawdown is None:
            max_drawdown = RiskEngine.calculate_max_drawdown(returns)
            
        if max_drawdown == 0:
            return 0.0
            
        return annual_return / abs(max_drawdown)
