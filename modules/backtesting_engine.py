"""
백테스팅 엔진 모듈
포트폴리오 가치 계산 및 성과 지표 산출 로직을 담당
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from modules.risk_engine import RiskEngine

class BacktestingEngine:
    """백테스팅 계산 엔진"""

    @staticmethod
    def calculate_portfolio_value(data: pd.DataFrame, weights: Dict[str, float]) -> pd.Series:
        """
        벡터화된 포트폴리오 가치 계산
        
        Args:
            data: 종목별 가격 데이터 (DataFrame)
            weights: 종목별 가중치 (Dict)
            
        Returns:
            포트폴리오 가치 시계열 (Series)
        """
        # NA 값을 먼저 처리한 후 수익률 계산
        data_filled = data.ffill()
        returns = data_filled.pct_change()
        
        # 열 정렬 및 누락 자산은 0 가중치로 안전 처리
        weights_series = pd.Series(weights).reindex(returns.columns, fill_value=0)
        
        # 가중 수익률 계산
        weighted_returns = (returns * weights_series).sum(axis=1)
        
        # 누적 수익률로 가치 계산 (초기값 1)
        return (1 + weighted_returns).cumprod()

    @staticmethod
    def calculate_metrics(returns: pd.Series) -> Dict[str, float]:
        """
        포트폴리오 성과 및 리스크 지표 계산
        
        Args:
            returns: 포트폴리오 수익률 시계열 (Series)
            
        Returns:
            성과 지표 딕셔너리
        """
        # 기본 수익률 지표
        annual_return = returns.mean() * 252
        annual_vol = returns.std() * np.sqrt(252)
        
        # RiskEngine을 사용하여 리스크 지표 계산
        sharpe_ratio = RiskEngine.calculate_sharpe_ratio(returns)
        max_drawdown = RiskEngine.calculate_max_drawdown(returns)
        sortino_ratio = RiskEngine.calculate_sortino_ratio(returns)
        calmar_ratio = RiskEngine.calculate_calmar_ratio(returns, max_drawdown)
        var_95 = RiskEngine.calculate_var(returns, 0.95)
        cvar_95 = RiskEngine.calculate_cvar(returns, 0.95)
        
        # 월별 평균 수익률 및 표준편차
        try:
            monthly_return = returns.groupby(pd.Grouper(freq='ME')).apply(
                lambda x: (1 + x).prod() - 1
            )
        except Exception:
            # pandas 버전에 따라 freq='M' 사용
            monthly_return = returns.groupby(pd.Grouper(freq='M')).apply(
                lambda x: (1 + x).prod() - 1
            )

        if monthly_return.empty:
            avg_monthly_return = np.nan
            monthly_vol = np.nan
            positive_months = np.nan
        else:
            avg_monthly_return = monthly_return.mean()
            monthly_vol = monthly_return.std()
            positive_months = (monthly_return > 0).sum() / len(monthly_return)
        
        return {
            "연간 수익률": annual_return,
            "연간 변동성": annual_vol,
            "Sharpe Ratio": sharpe_ratio,
            "Maximum Drawdown": max_drawdown,
            "Sortino Ratio": sortino_ratio,
            "Calmar Ratio": calmar_ratio,
            "VaR (95%)": var_95,
            "CVaR (95%)": cvar_95,
            "월 평균 수익률": avg_monthly_return,
            "월간 변동성": monthly_vol,
            "양의 수익 개월 비율": positive_months
        }
