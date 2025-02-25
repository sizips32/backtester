"""설정 파일 분리"""
import os
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class Config:
    PORTFOLIO_FILE = 'portfolio.json'
    DEFAULT_RISK_FREE_RATE = 0.02
    MARKET_INDICES = {
        "KOSPI": "^KS11",
        "S&P 500": "^GSPC"
    }
    ANALYSIS_PERIODS = {
        "1개월": 30,
        "3개월": 90,
        "6개월": 180,
        "1년": 365,
        "3년": 1095,
        "5년": 1825
    }

@dataclass
class BacktestConfig:
    """백테스트 설정"""
    initial_capital: float = 100_000_000
    risk_free_rate: float = 0.02
    transaction_cost: float = 0.0015
    rebalancing_frequency: str = "monthly"

@dataclass
class RiskConfig:
    """리스크 관리 설정"""
    max_drawdown: float = 0.20
    var_confidence: float = 0.95
    stop_loss: float = 0.05
    position_size_limit: float = 0.20

@dataclass
class AppConfig:
    """앱 전체 설정"""
    PORTFOLIO_FILE: str = 'portfolio.json'
    DEFAULT_RISK_FREE_RATE: float = 0.02
    CACHE_TTL: int = 3600
    DATA_MIN_PERIODS: int = 252
    
    # 시장 지수 설정
    MARKET_INDICES: Dict[str, str] = {
        "KOSPI": "^KS11",
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC"
    }
    
    # 분석 기간 설정
    ANALYSIS_PERIODS: Dict[str, int] = {
        "1개월": 30,
        "3개월": 90,
        "6개월": 180,
        "1년": 365,
        "3년": 1095,
        "5년": 1825
    }
    
    # 리스크 관리 설정
    RISK_LIMITS = {
        "max_drawdown": 0.20,
        "var_confidence": 0.95,
        "stop_loss": 0.05,
        "position_size": 0.20
    }

config = AppConfig() 
