import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

@st.cache_data(ttl=3600)  # 1시간 캐시
def fetch_stock_data(ticker, start_date, end_date):
    """주식 데이터 가져오기 (캐시 적용)"""
    try:
        stock = yf.download(ticker, start=start_date, end=end_date)
        return stock['Close'] if not stock.empty else None
    except Exception as e:
        st.error(f"{ticker} 데이터 로드 실패: {str(e)}")
        return None

def calculate_portfolio_value(data, weights):
    """벡터화된 포트폴리오 가치 계산"""
    returns = data.pct_change()
    weighted_returns = (returns * pd.Series(weights)).sum(axis=1)
    return (1 + weighted_returns).cumprod()

def calculate_metrics(returns):
    annual_return = returns.mean() * 252
    annual_vol = returns.std() * np.sqrt(252)
    sharpe_ratio = annual_return / annual_vol
    
    # Maximum Drawdown
    cum_returns = (1 + returns).cumprod()
    rolling_max = cum_returns.expanding().max()
    drawdowns = cum_returns/rolling_max - 1
    max_drawdown = drawdowns.min()
    
    return {
        "연간 수익률": annual_return,
        "연간 변동성": annual_vol,
        "Sharpe Ratio": sharpe_ratio,
        "Maximum Drawdown": max_drawdown
    }

def show_backtesting():
    st.header("포트폴리오 백테스팅")
    
    # 자산 선택 입력 방식 변경
    assets_input = st.text_input(
        "테스트할 자산의 티커를 입력하세요 (쉼표로 구분, 예: 005930.KS,035720.KS)",
        value="005930.KS"
    )
    assets = [ticker.strip() for ticker in assets_input.split(',') if ticker.strip()]
    
    if not assets:
        st.warning("자산을 입력해주세요.")
        return
    
    weights = {}
    st.subheader("자산 비중 설정")
    total_weight = 0
    
    cols = st.columns(len(assets))
    for i, asset in enumerate(assets):
        with cols[i]:
            weight = st.number_input(
                f"{asset} 비중 (%)",
                min_value=0,
                max_value=100,
                value=100 // len(assets),
                step=5
            )
            weights[asset] = weight / 100
            total_weight += weight
    
    if abs(total_weight - 100) > 0.01:
        st.error("전체 비중의 합이 100%가 되어야 합니다.")
        return
    
    # 기간 설정
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "백테스트 시작일",
            datetime.now() - timedelta(days=365)
        )
    with col2:
        end_date = st.date_input("백테스트 종료일", datetime.now())
    
    # 데이터 가져오기
    data = pd.DataFrame()
    for asset in assets:
        try:
            stock_data = fetch_stock_data(asset, start_date, end_date)
            if stock_data is not None:
                data[asset] = stock_data
        except Exception as e:
            st.error(f"{asset} 데이터를 가져오는데 실패했습니다: {str(e)}")
            return
    
    # 포트폴리오 가치 계산
    portfolio_value = calculate_portfolio_value(data, weights)
    
    # 결과 시각화
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=portfolio_value.index,
        y=portfolio_value.values,
        mode='lines',
        name='Portfolio Value'
    ))
    fig.update_layout(title="포트폴리오 가치 변화")
    st.plotly_chart(fig)
    
    # 성과 지표 계산
    portfolio_returns = portfolio_value.pct_change().dropna()
    metrics = calculate_metrics(portfolio_returns)
    
    # 성과 지표 표시
    cols = st.columns(4)
    for i, (metric, value) in enumerate(metrics.items()):
        with cols[i]:
            st.metric(metric, f"{value:.2%}")
    
    # 월별 수익률 히트맵
    monthly_returns = portfolio_returns.resample('M').apply(
        lambda x: (1 + x).prod() - 1
    )
    monthly_returns_matrix = monthly_returns.groupby(
        [monthly_returns.index.year, monthly_returns.index.month]
    ).first().unstack()
    
    st.subheader("월별 수익률 히트맵")
    fig = go.Figure(data=go.Heatmap(
        z=monthly_returns_matrix.values,
        x=monthly_returns_matrix.columns,
        y=monthly_returns_matrix.index,
        colorscale='RdYlGn'
    ))
    fig.update_layout(
        title="월별 수익률 히트맵",
        xaxis_title="월",
        yaxis_title="년"
    )
    st.plotly_chart(fig) 
