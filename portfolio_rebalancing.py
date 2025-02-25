import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from typing import Dict, List, Tuple

class PortfolioRebalancer:
    def __init__(self, initial_weights: Dict[str, float], threshold: float = 0.05):
        """
        포트폴리오 리밸런싱 클래스
        
        Args:
            initial_weights: 초기 포트폴리오 비중
            threshold: 리밸런싱 발동 임계값 (기본값: 5%)
        """
        self.target_weights = initial_weights
        self.threshold = threshold
        
    def calculate_current_weights(self, positions: Dict[str, Tuple[float, float]]) -> Dict[str, float]:
        """
        현재 포트폴리오 비중 계산
        
        Args:
            positions: {자산: (수량, 현재가격)} 형태의 딕셔너리
        """
        total_value = sum(qty * price for qty, price in positions.values())
        return {
            asset: (qty * price) / total_value 
            for asset, (qty, price) in positions.items()
        }
    
    def needs_rebalancing(self, current_weights: Dict[str, float]) -> bool:
        """리밸런싱 필요 여부 확인"""
        return any(
            abs(current_weights.get(asset, 0) - target) > self.threshold
            for asset, target in self.target_weights.items()
        )
    
    def calculate_trades(
        self, 
        positions: Dict[str, Tuple[float, float]], 
        cash: float
    ) -> Dict[str, float]:
        """
        필요한 매매 수량 계산
        
        Args:
            positions: 현재 포지션
            cash: 사용 가능한 현금
            
        Returns:
            자산별 매매 수량 (양수: 매수, 음수: 매도)
        """
        current_weights = self.calculate_current_weights(positions)
        total_value = sum(qty * price for qty, price in positions.values()) + cash
        
        trades = {}
        for asset, (qty, price) in positions.items():
            target_value = total_value * self.target_weights.get(asset, 0)
            current_value = qty * price
            value_difference = target_value - current_value
            trades[asset] = value_difference / price
            
        return trades

def get_rebalancing_description(method: str) -> str:
    """리밸런싱 방법에 대한 설명 반환"""
    descriptions = {
        "임계값 기반": """
        📊 임계값 기반 리밸런싱
        
        💡 작동 방식:
        - 자산 비중이 목표 비중에서 설정된 임계값 이상 벗어나면 리밸런싱
        - 시장 상황에 따라 유연하게 대응
        
        ✨ 장점:
        - 불필요한 거래 비용 최소화
        - 시장 변화에 효율적 대응
        - 포트폴리오 변동성 관리
        """,
        
        "정기 리밸런싱": """
        📅 정기 리밸런싱
        
        💡 작동 방식:
        - 정해진 주기(월별, 분기별 등)로 리밸런싱 실행
        - 목표 비중으로 정기적 조정
        
        ✨ 장점:
        - 규칙적이고 체계적인 관리
        - 감정적 거래 방지
        - 운영의 단순성
        """,
        
        "복합 방식": """
        🔄 복합 리밸런싱
        
        💡 작동 방식:
        - 정기 리밸런싱 + 임계값 기반 리밸런싱
        - 정기 점검과 임계값 모니터링 병행
        
        ✨ 장점:
        - 두 방식의 장점 결합
        - 더 섬세한 포트폴리오 관리
        - 리스크 관리 강화
        """
    }
    return descriptions.get(method, "설명이 없습니다.")

def show_portfolio_rebalancing():
    st.header("포트폴리오 리밸런싱")
    
    # 사이드바에 리밸런싱 설명 추가
    with st.sidebar:
        st.markdown("""
            ### 📚 리밸런싱이란?
            포트폴리오의 자산 비중을 목표 비중으로 
            재조정하는 과정입니다.
            
            ### 🎯 목적
            - 위험 관리
            - 수익 실현
            - 포트폴리오 건전성 유지
        """)
        
        st.markdown("---")
        
        rebalancing_method = st.selectbox(
            "리밸런싱 방식",
            ["임계값 기반", "정기 리밸런싱", "복합 방식"]
        )
        
        st.markdown("### 📌 선택한 방식 설명")
        st.markdown(get_rebalancing_description(rebalancing_method))
    
    # 리밸런싱 설정
    st.subheader("리밸런싱 설정")
    col1, col2 = st.columns(2)
    with col1:
        threshold = st.slider(
            "리밸런싱 임계값 (%)", 
            min_value=1, 
            max_value=20, 
            value=5
        ) / 100
    
    with col2:
        if rebalancing_method in ["정기 리밸런싱", "복합 방식"]:
            rebalancing_period = st.selectbox(
                "정기 리밸런싱 주기",
                ["월별", "분기별", "반기별", "연간"]
            )
    
    # 포트폴리오 입력
    st.subheader("현재 포트폴리오")
    
    # 자산 추가 기능
    with st.expander("자산 추가"):
        col1, col2, col3 = st.columns(3)
        with col1:
            asset = st.text_input("자산 코드")
        with col2:
            quantity = st.number_input("보유 수량", min_value=0.0)
        with col3:
            price = st.number_input("현재 가격", min_value=0.0)
            
        if st.button("자산 추가") and asset and quantity > 0 and price > 0:
            if 'positions' not in st.session_state:
                st.session_state.positions = {}
            st.session_state.positions[asset] = (quantity, price)
    
    # 현재 포트폴리오 표시
    if 'positions' in st.session_state and st.session_state.positions:
        portfolio_df = pd.DataFrame([
            {
                '자산': asset,
                '수량': qty,
                '현재가': price,
                '평가금액': qty * price
            }
            for asset, (qty, price) in st.session_state.positions.items()
        ])
        
        total_value = portfolio_df['평가금액'].sum()
        portfolio_df['비중'] = portfolio_df['평가금액'] / total_value
        
        st.dataframe(portfolio_df.style.format({
            '수량': '{:.2f}',
            '현재가': '{:,.0f}',
            '평가금액': '{:,.0f}',
            '비중': '{:.1%}'
        }))
        
        # 리밸런싱 분석
        st.subheader("리밸런싱 분석")
        
        # 목표 비중 설정
        target_weights = {}
        cols = st.columns(len(st.session_state.positions))
        for i, asset in enumerate(st.session_state.positions.keys()):
            with cols[i]:
                target_weights[asset] = st.number_input(
                    f"{asset} 목표비중 (%)",
                    min_value=0,
                    max_value=100,
                    value=int(100 / len(st.session_state.positions))
                ) / 100
        
        if abs(sum(target_weights.values()) - 1) > 0.0001:
            st.error("목표 비중의 합이 100%가 되어야 합니다.")
            return
            
        # 리밸런서 초기화 및 분석
        rebalancer = PortfolioRebalancer(target_weights, threshold)
        trades = rebalancer.calculate_trades(
            st.session_state.positions,
            cash=0  # 현금 입력 필드 추가 가능
        )
        
        # 리밸런싱 결과 표시
        st.subheader("필요한 리밸런싱 거래")
        trades_df = pd.DataFrame([
            {
                '자산': asset,
                '거래수량': qty,
                '예상금액': qty * st.session_state.positions[asset][1]
            }
            for asset, qty in trades.items()
            if abs(qty) > 0.000001  # 미미한 거래는 제외
        ])
        
        if not trades_df.empty:
            trades_df['거래유형'] = trades_df['거래수량'].apply(
                lambda x: '매수' if x > 0 else '매도'
            )
            st.dataframe(trades_df.style.format({
                '거래수량': '{:+.2f}',
                '예상금액': '{:+,.0f}'
            }))
        else:
            st.info("현재 리밸런싱이 필요하지 않습니다.") 
