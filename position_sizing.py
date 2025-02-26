import streamlit as st
import requests
from datetime import datetime
from typing import Dict, Tuple
from dataclasses import dataclass

def get_exchange_rate() -> Tuple[float, str]:
    """
    실시간 달러/원 환율 정보를 가져오는 함수
    기본값으로 1,350원을 사용하고, API 호출에 실패하면 기본값을 반환
    """
    try:
        # 환율 정보 API 호출 (예: 공개 API)
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=5)
        data = response.json()
        usd_krw = data["rates"]["KRW"]
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return usd_krw, last_updated
    except Exception as e:
        st.warning(
            f"환율 정보를 가져오는데 실패했습니다. 기본 환율(1,350원)을 사용합니다. 오류: {e}"
        )
        return 1350.0, "N/A"

@dataclass
class PositionSizeConfig:
    """포지션 사이징 설정"""
    max_position_size: float  # 단일 포지션 최대 비중
    risk_per_trade: float    # 거래당 리스크 비율
    account_size_usd: float  # 계좌 크기 (USD)
    exchange_rate: float     # USD/KRW 환율
    
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
            entry_price: 진입가격 (USD)
            stop_loss: 손절가격 (USD)
            risk_multiple: 리스크 배수 (기본값: 1.0)
            
        Returns:
            Dict containing:
                - quantity: 수량
                - position_value_usd: 포지션 가치 (USD)
                - position_value_krw: 포지션 가치 (KRW)
                - risk_amount_usd: 리스크 금액 (USD)
                - risk_amount_krw: 리스크 금액 (KRW)
        """
        risk_per_trade = self.config.account_size_usd * self.config.risk_per_trade
        risk_amount_usd = risk_per_trade * risk_multiple
        
        # 주당 리스크
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share == 0:
            raise ValueError("진입가와 손절가가 동일합니다")
            
        # 수량 계산
        quantity = risk_amount_usd / risk_per_share
        position_value_usd = quantity * entry_price
        
        # 최대 포지션 사이즈 제한 적용
        max_position_value = self.config.account_size_usd * self.config.max_position_size
        if position_value_usd > max_position_value:
            quantity = max_position_value / entry_price
            position_value_usd = quantity * entry_price
            risk_amount_usd = quantity * risk_per_share
            
        # 원화 환산
        position_value_krw = position_value_usd * self.config.exchange_rate
        risk_amount_krw = risk_amount_usd * self.config.exchange_rate
            
        return {
            "quantity": quantity,
            "position_value_usd": position_value_usd,
            "position_value_krw": position_value_krw,
            "risk_amount_usd": risk_amount_usd,
            "risk_amount_krw": risk_amount_krw
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
    
    # 환율 정보 가져오기
    default_usd_krw, exchange_rate_updated = get_exchange_rate()
    
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
        
        st.markdown("---")
        
        # 환율 정보 표시 및 수정 기능
        st.markdown("### 💱 환율 설정")
        col1, col2 = st.columns([3, 2])
        
        with col1:
            usd_krw = st.number_input(
                "USD/KRW 환율",
                min_value=900.0,
                max_value=2000.0,
                value=default_usd_krw,
                step=0.5,
                format="%.2f"
            )
        
        with col2:
            st.markdown(f"<small>마지막 업데이트:<br>{exchange_rate_updated}</small>", unsafe_allow_html=True)
            if st.button("기본값 사용", key="reset_exchange_rate"):
                usd_krw = default_usd_krw
                st.rerun()
    
    # 계좌 설정
    st.subheader("계좌 설정")
    col1, col2 = st.columns(2)
    
    with col1:
        account_size_usd = st.number_input(
            "계좌 크기 (USD)",
            min_value=0,
            value=10000,
            step=1000,
            format="%d"
        )
        st.metric("원화 환산 금액", f"{account_size_usd * usd_krw:,.0f}원")
    
    with col2:
        col2_1, col2_2 = st.columns(2)
        with col2_1:
            risk_per_trade = st.number_input(
                "거래당 리스크 (%)",
                min_value=0.1,
                max_value=10.0,
                value=1.0,
                step=0.1
            ) / 100
        
        with col2_2:
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
            "진입 가격 (USD)",
            min_value=0.0,
            value=100.0,
            step=1.0
        )
        st.caption(f"≈ {entry_price * usd_krw:,.0f}원")
    
    with col2:
        stop_loss = st.number_input(
            "손절 가격 (USD)",
            min_value=0.0,
            value=90.0,
            step=1.0
        )
        st.caption(f"≈ {stop_loss * usd_krw:,.0f}원")
    
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
        account_size_usd=account_size_usd,
        exchange_rate=usd_krw
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
        
        # 매매 수량과 투자금액 정보
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "매매 수량",
                f"{result['quantity']:.2f} 주"
            )
        
        with col2:
            st.metric(
                "포지션 비중",
                f"{result['position_value_usd']/account_size_usd:.1%}",
                f"계좌의 {max_position_size*100:.0f}% 제한 중"
            )
        
        # 포지션 금액 정보
        st.markdown("### 투자 금액")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "달러 ($)",
                f"${result['position_value_usd']:,.2f}"
            )
        
        with col2:
            st.metric(
                "원화 기본",
                f"{result['position_value_krw']:,.0f}원"
            )
            
        with col3:
            # 환율 변동 시나리오
            st.metric(
                "환율 5% 상승 시",
                f"{result['position_value_usd'] * usd_krw * 1.05:,.0f}원"
            )
        
        # 리스크 금액 정보
        st.markdown("### 리스크 금액")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "달러 ($)",
                f"${result['risk_amount_usd']:,.2f}",
                f"계좌의 {result['risk_amount_usd']/account_size_usd:.1%}"
            )
        
        with col2:
            st.metric(
                "원화 기본",
                f"{result['risk_amount_krw']:,.0f}원"
            )
            
        with col3:
            # 환율 변동 시나리오
            st.metric(
                "환율 5% 상승 시",
                f"{result['risk_amount_usd'] * usd_krw * 1.05:,.0f}원"
            )
        
        # 환율 변동 관련 안내
        st.info("""
        💱 **환율 변동 리스크 참고 사항**
        
        해외 자산 거래 시 환율 변동에 따라 실제 원화 손익이 달라질 수 있습니다.
        투자 결정 시 환율 변동성을 고려해주세요.
        """)
            
    except Exception as e:
        st.error(f"계산 중 오류 발생: {str(e)}") 
