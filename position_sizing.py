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
        
    def calculate_fixed_amount(
        self, 
        entry_price: float,
        fixed_amount_usd: float
    ) -> Dict[str, float]:
        """
        고정 금액 방식의 포지션 사이즈 계산
        
        Args:
            entry_price: 진입가격 (USD)
            fixed_amount_usd: 고정 투자 금액 (USD)
            
        Returns:
            Dict containing position details
        """
        # 최대 포지션 사이즈 제한 적용
        max_position_value = self.config.account_size_usd * self.config.max_position_size
        position_value_usd = min(fixed_amount_usd, max_position_value)
        
        # 수량 계산
        quantity = position_value_usd / entry_price
        
        # 원화 환산
        position_value_krw = position_value_usd * self.config.exchange_rate
        
        return {
            "quantity": quantity,
            "position_value_usd": position_value_usd,
            "position_value_krw": position_value_krw,
            "risk_amount_usd": 0,  # 손절가가 지정되지 않아 리스크 금액 확정 불가
            "risk_amount_krw": 0
        }
    
    def calculate_fixed_percent(
        self,
        entry_price: float,
        account_percent: float
    ) -> Dict[str, float]:
        """
        고정 비율 방식의 포지션 사이즈 계산
        
        Args:
            entry_price: 진입가격 (USD)
            account_percent: 계좌 대비 투자 비율 (0.0 ~ 1.0)
            
        Returns:
            Dict containing position details
        """
        # 포지션 크기 계산
        position_value_usd = self.config.account_size_usd * account_percent
        
        # 최대 포지션 사이즈 제한 적용
        max_position_value = self.config.account_size_usd * self.config.max_position_size
        position_value_usd = min(position_value_usd, max_position_value)
        
        # 수량 계산
        quantity = position_value_usd / entry_price
        
        # 원화 환산
        position_value_krw = position_value_usd * self.config.exchange_rate
        
        return {
            "quantity": quantity,
            "position_value_usd": position_value_usd,
            "position_value_krw": position_value_krw,
            "risk_amount_usd": 0,  # 손절가가 지정되지 않아 리스크 금액 확정 불가
            "risk_amount_krw": 0
        }
        
    def calculate_risk_based(
        self,
        entry_price: float,
        stop_loss: float,
        risk_multiple: float = 1.0
    ) -> Dict[str, float]:
        """
        리스크 기반 방식의 포지션 사이즈 계산
        
        Args:
            entry_price: 진입가격 (USD)
            stop_loss: 손절가격 (USD)
            risk_multiple: 리스크 배수 (기본값: 1.0)
            
        Returns:
            Dict containing position details
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
        max_value = self.config.account_size_usd * self.config.max_position_size
        if position_value_usd > max_value:
            quantity = max_value / entry_price
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

def get_sizing_usage_guide(method: str) -> str:
    """포지션 사이징 방법에 대한 사용 가이드 반환"""
    guides = {
        "고정 금액": """
        ### 📝 고정 금액 방식 사용법
        
        1. **고정 투자 금액** 설정: 모든 거래에 사용할 일정 금액을 입력합니다.
        2. **진입 가격** 입력: 매수 예정 가격을 입력합니다.
        3. **계산** 결과 확인: 설정한 금액으로 매수 가능한 수량과 비중이 계산됩니다.
        
        💡 **TIP**: 계좌 크기의 1~5% 사이의 금액을 권장합니다.
        """,
        
        "고정 비율": """
        ### 📝 고정 비율 방식 사용법
        
        1. **계좌 비율** 설정: 계좌 크기 대비 투자할 비율(%)을 입력합니다.
        2. **진입 가격** 입력: 매수 예정 가격을 입력합니다.
        3. **계산** 결과 확인: 계좌 비율에 따른 투자 금액과 가능한 수량이 계산됩니다.
        
        💡 **TIP**: 한 종목당 5~20% 비율을 초과하지 않는 것이 좋습니다.
        """,
        
        "리스크 기반": """
        ### 📝 리스크 기반 방식 사용법
        
        1. **거래당 리스크 비율(%)** 설정: 계좌에서 위험에 노출할 비율을 입력합니다.
        2. **진입 가격**과 **손절 가격** 입력: 매수 가격과 손절 가격을 모두 입력합니다.
        3. **리스크 배수** 조정: 기본 리스크의 몇 배로 설정할지 결정합니다.
        4. **계산** 결과 확인: 손절가 기준 리스크 금액에 따른 적정 수량이 계산됩니다.
        
        💡 **TIP**: 거래당 리스크는 보통 계좌의 1~2% 이내로 설정하는 것이 권장됩니다.
        """
    }
    return guides.get(method, "사용 가이드가 없습니다.")

def show_position_sizing():
    st.header("포지션 사이징 계산기")
    
    # 포트폴리오 사이징 가이드 expander 추가
    with st.expander("📚 포트폴리오 투자 시 사이징이란?", expanded=False):
        st.markdown("""
        # 포트폴리오 투자 시 사이징(Position Sizing)의 활용

        포트폴리오 투자 시 사이징은 여러분의 자금을 **얼마나, 어떻게 나눠서 투자할지** 결정하는 핵심 전략입니다. 간단히 말해, 여러분의 투자 자금을 어떻게 효율적으로 배분할지 결정하는 방법이에요.
        
        ## 포지션 사이징이 필요한 상황
        
        1. **다양한 종목에 투자할 때**
           - 여러 주식, ETF, 채권 등에 투자할 때 각각 얼마씩 투자할지 결정해야 합니다.
           - "애플에 100만원, 삼성전자에 50만원..." 이런 식으로요.
        
        2. **리스크 관리가 필요할 때**
           - 모든 돈을 한 종목에 투자하면 위험하죠? 사이징을 통해 위험을 분산합니다.
           - 한 종목이 폭락해도 전체 자산에 미치는 영향을 제한할 수 있어요.
        
        3. **장기 투자 계획을 세울 때**
           - 시간이 지나면서 자산 배분을 어떻게 조정할지 계획할 때 사용됩니다.
           - 예: "나이가 들수록 주식 비중은 줄이고 채권 비중은 늘리자"
        
        ## 포지션 사이징 방식별 활용법
        
        ### 1. 고정 금액 방식
        - **활용 상황**: 정기적으로 일정 금액을 투자할 때 (적립식 투자)
        - **예시**: 매월 급여에서 50만원씩 투자
        - **장점**: 계산이 단순하고, 초보자도 쉽게 실천 가능
        - **실생활 예**: "매달 주식형 펀드에 30만원, 채권형 펀드에 20만원씩 넣자"
        
        ### 2. 고정 비율 방식
        - **활용 상황**: 자산 클래스별 비중을 유지하고 싶을 때
        - **예시**: 포트폴리오의 60%는 주식, 30%는 채권, 10%는 현금
        - **장점**: 자산 가치 변동에 따라 자동으로 비율 조정 가능(리밸런싱)
        - **실생활 예**: "내 자산의 20%는 항상 기술주에 투자하고 싶어"
        
        ### 3. 리스크 기반 방식
        - **활용 상황**: 손실 위험을 정확히 제어하고 싶을 때
        - **예시**: 각 투자마다 총 자산의 1%만 위험에 노출
        - **장점**: 변동성이 큰 자산에 자동으로 적은 금액을 배분
        - **실생활 예**: "비트코인은 변동성이 크니 손실 가능성을 2%로 제한하자"
        
        ## 실제 활용 예시
        
        만약 1000만원의 투자금이 있다면:
        
        - **초보 투자자**: 고정 금액 방식으로 안정적인 ETF에 매달 100만원씩 투자
        - **중급 투자자**: 고정 비율 방식으로 주식 60%, 채권 30%, 금 10% 비율 유지
        - **전문 투자자**: 리스크 기반 방식으로 각 종목별 손실 위험을 1~2%로 제한
        
        ## 팁
        
        - 투자 경험이 적을수록 단순한 방식(고정 금액)으로 시작하세요.
        - 경험이 쌓이면 고정 비율 방식을 도입해 자산 비중을 관리하세요.
        - 리스크 관리 능력이 향상되면 리스크 기반 사이징을 시도해보세요.
        - 어떤 방식을 선택하든, 꾸준함이 가장 중요합니다!
        """)
    
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
        
        st.markdown("### 🔍 사용 가이드")
        st.markdown(get_sizing_usage_guide(sizing_method))
        
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
            st.markdown(f"<small>마지막 업데이트:<br>{exchange_rate_updated}</small>", 
                        unsafe_allow_html=True)
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
    
    # 거래 설정 (사이징 방식에 따라 다르게 표시)
    st.subheader(f"거래 설정 ({sizing_method})")
    
    # 방식에 따라 필요한 입력 필드 표시
    if sizing_method == "고정 금액":
        col1, col2 = st.columns(2)
        
        with col1:
            entry_price = st.number_input(
                "진입 가격 (USD)",
                min_value=0.01,
                value=100.0,
                step=1.0
            )
            st.caption(f"≈ {entry_price * usd_krw:,.0f}원")
        
        with col2:
            fixed_amount_percent = st.slider(
                "고정 투자 금액 (계좌 대비 %)",
                min_value=1.0,
                max_value=max_position_size * 100,
                value=5.0,
                step=0.5
            )
            fixed_amount_usd = account_size_usd * (fixed_amount_percent / 100)
            st.metric(
                "고정 투자 금액 (USD)",
                f"${fixed_amount_usd:,.2f}",
                f"계좌의 {fixed_amount_percent:.1f}%"
            )
            
    elif sizing_method == "고정 비율":
        col1, col2 = st.columns(2)
        
        with col1:
            entry_price = st.number_input(
                "진입 가격 (USD)",
                min_value=0.01,
                value=100.0,
                step=1.0
            )
            st.caption(f"≈ {entry_price * usd_krw:,.0f}원")
        
        with col2:
            account_percent = st.slider(
                "투자 비율 (계좌 대비 %)",
                min_value=1.0,
                max_value=max_position_size * 100,
                value=10.0,
                step=0.5
            ) / 100
            st.caption(f"최대 포지션 비중 {max_position_size*100:.0f}% 이내로 제한됩니다")
            
    else:  # 리스크 기반
        col1, col2, col3 = st.columns(3)
        
        with col1:
            entry_price = st.number_input(
                "진입 가격 (USD)",
                min_value=0.01,
                value=100.0,
                step=1.0
            )
            st.caption(f"≈ {entry_price * usd_krw:,.0f}원")
        
        with col2:
            stop_loss = st.number_input(
                "손절 가격 (USD)",
                min_value=0.01,
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
    
    if entry_price <= 0:
        st.error("가격은 0보다 커야 합니다")
        return
        
    if sizing_method == "리스크 기반":
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
        # 선택한 방식에 따라 다른 계산 함수 호출
        if sizing_method == "고정 금액":
            result = sizer.calculate_fixed_amount(
                entry_price=entry_price,
                fixed_amount_usd=fixed_amount_usd
            )
        elif sizing_method == "고정 비율":
            result = sizer.calculate_fixed_percent(
                entry_price=entry_price,
                account_percent=account_percent
            )
        else:  # 리스크 기반
            result = sizer.calculate_risk_based(
                entry_price=entry_price,
                stop_loss=stop_loss,
                risk_multiple=risk_multiple
            )
        
        # 결과 표시
        st.subheader(f"포지션 사이징 결과 ({sizing_method})")
        
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
        
        # 리스크 금액 정보 (리스크 기반 방식에서만 표시)
        if sizing_method == "리스크 기반":
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
