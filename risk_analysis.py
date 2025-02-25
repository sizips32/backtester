import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from scipy import stats
from datetime import datetime, timedelta
import plotly.graph_objects as go

class RiskAnalysisError(Exception):
    """리스크 분석 관련 커스텀 예외"""
    pass

def safe_calculation(func):
    """에러 처리를 위한 데코레이터"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"{func.__name__} 계산 중 오류 발생: {str(e)}")
            return 0
    return wrapper

@safe_calculation
def calculate_var(returns, confidence_level=0.95):
    if len(returns.dropna()) < 2:
        raise RiskAnalysisError("충분한 데이터가 없습니다")
    return np.percentile(returns.dropna(), (1 - confidence_level) * 100)

def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    """샤프 비율 계산"""
    try:
        returns = returns.dropna()
        if len(returns) < 2:
            return 0
        excess_returns = returns - risk_free_rate/252
        annual_factor = np.sqrt(252)
        if returns.std() == 0:
            return 0
        return annual_factor * excess_returns.mean() / returns.std()
    except Exception as e:
        st.error(f"Sharpe Ratio 계산 중 오류 발생: {str(e)}")
        return 0

def calculate_cvar(returns, confidence_level=0.95):
    try:
        returns = returns.dropna()
        if len(returns) < 2:
            return 0
        var = calculate_var(returns, confidence_level)
        return returns[returns <= var].mean() if len(returns[returns <= var]) > 0 else 0
    except Exception as e:
        st.error(f"CVaR 계산 중 오류 발생: {str(e)}")
        return 0

def calculate_sortino_ratio(returns, risk_free_rate=0.02):
    try:
        returns = returns.dropna()
        if len(returns) < 2:
            return 0
        excess_returns = returns - risk_free_rate/252
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std()
        return np.sqrt(252) * excess_returns.mean() / downside_std if downside_std != 0 else 0
    except Exception as e:
        st.error(f"Sortino Ratio 계산 중 오류 발생: {str(e)}")
        return 0

def calculate_beta(returns, market_returns):
    try:
        # Series가 아닌 경우 Series로 변환
        if isinstance(returns, pd.DataFrame):
            returns = returns.iloc[:, 0]
        if isinstance(market_returns, pd.DataFrame):
            market_returns = market_returns.iloc[:, 0]
            
        # 두 시리즈의 인덱스를 맞춤
        aligned_returns = pd.DataFrame({
            'stock': returns.squeeze() if hasattr(returns, 'squeeze') else returns,
            'market': market_returns.squeeze() if hasattr(market_returns, 'squeeze') else market_returns
        }).dropna()
        
        if len(aligned_returns) < 2:  # 데이터가 충분하지 않은 경우
            return 0
        
        covariance = np.cov(aligned_returns['stock'], aligned_returns['market'])[0][1]
        market_variance = np.var(aligned_returns['market'])
        return covariance / market_variance if market_variance != 0 else 0
        
    except Exception as e:
        st.error(f"Beta 계산 중 오류 발생: {str(e)}")
        return 0

def show_risk_analysis():
    try:
        st.header("리스크 분석")
        
        # 사이드바에 기간 설정과 기준 시장 선택 추가
        with st.sidebar:
            st.subheader("기간 설정")
            period = st.selectbox(
                "분석 기간",
                ["1개월", "3개월", "6개월", "1년", "3년", "5년"],
                index=3
            )
            
            period_days = {
                "1개월": 30,
                "3개월": 90,
                "6개월": 180,
                "1년": 365,
                "3년": 1095,
                "5년": 1825
            }
            
            st.subheader("베타 계산 설정")
            market_index = st.selectbox(
                "기준 시장 지수 선택",
                ["KOSPI", "S&P 500"],
                index=0
            )
            
            market_ticker = {
                "KOSPI": "^KS11",
                "S&P 500": "^GSPC"
            }

        # 티커 입력 받기
        ticker_input = st.text_input(
            "분석할 종목 코드를 입력하세요 (여러 종목은 쉼표로 구분, 예: 005930.KS,035720.KS)",
            value="005930.KS"
        )
        
        # 입력된 티커를 리스트로 변환
        tickers = [ticker.strip() for ticker in ticker_input.split(',') if ticker.strip()]
        
        if not tickers:
            st.warning("종목 코드를 입력해주세요.")
            return
        
        # 기간 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days[period])
        
        # 데이터 가져오기
        data = pd.DataFrame()
        market_data = pd.DataFrame()
        failed_tickers = []
        
        # 시장 데이터 가져오기
        try:
            market_data = yf.download(market_ticker[market_index], start=start_date, end=end_date)
            if market_data.empty:
                st.error(f"{market_index} 데이터를 가져오지 못했습니다.")
                return
            market_returns = market_data['Close'].pct_change()
        except Exception as e:
            st.error(f"시장 지수 데이터 로드 중 오류 발생: {str(e)}")
            return
        
        # 종목 데이터 가져오기
        for ticker in tickers:
            try:
                stock = yf.download(ticker, start=start_date, end=end_date)
                if stock.empty or 'Close' not in stock.columns:
                    failed_tickers.append(ticker)
                    continue
                data[ticker] = stock['Close']
            except Exception as e:
                st.error(f"{ticker} 데이터 로드 중 오류 발생: {str(e)}")
                failed_tickers.append(ticker)
        
        # 실패한 종목들 제거
        for ticker in failed_tickers:
            tickers.remove(ticker)
        
        if not tickers:
            st.error("분석 가능한 데이터가 없습니다.")
            return
        
        if failed_tickers:
            st.warning(f"다음 종목들의 데이터를 가져오지 못했습니다: {', '.join(failed_tickers)}")
        
        # 일간 수익률 계산
        returns = data.pct_change()
        
        # 리스크 지표 계산
        for ticker in tickers:
            try:
                st.subheader(f"{ticker} 리스크 분석")
                
                # 데이터 유효성 검사
                if returns[ticker].empty or len(returns[ticker].dropna()) < 2:
                    st.warning(f"{ticker}의 유효한 데이터가 충분하지 않습니다.")
                    continue
                
                # 리스크 지표 계산
                try:
                    var_95 = calculate_var(returns[ticker], 0.95)
                    var_99 = calculate_var(returns[ticker], 0.99)
                    cvar_95 = calculate_cvar(returns[ticker], 0.95)
                    sharpe = calculate_sharpe_ratio(returns[ticker])
                    sortino = calculate_sortino_ratio(returns[ticker])
                    beta = calculate_beta(returns[ticker], market_returns)
                    volatility = returns[ticker].std() * np.sqrt(252) if not returns[ticker].empty else 0
                    
                    # Maximum Drawdown 계산
                    try:
                        cumulative_returns = (1 + returns[ticker].dropna()).cumprod()
                        rolling_max = cumulative_returns.expanding().max()
                        drawdowns = cumulative_returns/rolling_max - 1
                        max_drawdown = drawdowns.min()
                    except Exception as e:
                        st.error(f"Maximum Drawdown 계산 중 오류 발생: {str(e)}")
                        max_drawdown = 0
                    
                    # 결과 표시
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("VaR (95%)", f"{var_95:.2%}")
                        st.metric("CVaR (95%)", f"{cvar_95:.2%}")
                    with col2:
                        st.metric("Sharpe Ratio", f"{sharpe:.2f}")
                        st.metric("Sortino Ratio", f"{sortino:.2f}")
                    with col3:
                        st.metric(f"Beta ({market_index})", f"{beta:.2f}")
                        st.metric("Volatility", f"{volatility:.2%}")
                    with col4:
                        st.metric("Maximum Drawdown", f"{max_drawdown:.2%}")
                        st.metric("VaR (99%)", f"{var_99:.2%}")
                    
                    # 수익률 분포 시각화
                    try:
                        fig = go.Figure()
                        fig.add_trace(go.Histogram(
                            x=returns[ticker].dropna(),
                            nbinsx=50,
                            name='수익률 분포'
                        ))
                        fig.update_layout(
                            title=f"{ticker} 일간 수익률 분포",
                            xaxis_title="수익률",
                            yaxis_title="빈도"
                        )
                        st.plotly_chart(fig)
                    except Exception as e:
                        st.error(f"수익률 분포 시각화 중 오류 발생: {str(e)}")
                
                except Exception as e:
                    st.error(f"{ticker}의 리스크 지표 계산 중 오류 발생: {str(e)}")
            
            except Exception as e:
                st.error(f"{ticker} 처리 중 오류 발생: {str(e)}")
                continue
    
    except Exception as e:
        st.error(f"리스크 분석 중 예상치 못한 오류 발생: {str(e)}")
