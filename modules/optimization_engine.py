"""
포트폴리오 최적화 엔진 모듈
마코위츠, 최소분산, 리스크 패리티 등 최적화 알고리즘 담당
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Tuple, Dict, Any, List

class OptimizationEngine:
    """포트폴리오 최적화 엔진"""

    @staticmethod
    def calculate_portfolio_stats(weights: np.ndarray, returns: pd.DataFrame) -> Tuple[float, float, float]:
        """
        포트폴리오 통계 계산 (수익률, 변동성, 샤프지수)
        
        Args:
            weights: 자산 비중 배열
            returns: 자산별 일간 수익률 DataFrame
            
        Returns:
            (연간 수익률, 연간 변동성, 샤프지수)
        """
        portfolio_return = np.sum(returns.mean() * weights) * 252
        portfolio_vol = np.sqrt(
            np.dot(weights.T, np.dot(returns.cov() * 252, weights))
        )
        sharpe_ratio = portfolio_return / portfolio_vol if portfolio_vol != 0 else 0
        return portfolio_return, portfolio_vol, sharpe_ratio

    @staticmethod
    def optimize_minimum_variance(returns: pd.DataFrame) -> np.ndarray:
        """
        최소 분산 포트폴리오 최적화
        
        Args:
            returns: 자산별 일간 수익률 DataFrame
            
        Returns:
            최적 비중 배열
        """
        n_assets = returns.shape[1]
        
        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
        
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        result = minimize(
            portfolio_volatility,
            np.array([1/n_assets] * n_assets),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        return result.x

    @staticmethod
    def optimize_risk_parity(returns: pd.DataFrame) -> np.ndarray:
        """
        리스크 패리티 최적화
        
        Args:
            returns: 자산별 일간 수익률 DataFrame
            
        Returns:
            최적 비중 배열
        """
        n_assets = returns.shape[1]
        cov_matrix = returns.cov().values * 252
        
        def risk_parity_objective(weights):
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            if portfolio_vol == 0:
                return 0
            risk_contributions = weights * (np.dot(cov_matrix, weights)) / portfolio_vol
            target_risk = portfolio_vol / n_assets
            return np.sum((risk_contributions - target_risk) ** 2)
        
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
            {'type': 'ineq', 'fun': lambda x: x}
        ]
        bounds = tuple((0.01, 1) for _ in range(n_assets))
        
        result = minimize(
            risk_parity_objective,
            np.array([1/n_assets] * n_assets),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        return result.x

    @staticmethod
    def optimize_markowitz(returns: pd.DataFrame) -> np.ndarray:
        """
        마코위츠 최적화 (최대 샤프지수)
        
        Args:
            returns: 자산별 일간 수익률 DataFrame
            
        Returns:
            최적 비중 배열
        """
        n_assets = returns.shape[1]
        
        def neg_sharpe_ratio(weights):
            port_return = np.sum(returns.mean() * weights) * 252
            port_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
            return -port_return / port_vol if port_vol != 0 else 0
        
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        result = minimize(
            neg_sharpe_ratio,
            np.array([1/n_assets] * n_assets),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        return result.x

    @staticmethod
    def optimize_portfolio(returns: pd.DataFrame, method: str = 'markowitz') -> np.ndarray:
        """
        통합 최적화 메서드
        
        Args:
            returns: 자산별 일간 수익률 DataFrame
            method: 최적화 방법 ('markowitz', 'minimum_variance', 'risk_parity', 'equal_weight')
            
        Returns:
            최적 비중 배열
        """
        n_assets = returns.shape[1]
        
        optimization_methods = {
            'equal_weight': lambda: np.array([1/n_assets] * n_assets),
            'minimum_variance': lambda: OptimizationEngine.optimize_minimum_variance(returns),
            'risk_parity': lambda: OptimizationEngine.optimize_risk_parity(returns),
            'markowitz': lambda: OptimizationEngine.optimize_markowitz(returns)
        }
        
        if method not in optimization_methods:
            raise ValueError(f"지원하지 않는 최적화 방법: {method}")
            
        return optimization_methods[method]()
