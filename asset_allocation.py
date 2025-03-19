import streamlit as st
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
import plotly.graph_objects as go
from datetime import datetime, timedelta
from optimization import (
    optimize_minimum_variance,
    optimize_risk_parity,
    optimize_markowitz
)

def portfolio_stats(weights, returns):
    """포트폴리오 통계 계산"""
    portfolio_return = np.sum(returns.mean() * weights) * 252
    portfolio_vol = np.sqrt(
        np.dot(weights.T, np.dot(returns.cov() * 252, weights))
    )
    sharpe_ratio = portfolio_return / portfolio_vol
    return portfolio_return, portfolio_vol, sharpe_ratio

def optimize_portfolio(returns, method='markowitz'):
    """최적화 로직 개선"""
    n_assets = returns.shape[1]
    
    optimization_methods = {
        'equal_weight': lambda: np.array([1/n_assets] * n_assets),
        'minimum_variance': lambda: optimize_minimum_variance(returns),
        'risk_parity': lambda: optimize_risk_parity(returns),
        'markowitz': lambda: optimize_markowitz(returns)
    }
    
    if method not in optimization_methods:
        raise ValueError(f"지원하지 않는 최적화 방법: {method}")
        
    return optimization_methods[method]()

def get_strategy_description(method):
    """투자 전략 설명을 반환"""
    descriptions = {
        "마코위츠 최적화": """
        📈 현대 포트폴리오 이론의 기초가 되는 방법
        - 주어진 리스크 수준에서 최대 수익률 추구
        - 샤프 비율(위험 대비 수익률) 최적화
        - 과거 데이터 기반 최적화
        
        💡 특징:
        - 분산투자 효과 극대화
        - 리스크와 수익의 균형 추구
        """,
        
        "최소분산 포트폴리오": """
        🛡️ 가장 안정적인 포트폴리오 구성 추구
        - 전체 포트폴리오의 변동성 최소화
        - 수익률보다 안정성에 초점
        
        💡 특징:
        - 보수적인 투자 전략
        - 변동성이 낮은 자산 선호
        """,
        
        "리스크 패리티": """
        ⚖️ 위험 기여도를 균등하게 분배
        - 각 자산의 리스크 기여도를 동일하게 조정
        - 변동성이 높은 자산의 비중 감소
        
        💡 특징:
        - 리스크 분산 효과 극대화
        - 안정적인 성과 추구
        """,
        
        "등가중 포트폴리오": """
        🎯 단순하고 직관적인 방식
        - 모든 자산에 동일한 비중 배분
        - 1/N 전략이라고도 함
        
        💡 특징:
        - 단순하고 투명한 전략
        - 정기적인 리밸런싱 필요
        """
    }
    return descriptions.get(method, "설명이 없습니다.")

def show_asset_allocation():
    """자산 배분 최적화 UI 표시"""
    st.header("최적 자산 배분")
    
    # 자산 입력 받기
    assets_input = st.text_input(
        "분석할 종목코드를 입력하세요 (예: 005930, 000660)",
        value="005930, 000660"
    )
    
    # 입력값 처리
    assets = [code.strip() for code in assets_input.split(',') if code.strip()]
    
    if len(assets) < 2:
        st.warning("최소 2개 이상의 자산을 입력해주세요.")
        return
        
    # 입력된 종목코드 확인
    st.write("선택된 종목코드:", ", ".join(assets))
    
    # 기간 설정
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "시작일",
            datetime.now() - timedelta(days=365)
        )
    with col2:
        end_date = st.date_input("종료일", datetime.now())
    
    # 데이터 가져오기
    data = pd.DataFrame()
    for asset in assets:
        try:
            stock_data = fdr.DataReader(asset, start_date, end_date)
            if stock_data.empty:
                st.error(f"{asset}에 대한 데이터가 없습니다.")
                return
            data[asset] = stock_data['Close']
        except Exception as e:
            st.error(f"{asset} 데이터 로드 중 오류 발생: {e}")
            return
    
    # 수익률 계산
    returns = data.pct_change().dropna()
    
    # 사이드바 설정
    with st.sidebar:
        st.subheader("최적화 설정")
        optimization_method = st.selectbox(
            "최적화 방법",
            ["마코위츠 최적화", "최소분산 포트폴리오", "리스크 패리티", "등가중 포트폴리오"]
        )
        
        # 선택된 전략 설명 표시
        st.markdown("---")
        st.subheader("📌 전략 설명")
        st.markdown(get_strategy_description(optimization_method))
    
    method_map = {
        "마코위츠 최적화": "markowitz",
        "최소분산 포트폴리오": "minimum_variance",
        "리스크 패리티": "risk_parity",
        "등가중 포트폴리오": "equal_weight"
    }
    
    try:
        weights = optimize_portfolio(
            returns,
            method=method_map[optimization_method]
        )
        
        # 결과 표시
        st.subheader("최적 자산 배분 비율")
        
        # 파이 차트로 시각화
        fig = go.Figure(data=[go.Pie(
            labels=assets,
            values=weights,
            textinfo='percent+label'
        )])
        st.plotly_chart(fig)
        
        # 포트폴리오 통계
        port_return, port_vol, sharpe = portfolio_stats(weights, returns)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("예상 연간 수익률", f"{port_return:.2%}")
        with col2:
            st.metric("연간 변동성", f"{port_vol:.2%}")
        with col3:
            st.metric("Sharpe Ratio", f"{sharpe:.2f}")
            
    except Exception as e:
        st.error(f"포트폴리오 최적화 중 오류 발생: {str(e)}") 
