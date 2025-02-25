"""포트폴리오 최적화 함수 모음"""
import numpy as np
from scipy.optimize import minimize

def optimize_minimum_variance(returns):
    """최소 분산 포트폴리오 최적화"""
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

def optimize_risk_parity(returns):
    """리스크 패리티 최적화"""
    n_assets = returns.shape[1]
    cov_matrix = returns.cov().values * 252
    
    def risk_parity_objective(weights):
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
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

def optimize_markowitz(returns):
    """마코위츠 최적화"""
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
