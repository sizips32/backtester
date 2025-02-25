import streamlit as st
import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class PositionSizeConfig:
    """포지션 사이징 설정"""
    max_position_size: float  # 단일 포지션 최대 비중
    risk_per_trade: float    # 거래당 리스크 비율
    account_size: float      # 계좌 크기
    
class PositionSizer:
    def __init__(self, config: PositionSizeConfig):
        self.config = config
        
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        risk_multiple: float = 1.0
    ) -> Dict[str, float]:
        """
        포지션 사이즈 계산
        
        Args:
            entry_price: 진입가격
            stop_loss: 손절가격
            risk_multiple: 리스크 배수 (기본값: 1.0)
            
        Returns:
            Dict containing:
                - quantity: 수량
                - position_value: 포지션 가치
                - risk_amount: 리스크 금액
        """
        risk_per_trade = self.config.account_size * self.config.risk_per_trade
        risk_amount = risk_per_trade * risk_multiple
        
        # 주당 리스크
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share == 0:
            raise ValueError("진입가와 손절가가 동일합니다")
            
        # 수량 계산
        quantity = risk_amount / risk_per_share
        position_value = quantity * entry_price
        
        # 최대 포지션 사이즈 제한 적용
        max_position_value = self.config.account_size * self.config.max_position_size
        if position_value > max_position_value:
            quantity = max_position_value / entry_price
            position_value = quantity * entry_price
            risk_amount = quantity * risk_per_share
            
        return {
            "quantity": quantity,
            "position_value": position_value,
            "risk_amount": risk_amount
        }

def get_sizing_description(method: str) -> str:
    """포지션 사이징 방법에 대한 설명 반환"""
    descriptions = {
        "고정 금액": """
        💵 고정 금액 방식
        
        💡 작동 방식:
        - 모든 거래에 동일한 금액 사용
        - 계좌 크기에 따라 금액 설정
        
        ✨ 장점:
        - 단순하고 명확한 관리
        - 리스크 통제 용이
        - 초보자에게 적합
        """,
        
        "고정 비율": """
        📊 고정 비율 방식
        
        💡 작동 방식:
        - 계좌의 일정 비율로 포지션 크기 결정
        - 복리 효과 활용
        
        ✨ 장점:
        - 계좌 크기에 따른 유연성
        - 자동적인 포지션 조절
        - 리스크 관리 효율성
        """,
        
        "리스크 기반": """
        ⚖️ 리스크 기반 방식
        
        💡 작동 방식:
        - 거래당 리스크 금액 기준
        - 손절가 위치에 따른 수량 조절
        
        ✨ 장점:
        - 정교한 리스크 관리
        - 변동성 고려
        - 전문적인 자금 관리
        """
    }
    return descriptions.get(method, "설명이 없습니다.")


def show_position_sizing():
    st.header("포지션 사이징 계산기")
    
    # 사이드바에 포지션 사이징 설명 추가
    with st.sidebar:
        st.markdown("""
            ### 📚 포지션 사이징이란?
            각 거래에서 투자할 적절한 금액을 
            결정하는 프로세스입니다.
            
            ### 🎯 목적
            - 리스크 관리
            - 자본금 보존
            - 수익 최적화
        """)
        
        st.markdown("---")
        
        sizing_method = st.selectbox(
            "사이징 방식",
            ["고정 금액", "고정 비율", "리스크 기반"]
        )
        
        st.markdown("### 📌 선택한 방식 설명")
        st.markdown(get_sizing_description(sizing_method))
    
    # 계좌 설정
    st.subheader("계좌 설정")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        account_size = st.number_input(
            "계좌 크기",
            min_value=0,
            value=10000000,
            step=1000000,
            format="%d"
        )
    
    with col2:
        risk_per_trade = st.number_input(
            "거래당 리스크 (%)",
            min_value=0.1,
            max_value=10.0,
            value=1.0,
            step=0.1
        ) / 100
    
    with col3:
        max_position_size = st.number_input(
            "최대 포지션 비중 (%)",
            min_value=1,
            max_value=100,
            value=20,
            step=1
        ) / 100
    
    # 거래 설정
    st.subheader("거래 설정")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        entry_price = st.number_input(
            "진입 가격",
            min_value=0.0,
            value=50000.0,
            step=1000.0
        )
    
    with col2:
        stop_loss = st.number_input(
            "손절 가격",
            min_value=0.0,
            value=45000.0,
            step=1000.0
        )
    
    with col3:
        risk_multiple = st.number_input(
            "리스크 배수",
            min_value=0.1,
            max_value=3.0,
            value=1.0,
            step=0.1
        )
    
    if entry_price <= 0 or stop_loss <= 0:
        st.error("가격은 0보다 커야 합니다")
        return
        
    if entry_price == stop_loss:
        st.error("진입가와 손절가가 다르게 설정되어야 합니다")
        return
        
    # 포지션 사이징 계산
    config = PositionSizeConfig(
        max_position_size=max_position_size,
        risk_per_trade=risk_per_trade,
        account_size=account_size
    )
    
    sizer = PositionSizer(config)
    
    try:
        result = sizer.calculate_position_size(
            entry_price=entry_price,
            stop_loss=stop_loss,
            risk_multiple=risk_multiple
        )
        
        # 결과 표시
        st.subheader("포지션 사이징 결과")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "매매 수량",
                f"{result['quantity']:.2f} 주"
            )
        
        with col2:
            st.metric(
                "포지션 크기",
                f"{result['position_value']:,.0f} 원",
                f"계좌의 {result['position_value']/account_size:.1%}"
            )
        
        with col3:
            st.metric(
                "리스크 금액",
                f"{result['risk_amount']:,.0f} 원",
                f"계좌의 {result['risk_amount']/account_size:.1%}"
            )
            
    except Exception as e:
        st.error(f"계산 중 오류 발생: {str(e)}") 
