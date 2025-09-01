"""
데이터 검증 시스템
입력 데이터의 품질과 유효성을 체계적으로 검증
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any, Optional, Union
import streamlit as st
from utils.error_handler import ValidationError, InsufficientDataError

# 설정 시스템 import
from config.app_config import get_validation_config

class DataValidator:
    """데이터 검증 클래스"""
    
    def __init__(self) -> None:
        self.config = get_validation_config()
    
    @property
    def TICKER_PATTERNS(self) -> Dict[str, str]:
        """설정에서 가져온 종목 코드 패턴"""
        return self.config.ticker_patterns
    
    @property
    def ASSET_TYPE_RULES(self) -> Dict[str, Dict[str, float]]:
        """설정에서 가져온 자산 유형별 규칙"""
        return self.config.asset_limits
    
    def validate_ticker(self, ticker: str) -> Tuple[bool, str, str]:
        """
        종목 코드 검증
        
        Args:
            ticker: 검증할 종목 코드
            
        Returns:
            (유효성, 에러메시지, 종목타입)
        """
        if not ticker:
            return False, "종목 코드를 입력해주세요.", ""
        
        ticker = ticker.strip().upper()
        
        # 각 패턴별로 검증
        for ticker_type, pattern in self.TICKER_PATTERNS.items():
            if re.match(pattern, ticker):
                return True, "", ticker_type
        
        return False, f"유효하지 않은 종목 코드 형식입니다: {ticker}", ""
    
    def validate_asset_data(
        self, 
        asset_type: str, 
        quantity: float, 
        price: float
    ) -> Tuple[bool, List[str]]:
        """
        자산 데이터 검증
        
        Args:
            asset_type: 자산 유형
            quantity: 수량
            price: 가격
            
        Returns:
            (유효성, 에러메시지 리스트)
        """
        errors = []
        
        if asset_type not in self.ASSET_TYPE_RULES:
            errors.append(f"지원하지 않는 자산 유형입니다: {asset_type}")
            return False, errors
        
        rules = self.ASSET_TYPE_RULES[asset_type]
        
        # 수량 검증
        if quantity <= 0:
            errors.append("수량은 0보다 커야 합니다.")
        elif quantity < rules['min_quantity']:
            errors.append(f"수량이 너무 작습니다. 최소 {rules['min_quantity']} 이상이어야 합니다.")
        
        # 가격 검증
        if price <= 0:
            errors.append("가격은 0보다 커야 합니다.")
        elif price < rules['min_price']:
            errors.append(f"가격이 너무 낮습니다. 최소 ${rules['min_price']} 이상이어야 합니다.")
        elif price > rules['max_price']:
            errors.append(f"가격이 너무 높습니다. 최대 ${rules['max_price']} 이하여야 합니다.")
        
        return len(errors) == 0, errors
    
    def validate_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        min_days: Optional[int] = None,
        max_days: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """
        날짜 범위 검증
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            min_days: 최소 기간 (일)
            max_days: 최대 기간 (일)
            
        Returns:
            (유효성, 에러메시지 리스트)
        """
        # 설정에서 기본값 가져오기
        from config.app_config import get_analysis_config
        analysis_cfg = get_analysis_config()
        
        min_days = min_days or analysis_cfg.min_analysis_days
        max_days = max_days or analysis_cfg.max_analysis_days
        
        errors = []
        
        # 기본 검증
        if start_date >= end_date:
            errors.append("시작 날짜는 종료 날짜보다 빨라야 합니다.")
            return False, errors
        
        # 미래 날짜 검증
        today = datetime.now().date()
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
            
        if end_date > today:
            errors.append("종료 날짜는 오늘 날짜를 초과할 수 없습니다.")
        
        # 기간 검증
        period_days = (end_date - start_date).days
        
        if period_days < min_days:
            errors.append(f"분석 기간이 너무 짧습니다. 최소 {min_days}일 이상이어야 합니다.")
        
        if period_days > max_days:
            errors.append(f"분석 기간이 너무 깁니다. 최대 {max_days}일 이하여야 합니다.")
        
        return len(errors) == 0, errors
    
    def validate_portfolio_weights(
        self, 
        weights: Dict[str, float],
        tolerance: Optional[float] = None
    ) -> Tuple[bool, List[str]]:
        """
        포트폴리오 가중치 검증
        
        Args:
            weights: {자산: 가중치} 딕셔너리
            tolerance: 허용 오차
            
        Returns:
            (유효성, 에러메시지 리스트)
        """
        # 설정에서 기본값 가져오기
        tolerance = tolerance or self.config.weight_tolerance
        
        errors = []
        
        if not weights:
            errors.append("포트폴리오 가중치가 비어있습니다.")
            return False, errors
        
        # 개별 가중치 검증
        for asset, weight in weights.items():
            if weight < 0:
                errors.append(f"{asset}: 가중치는 음수일 수 없습니다.")
            elif weight > 1:
                errors.append(f"{asset}: 가중치는 1을 초과할 수 없습니다.")
        
        # 가중치 합계 검증
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > tolerance:
            errors.append(
                f"가중치 합계가 100%가 아닙니다. "
                f"현재: {total_weight:.3f} (허용 오차: ±{tolerance})"
            )
        
        return len(errors) == 0, errors

class DataQualityChecker:
    """데이터 품질 검사 클래스"""
    
    @staticmethod
    def check_data_completeness(
        data: pd.DataFrame,
        min_completeness: float = 0.8
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        데이터 완성도 검사
        
        Args:
            data: 검사할 데이터프레임
            min_completeness: 최소 완성도 (0.0~1.0)
            
        Returns:
            (통과 여부, 상세 정보)
        """
        if data.empty:
            return False, {"error": "데이터가 비어있습니다."}
        
        # 결측치 비율 계산
        total_cells = data.size
        missing_cells = data.isna().sum().sum()
        completeness = 1 - (missing_cells / total_cells)
        
        details = {
            "completeness": completeness,
            "missing_cells": missing_cells,
            "total_cells": total_cells,
            "missing_by_column": data.isna().sum().to_dict(),
            "min_required": min_completeness
        }
        
        passed = completeness >= min_completeness
        
        if not passed:
            details["error"] = f"데이터 완성도가 부족합니다. " \
                             f"현재: {completeness:.2%}, 최소: {min_completeness:.2%}"
        
        return passed, details
    
    @staticmethod
    def check_data_consistency(data: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        데이터 일관성 검사
        
        Args:
            data: 검사할 데이터프레임
            
        Returns:
            (통과 여부, 상세 정보)
        """
        issues = []
        details = {}
        
        # 음수 가격 검사
        if data.select_dtypes(include=[np.number]).lt(0).any().any():
            issues.append("음수 가격이 발견되었습니다.")
            details["negative_values"] = True
        
        # 이상치 검사 (IQR 방법)
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        outliers_info = {}
        
        for col in numeric_cols:
            Q1 = data[col].quantile(0.25)
            Q3 = data[col].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = data[(data[col] < lower_bound) | (data[col] > upper_bound)]
            if len(outliers) > 0:
                outliers_info[col] = {
                    "count": len(outliers),
                    "percentage": len(outliers) / len(data) * 100,
                    "bounds": {"lower": lower_bound, "upper": upper_bound}
                }
        
        if outliers_info:
            details["outliers"] = outliers_info
            issues.append("이상치가 발견되었습니다.")
        
        # 데이터 타입 검사
        if data.dtypes.apply(lambda x: x == 'object').any():
            details["non_numeric_columns"] = data.select_dtypes(include=['object']).columns.tolist()
        
        details["issues"] = issues
        passed = len(issues) == 0
        
        return passed, details
    
    @staticmethod
    def check_temporal_consistency(
        data: pd.DataFrame,
        date_column: str = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        시계열 데이터 일관성 검사
        
        Args:
            data: 검사할 데이터프레임
            date_column: 날짜 컬럼명 (None이면 인덱스 사용)
            
        Returns:
            (통과 여부, 상세 정보)
        """
        issues = []
        details = {}
        
        # 날짜 인덱스 또는 컬럼 확인
        if date_column:
            if date_column not in data.columns:
                return False, {"error": f"날짜 컬럼 '{date_column}'을 찾을 수 없습니다."}
            dates = data[date_column]
        else:
            if not isinstance(data.index, pd.DatetimeIndex):
                return False, {"error": "데이터의 인덱스가 날짜 타입이 아닙니다."}
            dates = data.index
        
        # 날짜 순서 검사
        if not dates.is_monotonic_increasing:
            issues.append("날짜가 순차적으로 정렬되지 않았습니다.")
        
        # 중복 날짜 검사
        duplicates = dates.duplicated().sum()
        if duplicates > 0:
            issues.append(f"중복된 날짜가 {duplicates}개 발견되었습니다.")
            details["duplicate_dates"] = duplicates
        
        # 날짜 간격 검사
        if len(dates) > 1:
            date_diffs = dates.to_series().diff().dropna()
            
            # 주말 제외한 영업일 기준
            median_diff = date_diffs.median()
            std_diff = date_diffs.std()
            
            # 비정상적인 간격 검사
            abnormal_gaps = date_diffs[
                (date_diffs > median_diff + 2 * std_diff) |
                (date_diffs < timedelta(0))
            ]
            
            if len(abnormal_gaps) > 0:
                issues.append("비정상적인 날짜 간격이 발견되었습니다.")
                details["abnormal_gaps"] = len(abnormal_gaps)
        
        details["issues"] = issues
        passed = len(issues) == 0
        
        return passed, details

class PortfolioValidator:
    """포트폴리오 전용 검증 클래스"""
    
    @staticmethod
    def validate_portfolio_data(
        symbols: List[str],
        weights: Dict[str, float],
        data: Optional[pd.DataFrame] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        포트폴리오 데이터 종합 검증
        
        Args:
            symbols: 종목 리스트
            weights: 가중치 딕셔너리
            data: 가격 데이터 (선택사항)
            
        Returns:
            (유효성, 검증 결과 상세)
        """
        results = {
            "passed": True,
            "errors": [],
            "warnings": [],
            "details": {}
        }
        
        # 종목 코드 검증
        validator = DataValidator()
        ticker_results = []
        for symbol in symbols:
            valid, error, ticker_type = validator.validate_ticker(symbol)
            ticker_results.append({
                "symbol": symbol,
                "valid": valid,
                "error": error,
                "type": ticker_type
            })
            
            if not valid:
                results["errors"].append(f"{symbol}: {error}")
                results["passed"] = False
        
        results["details"]["tickers"] = ticker_results
        
        # 가중치 검증
        weights_valid, weight_errors = validator.validate_portfolio_weights(weights)
        if not weights_valid:
            results["errors"].extend(weight_errors)
            results["passed"] = False
        
        # 종목과 가중치 일치성 검사
        symbol_set = set(symbols)
        weight_set = set(weights.keys())
        
        missing_weights = symbol_set - weight_set
        extra_weights = weight_set - symbol_set
        
        if missing_weights:
            results["errors"].append(f"가중치가 누락된 종목: {missing_weights}")
            results["passed"] = False
        
        if extra_weights:
            results["warnings"].append(f"불필요한 가중치: {extra_weights}")
        
        # 데이터 품질 검사 (데이터가 제공된 경우)
        if data is not None and not data.empty:
            completeness_ok, completeness_details = DataQualityChecker.check_data_completeness(data)
            consistency_ok, consistency_details = DataQualityChecker.check_data_consistency(data)
            temporal_ok, temporal_details = DataQualityChecker.check_temporal_consistency(data)
            
            results["details"]["data_quality"] = {
                "completeness": completeness_details,
                "consistency": consistency_details,
                "temporal": temporal_details
            }
            
            if not completeness_ok:
                results["errors"].append("데이터 완성도가 부족합니다.")
                results["passed"] = False
            
            if not consistency_ok:
                results["warnings"].extend(consistency_details.get("issues", []))
            
            if not temporal_ok:
                results["warnings"].extend(temporal_details.get("issues", []))
        
        return results["passed"], results

def show_validation_results(results: Dict[str, Any]) -> None:
    """검증 결과를 Streamlit UI로 표시"""
    if results["passed"]:
        st.success("✅ 모든 검증을 통과했습니다!")
    else:
        st.error("❌ 검증에 실패했습니다.")
    
    # 에러 표시
    if results["errors"]:
        st.subheader("🚨 오류")
        for error in results["errors"]:
            st.error(f"• {error}")
    
    # 경고 표시
    if results["warnings"]:
        st.subheader("⚠️ 경고")
        for warning in results["warnings"]:
            st.warning(f"• {warning}")
    
    # 상세 정보 표시 (접기 가능)
    if results.get("details"):
        with st.expander("📊 상세 검증 정보", expanded=False):
            st.json(results["details"])

# 전역 validator 인스턴스
default_validator = DataValidator()

# 편의 함수들
def validate_ticker_input(ticker: str) -> bool:
    """티커 입력 검증 (UI용)"""
    valid, error, _ = default_validator.validate_ticker(ticker)
    if not valid:
        st.error(error)
    return valid

def validate_weights_input(weights: Dict[str, float]) -> bool:
    """가중치 입력 검증 (UI용)"""
    valid, errors = default_validator.validate_portfolio_weights(weights)
    if not valid:
        for error in errors:
            st.error(error)
    return valid

def validate_date_input(start_date: datetime, end_date: datetime) -> bool:
    """날짜 범위 검증 (UI용)"""
    valid, errors = default_validator.validate_date_range(start_date, end_date)
    if not valid:
        for error in errors:
            st.error(error)
    return valid