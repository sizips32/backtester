"""
통합 데이터 서비스 레이어
중복 코드 제거 및 성능 최적화
"""

import pandas as pd
import numpy as np
import yfinance as yf
# import FinanceDataReader as fdr  # Package no longer available
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
from functools import lru_cache
import hashlib
import json
import time

# 설정 시스템 import
from config.app_config import get_config, get_api_config, get_analysis_config

# 로깅 및 에러 처리 시스템 import
from utils.error_handler import (
    handle_errors, ErrorRecovery, TickerNotFoundError, 
    DataUnavailableError, InsufficientDataError, error_handler
)
from utils.logger import portfolio_logger, log_data_operation

class DataService:
    """통합 데이터 서비스 클래스"""
    
    def __init__(self) -> None:
        """설정 기반 초기화"""
        api_config = get_api_config()
        self.cache_ttl = api_config.cache_ttl_seconds
        self.max_workers = api_config.max_workers
        self.timeout = api_config.timeout_seconds
        self.max_retries = api_config.max_retries
        self._cache: Dict[str, Tuple[pd.DataFrame, datetime]] = {}
        self._now = lambda: datetime.now()

    def _get_cache_key(self, ticker: str, start_date: str, end_date: str) -> str:
        """캐시 키 생성"""
        key_string = f"{ticker}_{start_date}_{end_date}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_cached_data(self, cache_key: str) -> Optional[pd.DataFrame]:
        """In-memory cache lookup with TTL support."""
        entry = self._cache.get(cache_key)
        if not entry:
            return None

        data, expires_at = entry
        if self._now() >= expires_at:
            self._cache.pop(cache_key, None)
            return None
        return data

    def _set_cached_data(self, cache_key: str, data: pd.DataFrame) -> None:
        """Store data with expiration aligned to app configuration."""
        expires_at = self._now() + timedelta(seconds=self.cache_ttl)
        self._cache[cache_key] = (data, expires_at)
    
    def _is_korean_stock(self, ticker: str) -> bool:
        """한국 주식 여부 확인"""
        return (
            (len(ticker) in [6, 7] and ticker.isdigit()) or 
            ticker.endswith('.KS') or 
            ticker.endswith('.KQ')
        )
    
    def _clean_ticker(self, ticker: str) -> str:
        """티커 심볼 정리
        - 한국 종목 처리: 6자리 숫자는 기본적으로 .KS를 붙임, 이미 접미사가 있으면 유지
        - 그 외는 원본 유지 (지수의 ^ 포함)
        """
        t = ticker.strip()
        if t.endswith('.KS') or t.endswith('.KQ'):
            return t
        if len(t) == 6 and t.isdigit():
            return f"{t}.KS"
        return t

    def _korean_ticker_variants(self, ticker: str) -> List[str]:
        """한국 종목일 경우 시도할 심볼 변형 목록 (.KS 우선, 이후 .KQ)"""
        t = ticker.strip()
        if t.endswith('.KS') or t.endswith('.KQ'):
            return [t]
        if len(t) == 6 and t.isdigit():
            return [f"{t}.KS", f"{t}.KQ"]
        return [t]
    
    @st.cache_data(ttl=3600)
    def fetch_single_stock(
        _self, 
        ticker: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """
        단일 주식 데이터 가져오기
        
        Args:
            ticker: 종목 코드
            start_date: 시작일
            end_date: 종료일
            
        Returns:
            주가 데이터 DataFrame 또는 None
        """
        # 날짜 정규화: 순서 보정 및 미래 날짜 캡
        try:
            now_dt = _self._now()
            if end_date > now_dt:
                end_date = now_dt
            if start_date > end_date:
                # 보수적으로 1년 전으로 설정
                start_date, end_date = end_date - timedelta(days=365), end_date
        except Exception:
            pass

        cache_key = _self._get_cache_key(
            ticker, 
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # 캐시 확인
        cached_data = _self._get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data
        
        # 데이터 가져오기 (캐시 미스)
        try:
            df = _self._fetch_from_source(ticker, start_date, end_date)
            
            if df is not None and not df.empty:
                _self._set_cached_data(cache_key, df)
                return df
        except Exception as e:
            portfolio_logger.logger.error(f"Error fetching data for {ticker}: {str(e)}")
            
        return None

    def _fetch_from_source(self, ticker: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """실제 데이터 소스(yfinance)에서 데이터 가져오기"""
        # 한국 종목의 경우 여러 변형을 시도 (.KS -> .KQ)
        candidates = self._korean_ticker_variants(ticker)
        for sym in candidates:
            for attempt in range(self.max_retries):
                try:
                    # yfinance 우선 시도
                    ticker_obj = yf.Ticker(sym)
                    df = ticker_obj.history(start=start_date, end=end_date)
                    if df is not None and not df.empty:
                        return df

                    # yfinance 폴백
                    df = yf.download(
                        sym,
                        start=start_date,
                        end=end_date,
                        progress=False,
                        auto_adjust=True
                    )

                    if df is not None and not df.empty:
                        return df

                except Exception as e:
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # 지수 백오프
                        continue
                    # UI에 의존하지 않고 로깅만 수행
                    portfolio_logger.logger.error(
                        f"DATA_FETCH_FAILED: {sym} | Error: {str(e)}"
                    )
        return None
    
    def fetch_multiple_stocks(
        self,
        tickers: List[str],
        start_date: datetime,
        end_date: datetime,
        show_progress: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        여러 주식 데이터 병렬로 가져오기
        
        Args:
            tickers: 종목 코드 리스트
            start_date: 시작일
            end_date: 종료일
            show_progress: 진행 상황 표시 여부
            
        Returns:
            {ticker: DataFrame} 딕셔너리
        """
        results = {}
        failed = []
        
        # 진행 상황 표시
        if show_progress:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 비동기 작업 제출
            future_to_ticker = {
                executor.submit(
                    self.fetch_single_stock, 
                    ticker, 
                    start_date, 
                    end_date
                ): ticker 
                for ticker in tickers
            }
            
            # 결과 수집
            for i, future in enumerate(as_completed(future_to_ticker)):
                ticker = future_to_ticker[future]
                
                if show_progress:
                    progress = (i + 1) / len(tickers)
                    progress_bar.progress(progress)
                    status_text.text(f"{ticker} 처리 중... ({i+1}/{len(tickers)})")
                
                try:
                    data = future.result()
                    if data is not None:
                        results[ticker] = data
                    else:
                        failed.append(ticker)
                except Exception as e:
                    failed.append(ticker)
                    portfolio_logger.logger.error(
                        f"DATA_FETCH_EXCEPTION: {ticker} | Error: {str(e)}"
                    )
        
        if show_progress:
            progress_bar.empty()
            status_text.empty()
        
        # 실패한 종목 보고
        if failed:
            # 서비스 레이어에서는 로깅만 수행
            portfolio_logger.logger.warning(
                "DATA_BATCH_FETCH_FAILED: " + ", ".join(failed[:5]) + 
                (f" ...(+{len(failed)-5})" if len(failed) > 5 else "")
            )
        
        return results
    
    def get_current_price(self, ticker: str) -> Tuple[Optional[float], Optional[str]]:
        """
        현재가 조회
        
        Args:
            ticker: 종목 코드
            
        Returns:
            (현재가, 에러메시지) 튜플
        """
        # 한국 종목 변형을 모두 시도
        for sym in self._korean_ticker_variants(ticker):
            # 1) yfinance 시도 (실패해도 폴백 계속)
            try:
                tk = yf.Ticker(sym)
                df = tk.history(period="1d")
                if df is not None and not df.empty:
                    price = df['Close'].iloc[-1]
                    return (float(price) if price is not None else None), None
            except Exception:
                pass

            # 2) yfinance.history 시도
            try:
                ticker_obj = yf.Ticker(sym)
                hist = ticker_obj.history(period="1d", auto_adjust=True)
                if hist is not None and not hist.empty:
                    price = hist['Close'].iloc[-1]
                    return (float(price) if price is not None else None), None
            except Exception:
                pass

            # 3) yfinance.fast_info 시도
            try:
                fi = getattr(yf.Ticker(sym), 'fast_info', None)
                if fi and getattr(fi, 'last_price', None) is not None:
                    return float(fi.last_price), None
            except Exception:
                pass

            # 4) yfinance.info 시도
            try:
                info = yf.Ticker(sym).info
                price_fields = ['regularMarketPrice', 'currentPrice', 'price']
                for field in price_fields:
                    if field in info and info[field] is not None:
                        return float(info[field]), None
            except Exception:
                pass
        
        return None, "가격 정보를 찾을 수 없습니다"
    
    def calculate_returns(
        self, 
        prices: pd.DataFrame, 
        method: str = 'simple'
    ) -> pd.DataFrame:
        """
        수익률 계산
        
        Args:
            prices: 가격 데이터
            method: 'simple' 또는 'log'
            
        Returns:
            수익률 DataFrame
        """
        if method == 'simple':
            return prices.pct_change()
        elif method == 'log':
            return np.log(prices / prices.shift(1))
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def combine_price_data(
        self, 
        data_dict: Dict[str, pd.DataFrame],
        price_column: str = 'Close'
    ) -> pd.DataFrame:
        """
        여러 종목의 가격 데이터 결합
        
        Args:
            data_dict: {ticker: DataFrame} 딕셔너리
            price_column: 사용할 가격 컬럼명
            
        Returns:
            결합된 가격 DataFrame
        """
        price_data = {}
        
        for ticker, df in data_dict.items():
            if price_column in df.columns:
                price_data[ticker] = df[price_column]
            elif len(df.columns) == 1:
                price_data[ticker] = df.iloc[:, 0]
            else:
                # 멀티 인덱스 처리 (yfinance)
                if isinstance(df.columns, pd.MultiIndex):
                    price_data[ticker] = df[price_column][ticker]
                else:
                    price_data[ticker] = df[price_column]
        
        combined = pd.DataFrame(price_data)
        
        # 결측치 처리
        combined = combined.ffill().bfill()
        
        return combined
    
    def validate_data_quality(
        self, 
        data: pd.DataFrame,
        min_data_points: int = None,
        max_na_ratio: float = None
    ) -> Tuple[bool, str]:
        """
        데이터 품질 검증
        
        Args:
            data: 검증할 데이터
            min_data_points: 최소 데이터 포인트 수
            max_na_ratio: 최대 결측치 비율
            
        Returns:
            (유효 여부, 메시지) 튜플
        """
        analysis_config = get_analysis_config()
        min_data_points = min_data_points or analysis_config.min_analysis_days
        max_na_ratio = max_na_ratio or analysis_config.max_missing_data_ratio
        if data.empty:
            return False, "데이터가 비어있습니다"
        
        if len(data) < min_data_points:
            return False, f"데이터 포인트가 너무 적습니다 ({len(data)} < {min_data_points})"
        
        na_ratio = data.isna().sum().sum() / (len(data) * len(data.columns))
        if na_ratio > max_na_ratio:
            return False, f"결측치 비율이 너무 높습니다 ({na_ratio:.1%} > {max_na_ratio:.1%})"
        
        return True, "데이터 품질 검증 통과"
    
    @st.cache_data(ttl=3600)
    def get_exchange_rate(_self, from_currency: str, to_currency: str, date: datetime = None) -> Optional[float]:
        """
        환율 정보 가져오기
        
        Args:
            from_currency: 기준 통화 (예: 'USD')
            to_currency: 대상 통화 (예: 'KRW')
            date: 환율 조회 날짜 (기본값: 현재)
            
        Returns:
            환율 또는 None
        """
        if date is None:
            date = _self._now()
        
        # USD/KRW 환율 조회
        if from_currency == 'USD' and to_currency == 'KRW':
            try:
                # USD/KRW 환율 티커 (여러 변형 시도)
                # "USD/KRW"는 yfinance에서 지원하지 않으므로 제거
                tickers = ["USDKRW=X", "KRW=X"]
                for ticker_symbol in tickers:
                    try:
                        ticker = yf.Ticker(ticker_symbol)
                        df = ticker.history(start=date, end=date + timedelta(days=1), period="1d")
                        if not df.empty:
                            return float(df['Close'].iloc[-1])
                    except Exception:
                        continue
            except Exception:
                pass
        
        # KRW/USD 환율 조회 (역환율)
        elif from_currency == 'KRW' and to_currency == 'USD':
            try:
                # USD/KRW 환율을 먼저 가져온 후 역환율 계산
                usd_krw_rate = _self.get_exchange_rate('USD', 'KRW', date)
                if usd_krw_rate:
                    return 1.0 / usd_krw_rate
            except Exception:
                pass
        
        # 환율 조회 실패 시 기본값 사용 (대략적인 환율)
        if from_currency == 'USD' and to_currency == 'KRW':
            return 1400.0  # 대략적인 USD/KRW 환율
        elif from_currency == 'KRW' and to_currency == 'USD':
            return 1.0 / 1400.0  # 대략적인 KRW/USD 환율
        
        return None
    
    def convert_currency(self, amount: float, from_currency: str, to_currency: str, date: datetime = None) -> Optional[float]:
        """
        통화 변환
        
        Args:
            amount: 변환할 금액
            from_currency: 기준 통화
            to_currency: 대상 통화
            date: 환율 기준 날짜
            
        Returns:
            변환된 금액 또는 None
        """
        if from_currency == to_currency:
            return amount
        
        rate = self.get_exchange_rate(from_currency, to_currency, date)
        if rate is not None:
            return amount * rate
        
        return None

    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._cache.clear()
        st.cache_data.clear()


# 싱글톤 인스턴스
data_service = DataService()
