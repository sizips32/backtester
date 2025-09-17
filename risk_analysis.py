import streamlit as st
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import plotly.graph_objects as go
from services.data_service import data_service

# 상수 정의
class Config:
    RISK_FREE_RATE = 0.02
    TRADING_DAYS = 252
    CONFIDENCE_LEVELS = {
        "standard": 0.95,
        "strict": 0.99
    }
    ROLLING_WINDOWS = {
        "short": 20,
        "long": 60
    }

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
        excess_returns = returns.mean() * 252 - risk_free_rate
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std()
        return np.sqrt(252) * excess_returns.mean() / downside_std if downside_std != 0 else 0
    except Exception as e:
        st.error(f"Sortino Ratio 계산 중 오류 발생: {str(e)}")
        return 0

def validate_ticker(ticker):
    """티커 심볼 검증 (데이터 서비스 사용)"""
    try:
        end = datetime.now()
        start = end - timedelta(days=180)
        df = data_service.fetch_single_stock(ticker, start, end)
        return df is not None and not df.empty
    except Exception as e:
        st.warning(f"{ticker}: 유효하지 않은 티커 심볼입니다. ({str(e)})")
        return False

@st.cache_data
def fetch_stock_data(ticker, start_date, end_date):
    """주식 데이터 조회 (데이터 서비스 사용)"""
    try:
        df = data_service.fetch_single_stock(ticker, start_date, end_date)
        if df is None or df.empty:
            return pd.DataFrame()
        return df[['Close']] if 'Close' in df.columns else pd.DataFrame(df.iloc[:, 0])
    except Exception as e:
        st.error(f"{ticker} 데이터 다운로드 실패: {str(e)}")
        return pd.DataFrame()

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

            # 기간 설정
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days[period])

            # 벤치마크 지수 데이터 가져오기 (데이터 서비스 사용)
            try:
                st.subheader("벤치마크 지수 성과")
                benchmark_tickers = {
                    "S&P500": "US500",    # S&P 500
                    "KOSPI": "KS11",      # KOSPI
                    "상해종합": "SSEC",     # 상해종합
                    "일본Nikkei": "N225"    # 니케이225
                }
                
                benchmark_data = pd.DataFrame()
                for name, ticker in benchmark_tickers.items():
                    try:
                        df = data_service.fetch_single_stock(ticker, start_date, end_date)
                        if df is not None and not df.empty:
                            series = df['Close'] if 'Close' in df.columns else df.iloc[:, 0]
                            benchmark_data[name] = series
                            st.success(f"{name} 데이터 조회 성공")
                    except Exception as e:
                        st.warning(f"{name} 데이터 조회 실패: {str(e)}")
                        continue
                
                if not benchmark_data.empty:
                    # 누적수익률 계산
                    benchmark_returns = benchmark_data.pct_change()
                    benchmark_cum_returns = (1 + benchmark_returns).cumprod() - 1
                    
                    # 그래프 생성
                    fig_benchmark = go.Figure()
                    colors = {
                        "S&P500": "#00ffff",      # 하늘색
                        "KOSPI": "#ff9900",       # 주황색
                        "상해종합": "#00ff00",     # 연두색
                        "일본Nikkei": "#ff3333"    # 빨간색
                    }
                    
                    for name in benchmark_data.columns:
                        fig_benchmark.add_trace(go.Scatter(
                            x=benchmark_cum_returns.index,
                            y=benchmark_cum_returns[name],
                            mode='lines',
                            name=name,
                            line=dict(color=colors.get(name, "#ffffff"), width=1.5)
                        ))
                    
                    fig_benchmark.update_layout(
                        height=250,
                        margin=dict(l=5, r=5, t=25, b=25),
                        title=dict(
                            text="벤치마크 지수 누적수익률",
                            x=0.5,
                            y=0.95,
                            xanchor='center',
                            yanchor='top',
                            font=dict(size=14, color='white')
                        ),
                        xaxis=dict(
                            showgrid=True,
                            gridcolor='rgba(128, 128, 128, 0.2)',
                            tickfont=dict(color='white')
                        ),
                        yaxis=dict(
                            showgrid=True,
                            gridcolor='rgba(128, 128, 128, 0.2)',
                            tickfont=dict(color='white'),
                            tickformat='.1%'
                        ),
                        yaxis_tickformat='.1%',
                        hovermode='x unified',
                        legend=dict(
                            orientation="h",
                            yanchor="top",
                            y=-0.15,
                            xanchor="center",
                            x=0.5,
                            bgcolor="rgba(0, 0, 0, 0.5)",
                            font=dict(size=10, color='white'),
                            bordercolor='rgba(128, 128, 128, 0.2)'
                        ),
                        plot_bgcolor='black',
                        paper_bgcolor='black'
                    )
                    st.plotly_chart(fig_benchmark, use_container_width=True)
                else:
                    st.warning("벤치마크 지수 데이터를 가져올 수 없습니다.")
            except Exception as e:
                st.error(f"벤치마크 지수 처리 중 오류 발생: {str(e)}")
                st.info("일부 벤치마크 지수 데이터만 표시될 수 있습니다.")

        # 티커 입력 받기
        ticker_input = st.text_input(
            "분석할 종목 코드를 입력하세요 (여러 종목은 쉼표로 구분, 예: 005930,035720)",
            value="005930"
        )
        
        # 입력된 티커를 리스트로 변환
        tickers = [
            ticker.strip() 
            for ticker in ticker_input.split(',') 
            if ticker.strip() and validate_ticker(ticker.strip())
        ]
        
        if not tickers:
            st.warning("종목 코드를 입력해주세요.")
            return
        
        # 데이터 가져오기
        data = pd.DataFrame()
        failed_tickers = []
        
        # 종목 데이터 가져오기
        for ticker in tickers:
            try:
                stock_data = fetch_stock_data(ticker, start_date, end_date)
                if stock_data.empty:
                    st.warning(f"{ticker}: 데이터를 찾을 수 없습니다.")
                    continue
                data[ticker] = stock_data['Close']
            except Exception as e:
                st.error(f"{ticker} 데이터 다운로드 실패: {str(e)}")
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
                if len(returns[ticker].dropna()) < 2:
                    st.warning(f"{ticker}의 유효한 데이터가 충분하지 않습니다.")
                    continue
                
                # 리스크 지표 계산
                try:
                    var_95 = calculate_var(returns[ticker], 0.95)
                    var_99 = calculate_var(returns[ticker], 0.99)
                    cvar_95 = calculate_cvar(returns[ticker], 0.95)
                    sharpe = calculate_sharpe_ratio(returns[ticker])
                    sortino = calculate_sortino_ratio(returns[ticker])
                    has_data = len(returns[ticker]) > 0
                    volatility = returns[ticker].std() * np.sqrt(252) if has_data else 0
                    
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
                    
                    # 성과 분석 섹션 추가
                    st.subheader(f"{ticker} 성과 분석")
                    
                    try:
                        # 누적 수익률 계산
                        cumulative_returns = (1 + returns[ticker].dropna()).cumprod() - 1
                        
                        # 연간화된 수익률 계산
                        total_days = (data.index[-1] - data.index[0]).days
                        annual_return = (
                            (1 + cumulative_returns.iloc[-1]) ** (365 / total_days) - 1 
                            if total_days > 0 
                            else 0
                        )
                        
                        # 월간 수익률 계산
                        try:
                            # 일별 데이터를 월별로 리샘플링
                            monthly_data = data[ticker].resample('ME').last()
                            # 월간 수익률 계산
                            monthly_returns = monthly_data.pct_change().dropna()
                            
                            if len(monthly_returns) == 0:
                                st.warning("월간 수익률을 계산할 수 있는 충분한 데이터가 없습니다.")
                                monthly_returns = pd.Series(dtype=float)
                        except Exception as e:
                            st.warning(f"월간 수익률 계산 중 오류 발생: {str(e)}")
                            # 대체 방법: 일간 수익률을 월별로 집계
                            try:
                                # 일간 수익률에 날짜 인덱스의 연-월을 기준으로 그룹화하여 집계
                                monthly_returns = returns[ticker].groupby(
                                    returns[ticker].index.to_period('ME')
                                ).apply(
                                    lambda x: (1 + x).prod() - 1
                                ).dropna()
                            except Exception as sub_e:
                                st.error(f"대체 월간 수익률 계산 중 오류 발생: {str(sub_e)}")
                                monthly_returns = pd.Series(dtype=float)
                        
                        # 성과 지표 표시
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric(
                                "누적 수익률",
                                f"{cumulative_returns.iloc[-1]:.2%}"
                            )
                            st.metric(
                                "양의 수익률 일수",
                                f"{(returns[ticker] > 0).sum()}/{len(returns[ticker].dropna())}"
                            )
                        with col2:
                            st.metric("연간화 수익률", f"{annual_return:.2%}")
                            if len(monthly_returns) > 0:
                                st.metric(
                                    "월간 평균 수익률",
                                    f"{monthly_returns.mean():.2%}"
                                )
                            else:
                                st.metric("월간 평균 수익률", "N/A")
                        with col3:
                            st.metric(
                                "최대 일간 상승",
                                f"{returns[ticker].max():.2%}"
                            )
                            if len(monthly_returns) > 0:
                                st.metric(
                                    "최대 월간 상승",
                                    f"{monthly_returns.max():.2%}"
                                )
                            else:
                                st.metric("최대 월간 상승", "N/A")
                        with col4:
                            st.metric(
                                "최대 일간 하락",
                                f"{returns[ticker].min():.2%}"
                            )
                            if len(monthly_returns) > 0:
                                st.metric(
                                    "최대 월간 하락",
                                    f"{monthly_returns.min():.2%}"
                                )
                            else:
                                st.metric("최대 월간 하락", "N/A")
                        
                        # 성과 시각화
                        
                        # 1. 누적 수익률 그래프
                        fig_cum = go.Figure()
                        fig_cum.add_trace(go.Scatter(
                            x=cumulative_returns.index,
                            y=cumulative_returns,
                            mode='lines',
                            name='누적 수익률',
                            line=dict(color='#1f77b4', width=2)
                        ))
                        fig_cum.update_layout(
                            title=f"{ticker} 누적 수익률",
                            xaxis_title="날짜",
                            yaxis_title="누적 수익률",
                            yaxis_tickformat='.1%',
                            hovermode='x unified'
                        )
                        st.plotly_chart(fig_cum)
                        
                        # 2. 월간 수익률 바 차트
                        if len(monthly_returns) > 0:
                            try:
                                fig_monthly = go.Figure()
                                fig_monthly.add_trace(go.Bar(
                                    x=monthly_returns.index,
                                    y=monthly_returns,
                                    name='월간 수익률',
                                    marker_color=monthly_returns.apply(lambda x: '#2ca02c' if x > 0 else '#d62728')
                                ))
                                fig_monthly.update_layout(
                                    title=f"{ticker} 월간 수익률",
                                    xaxis_title="월",
                                    yaxis_title="수익률",
                                    yaxis_tickformat='.1%',
                                    hovermode='x unified'
                                )
                                st.plotly_chart(fig_monthly)
                            except Exception as e:
                                st.warning(f"월간 수익률 차트 생성 중 오류 발생: {str(e)}")
                        
                        # 3. 롤링 윈도우 성과 지표
                        if len(returns[ticker].dropna()) > 20:  # 충분한 데이터가 있는 경우에만
                            # 롤링 윈도우 계산 (20일, 60일)
                            rolling_returns = returns[ticker].dropna()
                            rolling_20d = rolling_returns.rolling(window=20).mean() * 20
                            rolling_60d = rolling_returns.rolling(window=60).mean() * 60
                            
                            fig_rolling = go.Figure()
                            fig_rolling.add_trace(go.Scatter(
                                x=rolling_20d.index,
                                y=rolling_20d,
                                mode='lines',
                                name='20일 롤링 수익률',
                                line=dict(color='#ff7f0e', width=2)
                            ))
                            fig_rolling.add_trace(go.Scatter(
                                x=rolling_60d.index,
                                y=rolling_60d,
                                mode='lines',
                                name='60일 롤링 수익률',
                                line=dict(color='#9467bd', width=2)
                            ))
                            fig_rolling.update_layout(
                                title=f"{ticker} 롤링 윈도우 수익률",
                                xaxis_title="날짜",
                                yaxis_title="연율화 수익률",
                                yaxis_tickformat='.1%',
                                hovermode='x unified'
                            )
                            st.plotly_chart(fig_rolling)
                    
                    except Exception as e:
                        st.error(f"{ticker}의 리스크 지표 계산 중 오류 발생: {str(e)}")
                
                except Exception as e:
                    st.error(f"{ticker}의 리스크 지표 계산 중 오류 발생: {str(e)}")
            
            except Exception as e:
                st.error(f"{ticker} 처리 중 오류 발생: {str(e)}")
                continue
    
    except Exception as e:
        st.error(f"리스크 분석 중 예상치 못한 오류 발생: {str(e)}")
