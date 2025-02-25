"""데이터 검증 유틸리티"""
from typing import List, Dict, Union
import pandas as pd
import numpy as np

def validate_portfolio_data(
    data: pd.DataFrame,
    min_periods: int = 252
) -> bool:
    """포트폴리오 데이터 유효성 검증"""
    if data.empty:
        raise ValueError("데이터가 비어있습니다")
    
    if data.isnull().any().any():
        raise ValueError("결측치가 존재합니다")
        
    if len(data) < min_periods:
        raise ValueError(f"최소 {min_periods}개의 데이터가 필요합니다")
    
    return True

def validate_weights(weights: Dict[str, float]) -> bool:
    """포트폴리오 비중 검증"""
    if not weights:
        raise ValueError("비중 데이터가 없습니다")
        
    if not np.isclose(sum(weights.values()), 1.0, rtol=1e-5):
        raise ValueError("비중의 합이 1이 아닙니다")
        
    if any(w < 0 for w in weights.values()):
        raise ValueError("음수 비중이 존재합니다")
    
    return True 
