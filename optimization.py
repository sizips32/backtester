"""
포트폴리오 최적화 함수 모음 (Deprecated)
modules.optimization_engine.OptimizationEngine을 사용하세요.
"""
from modules.optimization_engine import OptimizationEngine

def optimize_minimum_variance(returns):
    """최소 분산 포트폴리오 최적화"""
    return OptimizationEngine.optimize_minimum_variance(returns)

def optimize_risk_parity(returns):
    """리스크 패리티 최적화"""
    return OptimizationEngine.optimize_risk_parity(returns)

def optimize_markowitz(returns):
    """마코위츠 최적화"""
    return OptimizationEngine.optimize_markowitz(returns)
