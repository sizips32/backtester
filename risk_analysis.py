import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
from services.data_service import data_service

# 데이터베이스 및 리포지토리 import
from utils.database import get_db
from repository.portfolio_repo import get_all_portfolios, get_portfolio_by_id
from repository.target_weights_repo import get_portfolio_target_weights
from repository.holdings_repo import get_portfolio_holdings

# 상수 정의
# NOTE: 이 설정들은 config/app_config.py로 통합될 예정입니다
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
    """Sortino ratio using downside deviation for daily returns."""
    try:
        returns = returns.dropna()
        if len(returns) < 2:
            return 0

        # Convert to excess daily returns so annualised figures are consistent with Sharpe.
        excess_daily_returns = returns - (risk_free_rate / 252)
        downside_returns = excess_daily_returns[excess_daily_returns < 0]
        if downside_returns.empty:
            return 0

        annualised_excess_return = excess_daily_returns.mean() * 252
        downside_deviation = downside_returns.std() * np.sqrt(252)
        if downside_deviation == 0:
            return 0

        return annualised_excess_return / downside_deviation
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
    st.header("리스크 분석")

    # 탭 생성: 저장된 포트폴리오별 + 수동 입력
    tab1, tab2 = st.tabs(["📁 저장된 포트폴리오", "✏️ 수동 입력"])

    with tab1:
        show_saved_portfolio_risk_analysis()

    with tab2:
        show_manual_risk_analysis()

def show_saved_portfolio_risk_analysis():
    """저장된 포트폴리오별 리스크 분석"""
    st.subheader("저장된 포트폴리오 리스크 분석")
    
    # 포트폴리오 목록 새로고침 버튼
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 목록 새로고침", help="포트폴리오 목록을 새로고침합니다", key="risk_refresh"):
            st.rerun()

    # 저장된 포트폴리오 목록 가져오기
    db = next(get_db())
    try:
        portfolios = get_all_portfolios(db)

        # 목표 비중 또는 보유 종목이 있는 포트폴리오만 필터링
        portfolios_with_data = []
        for portfolio in portfolios:
            weights = get_portfolio_target_weights(db, portfolio.id)
            holdings = get_portfolio_holdings(db, portfolio.id)

            if weights or holdings:
                # 종목 목록 생성 (목표 비중 우선, 없으면 보유 종목)
                symbols = list(weights.keys()) if weights else [h.symbol for h in holdings]
                portfolios_with_data.append({
                    'id': portfolio.id,
                    'name': portfolio.name,
                    'description': portfolio.description,
                    'symbols': symbols,
                    'weights': weights,
                    'holdings': holdings
                })
    finally:
        db.close()

    if not portfolios_with_data:
        st.warning("리스크 분석할 수 있는 포트폴리오가 없습니다. 포트폴리오 관리에서 목표 비중을 설정하거나 종목을 추가해주세요.")
        return

    # 포트폴리오 선택
    portfolio_names = [p['name'] for p in portfolios_with_data]
    selected_portfolio_name = st.selectbox(
        "리스크 분석할 포트폴리오를 선택하세요:",
        portfolio_names,
        key="risk_portfolio_selector"
    )

    if not selected_portfolio_name:
        st.stop()

    # 선택된 포트폴리오 정보 가져오기
    selected_portfolio = next(p for p in portfolios_with_data if p['name'] == selected_portfolio_name)
    symbols = selected_portfolio['symbols']

    # 포트폴리오 정보 표시
    st.info(f"**포트폴리오**: {selected_portfolio['name']}")
    if selected_portfolio['description']:
        st.info(f"**설명**: {selected_portfolio['description']}")

    # 분석할 종목 목록 표시
    with st.expander("분석 종목 확인", expanded=False):
        st.write(f"**분석 대상 종목** ({len(symbols)}개):")
        for symbol in symbols:
            st.write(f"• {symbol}")

    # 기간 설정
    st.subheader("분석 설정")
    col1, col2 = st.columns(2)

    with col1:
        period = st.selectbox(
            "분석 기간",
            ["1개월", "3개월", "6개월", "1년", "3년", "5년"],
            index=3,
            key="saved_risk_period"
        )

    with col2:
        confidence_level = st.selectbox(
            "신뢰구간",
            [0.90, 0.95, 0.99],
            index=1,
            format_func=lambda x: f"{x*100:.0f}%",
            key="saved_risk_confidence"
        )

    period_days = {
        "1개월": 30, "3개월": 90, "6개월": 180,
        "1년": 365, "3년": 1095, "5년": 1825
    }

    # 기간 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days[period])

    # 포트폴리오 데이터 가져오기 및 리스크 분석
    if st.button("리스크 분석 실행", type="primary", use_container_width=True, key="saved_portfolio_risk_execute"):
        analyze_portfolio_risk(symbols, selected_portfolio['weights'], start_date, end_date, confidence_level, f"{selected_portfolio['name']} 포트폴리오")

def analyze_portfolio_risk(symbols, weights, start_date, end_date, confidence_level, portfolio_name):
    """포트폴리오 리스크 분석 실행"""
    st.subheader(f"{portfolio_name} 리스크 분석 결과")

    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # 1. 데이터 수집
        status_text.text("📊 데이터 수집 중...")
        progress_bar.progress(20)

        portfolio_data = pd.DataFrame()
        valid_symbols = []

        for i, symbol in enumerate(symbols):
            try:
                df = fetch_stock_data(symbol, start_date, end_date)
                if not df.empty:
                    portfolio_data[symbol] = df.iloc[:, 0]
                    valid_symbols.append(symbol)
                    st.success(f"✅ {symbol}: 데이터 수집 완료")
                else:
                    st.warning(f"⚠️ {symbol}: 데이터 없음")
            except Exception as e:
                st.error(f"❌ {symbol}: {str(e)}")

        if portfolio_data.empty:
            st.error("분석할 수 있는 데이터가 없습니다.")
            return

        progress_bar.progress(50)

        # 2. 수익률 계산
        status_text.text("📈 수익률 계산 중...")
        returns = portfolio_data.pct_change().dropna()

        # 포트폴리오 가중 수익률 계산 (가중치가 있는 경우)
        if weights and all(symbol in weights for symbol in valid_symbols):
            # 가중치 정규화
            total_weight = sum(weights[symbol] for symbol in valid_symbols)
            normalized_weights = {symbol: weights[symbol] / total_weight for symbol in valid_symbols}

            portfolio_returns = sum(returns[symbol] * normalized_weights[symbol] for symbol in valid_symbols)
            portfolio_returns = pd.Series(portfolio_returns, index=returns.index)
        else:
            # 동일 가중 포트폴리오
            portfolio_returns = returns.mean(axis=1)

        progress_bar.progress(70)

        # 3. 리스크 지표 계산
        status_text.text("🔍 리스크 지표 계산 중...")

        # 개별 종목 리스크 지표
        risk_metrics = []
        for symbol in valid_symbols:
            symbol_returns = returns[symbol]

            metrics = {
                '종목': symbol,
                '평균 수익률 (연)': symbol_returns.mean() * 252 * 100,
                '변동성 (연)': symbol_returns.std() * np.sqrt(252) * 100,
                'Sharpe Ratio': calculate_sharpe_ratio(symbol_returns),
                'Sortino Ratio': calculate_sortino_ratio(symbol_returns),
                f'VaR ({confidence_level*100:.0f}%)': calculate_var(symbol_returns, confidence_level) * 100,
                f'CVaR ({confidence_level*100:.0f}%)': calculate_cvar(symbol_returns, confidence_level) * 100
            }
            risk_metrics.append(metrics)

        # 포트폴리오 전체 리스크 지표
        portfolio_metrics = {
            '종목': f'{portfolio_name} (전체)',
            '평균 수익률 (연)': portfolio_returns.mean() * 252 * 100,
            '변동성 (연)': portfolio_returns.std() * np.sqrt(252) * 100,
            'Sharpe Ratio': calculate_sharpe_ratio(portfolio_returns),
            'Sortino Ratio': calculate_sortino_ratio(portfolio_returns),
            f'VaR ({confidence_level*100:.0f}%)': calculate_var(portfolio_returns, confidence_level) * 100,
            f'CVaR ({confidence_level*100:.0f}%)': calculate_cvar(portfolio_returns, confidence_level) * 100
        }
        risk_metrics.append(portfolio_metrics)

        progress_bar.progress(90)

        # 4. 결과 표시
        status_text.text("📋 결과 표시 중...")

        # 리스크 지표 테이블
        risk_df = pd.DataFrame(risk_metrics)
        st.dataframe(risk_df.style.format({
            '평균 수익률 (연)': '{:.2f}%',
            '변동성 (연)': '{:.2f}%',
            'Sharpe Ratio': '{:.3f}',
            'Sortino Ratio': '{:.3f}',
            f'VaR ({confidence_level*100:.0f}%)': '{:.2f}%',
            f'CVaR ({confidence_level*100:.0f}%)': '{:.2f}%'
        }), use_container_width=True)

        # 누적 수익률 차트
        cumulative_returns = (1 + returns).cumprod() - 1
        portfolio_cumulative = (1 + portfolio_returns).cumprod() - 1

        fig = go.Figure()

        # 개별 종목
        for symbol in valid_symbols:
            fig.add_trace(go.Scatter(
                x=cumulative_returns.index,
                y=cumulative_returns[symbol] * 100,
                mode='lines',
                name=symbol,
                opacity=0.7
            ))

        # 포트폴리오 전체
        fig.add_trace(go.Scatter(
            x=portfolio_cumulative.index,
            y=portfolio_cumulative * 100,
            mode='lines',
            name=f'{portfolio_name} (전체)',
            line=dict(width=3, color='red')
        ))

        fig.update_layout(
            title=f"{portfolio_name} 누적 수익률",
            xaxis_title="날짜",
            yaxis_title="누적 수익률 (%)",
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)

        progress_bar.progress(100)
        status_text.text("✅ 분석 완료!")

        # 분석 요약
        st.subheader("분석 요약")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("포트폴리오 연평균 수익률", f"{portfolio_metrics['평균 수익률 (연)']:.2f}%")

        with col2:
            st.metric("포트폴리오 연변동성", f"{portfolio_metrics['변동성 (연)']:.2f}%")

        with col3:
            st.metric("포트폴리오 Sharpe Ratio", f"{portfolio_metrics['Sharpe Ratio']:.3f}")

    except Exception as e:
        st.error(f"분석 중 오류 발생: {str(e)}")
    finally:
        progress_bar.empty()
        status_text.empty()

def show_manual_risk_analysis():
    """수동 입력 리스크 분석 (기존 코드)"""
    try:
        
        # 사이드바에 기간 설정과 기준 시장 선택 추가
        with st.sidebar:
            st.subheader("기간 설정")
            period = st.selectbox(
                "분석 기간",
                ["1개월", "3개월", "6개월", "1년", "3년", "5년"],
                index=3,
                key="manual_risk_period"
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
                    "S&P500": "^GSPC",        # S&P 500
                    "KOSPI": "^KS11",         # KOSPI
                    "나스닥": "^IXIC",         # 나스닥 종합지수
                    "다우존스": "^DJI",        # 다우존스 산업평균
                    "상해종합": "000001.SS",   # 상해종합
                    "일본Nikkei": "^N225"     # 니케이225
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
