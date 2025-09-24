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

    # 포트폴리오 기반 탭 추가
    tab1, tab2 = st.tabs(["📊 포트폴리오 기반", "📈 개별 종목"])

    with tab1:
        show_portfolio_based_sizing()

    with tab2:
        show_individual_sizing()

def show_portfolio_based_sizing():
    """포트폴리오 기반 포지션 사이징"""
    st.subheader("🗂️ 포트폴리오 선택")
    
    # 포트폴리오 목록 새로고침 버튼
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 목록 새로고침", help="포트폴리오 목록을 새로고침합니다", key="position_refresh"):
            st.rerun()

    # 포트폴리오 목록 가져오기
    try:
        from backtesting import get_all_portfolio_list, load_portfolio
        portfolio_list = get_all_portfolio_list()

        if not portfolio_list:
            st.warning("⚠️ 저장된 포트폴리오가 없습니다.")
            st.info("포트폴리오 관리 페이지에서 포트폴리오를 생성해주세요.")
            return

        selected_portfolio = st.selectbox(
            "포트폴리오 선택",
            portfolio_list,
            help="모든 포트폴리오가 표시됩니다. 목표 비중이 없는 포트폴리오는 보유 종목을 기반으로 동일 비중으로 설정됩니다."
        )

        if selected_portfolio:
            portfolio_data = load_portfolio(selected_portfolio)
            if portfolio_data:
                st.success(f"✅ '{selected_portfolio}' 포트폴리오 로드 완료")

                # 포트폴리오 정보 표시
                with st.expander("📊 포트폴리오 구성", expanded=True):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        import pandas as pd
                        weights_data = []
                        for asset, weight in portfolio_data['weights'].items():
                            weights_data.append({
                                '자산': asset,
                                '목표 비중': f"{weight*100:.1f}%",
                                '비중(소수)': weight
                            })

                        weights_df = pd.DataFrame(weights_data)
                        st.dataframe(weights_df[['자산', '목표 비중']], use_container_width=True, hide_index=True)

                    with col2:
                        st.metric("총 자산 수", len(portfolio_data['assets']))
                        total_weight = sum(portfolio_data['weights'].values())
                        st.metric("비중 합계", f"{total_weight*100:.1f}%")

                # 투자 금액 설정
                st.subheader("💰 투자 금액 설정")

                col1, col2, col3 = st.columns(3)

                with col1:
                    total_investment_usd = st.number_input(
                        "총 투자 금액 (USD)",
                        min_value=100.0,
                        max_value=10000000.0,
                        value=10000.0,
                        step=100.0,
                        format="%.2f",
                        key="portfolio_total_investment"
                    )

                with col2:
                    # 환율 정보
                    default_usd_krw, exchange_rate_updated = get_exchange_rate()
                    usd_krw = st.number_input(
                        "USD/KRW 환율",
                        min_value=900.0,
                        max_value=2000.0,
                        value=default_usd_krw,
                        step=0.5,
                        format="%.2f",
                        key="portfolio_usd_krw"
                    )

                with col3:
                    total_investment_krw = total_investment_usd * usd_krw
                    st.metric("총 투자 금액 (KRW)", f"₩{total_investment_krw:,.0f}")

                # 포지션 사이징 계산
                st.subheader("📊 자산별 포지션 사이징")

                sizing_results = []
                for asset, weight in portfolio_data['weights'].items():
                    asset_investment_usd = total_investment_usd * weight
                    asset_investment_krw = asset_investment_usd * usd_krw

                    sizing_results.append({
                        '자산': asset,
                        '목표 비중': f"{weight*100:.1f}%",
                        '투자 금액 (USD)': f"${asset_investment_usd:,.2f}",
                        '투자 금액 (KRW)': f"₩{asset_investment_krw:,.0f}",
                        '비중(숫자)': weight,
                        '금액USD(숫자)': asset_investment_usd,
                        '금액KRW(숫자)': asset_investment_krw
                    })

                # 결과 표시
                results_df = pd.DataFrame(sizing_results)

                # 표 표시
                display_df = results_df[['자산', '목표 비중', '투자 금액 (USD)', '투자 금액 (KRW)']]
                st.dataframe(display_df, use_container_width=True, hide_index=True)

                # 차트 표시
                col1, col2 = st.columns(2)

                with col1:
                    import plotly.express as px
                    fig_pie = px.pie(
                        results_df,
                        values='금액USD(숫자)',
                        names='자산',
                        title='투자 금액 분배 (USD)',
                        hover_data=['투자 금액 (USD)']
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)

                with col2:
                    # 상위 5개 자산 표시
                    top5 = results_df.nlargest(5, '금액USD(숫자)')
                    st.subheader("💎 Top 5 투자 금액")
                    for _, row in top5.iterrows():
                        st.metric(
                            row['자산'],
                            row['투자 금액 (USD)'],
                            f"{row['목표 비중']}"
                        )

                # 다운로드 기능
                st.subheader("💾 결과 다운로드")

                # CSV 다운로드
                csv_data = results_df[['자산', '목표 비중', '투자 금액 (USD)', '투자 금액 (KRW)']].to_csv(index=False)
                st.download_button(
                    label="📄 CSV 파일 다운로드",
                    data=csv_data,
                    file_name=f"position_sizing_{selected_portfolio}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

    except ImportError:
        st.error("❌ 포트폴리오 데이터를 로드할 수 없습니다. 백테스팅 모듈을 확인해주세요.")
    except Exception as e:
        st.error(f"❌ 오류 발생: {str(e)}")

def show_individual_sizing():
    """개별 종목 기반 포지션 사이징 (기존 코드)"""

    # 개별 종목 사이징 가이드
    with st.expander("📚 개별 종목 포지션 사이징이란?", expanded=False):
        st.markdown("""
        # 개별 종목 포지션 사이징(Position Sizing)의 활용

        개별 종목 포지션 사이징은 **특정 종목에 얼마나 투자할지** 결정하는 중요한 과정입니다.

        ## 주요 사이징 방식

        ### 1. 고정 금액 방식
        - **언제 사용**: 정기적으로 일정 금액을 투자할 때
        - **예시**: 매달 애플 주식에 100만원씩 투자
        - **장점**: 계산이 단순하고 실행하기 쉬움

        ### 2. 고정 비율 방식
        - **언제 사용**: 전체 자산 대비 일정 비율로 투자할 때
        - **예시**: 전체 자산의 10%를 테슬라에 투자
        - **장점**: 자산 가치 변동에 따라 자동 조정

        ### 3. 리스크 기반 방식
        - **언제 사용**: 손실 위험을 정확히 제어하고 싶을 때
        - **예시**: 비트코인 투자 시 손실을 총 자산의 2%로 제한
        - **장점**: 변동성이 큰 자산에 대한 체계적 리스크 관리
        """)

    # 기존 개별 종목 사이징 로직
    show_original_individual_sizing()

def show_original_individual_sizing():
    """기존 개별 종목 사이징 로직"""

    # 환율 정보
    default_usd_krw, exchange_rate_updated = get_exchange_rate()

    with st.expander("💡 사이징 방식별 설명", expanded=False):
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
                format="%.2f",
                key="individual_usd_krw"
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
            min_value=100.0,
            max_value=10000000.0,
            value=10000.0,
            step=100.0,
            format="%.2f",
            key="individual_account_size"
        )

    with col2:
        account_size_krw = account_size_usd * usd_krw
        st.metric("계좌 크기 (KRW)", f"₩{account_size_krw:,.0f}")

    # 종목 정보 입력
    st.subheader("종목 정보")
    col1, col2 = st.columns(2)

    with col1:
        ticker = st.text_input("종목 코드", value="AAPL", help="예: AAPL, TSLA, MSFT 등", key="individual_ticker")

    with col2:
        entry_price = st.number_input(
            "진입 가격 (USD)",
            min_value=0.01,
            value=150.0,
            step=0.01,
            format="%.2f",
            key="individual_entry_price"
        )

    # 사이징 방식별 설정
    if sizing_method == "고정 금액":
        st.subheader("고정 금액 설정")
        fixed_amount_usd = st.number_input(
            "투자 금액 (USD)",
            min_value=1.0,
            value=1000.0,
            step=10.0,
            format="%.2f",
            key="individual_fixed_amount"
        )

    elif sizing_method == "고정 비율":
        st.subheader("고정 비율 설정")
        fixed_percentage = st.slider(
            "계좌 대비 투자 비율 (%)",
            min_value=0.1,
            max_value=50.0,
            value=5.0,
            step=0.1
        )

    else:  # 리스크 기반
        st.subheader("리스크 기반 설정")
        col1, col2 = st.columns(2)

        with col1:
            risk_per_trade = st.slider(
                "거래당 리스크 (%)",
                min_value=0.1,
                max_value=10.0,
                value=2.0,
                step=0.1
            )

        with col2:
            stop_loss_pct = st.slider(
                "손절가 (%)",
                min_value=1.0,
                max_value=50.0,
                value=10.0,
                step=0.5
            )

    # 계산 버튼
    if st.button("포지션 사이즈 계산", type="primary"):
        try:
            config = PositionSizeConfig(
                max_position_size=0.25,
                risk_per_trade=risk_per_trade if sizing_method == "리스크 기반" else 2.0,
                account_size_usd=account_size_usd,
                exchange_rate=usd_krw
            )

            sizer = PositionSizer(config)

            if sizing_method == "고정 금액":
                result = sizer.calculate_fixed_amount(entry_price, fixed_amount_usd)
            elif sizing_method == "고정 비율":
                result = sizer.calculate_fixed_percentage(entry_price, fixed_percentage / 100)
            else:  # 리스크 기반
                stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
                result = sizer.calculate_risk_based(entry_price, stop_loss_price)

            # 결과 표시
            st.subheader("💡 계산 결과")

            # 포지션 정보
            st.markdown("### 포지션 정보")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "주식 수",
                    f"{result['shares']:.2f} 주"
                )

            with col2:
                st.metric(
                    "포지션 크기 (%)",
                    f"{result['position_percentage']:.2f}%"
                )

            with col3:
                st.metric(
                    "투자 금액 (USD)",
                    f"${result['position_value_usd']:,.2f}"
                )

            # 원화 환산 정보
            st.markdown("### 원화 환산")
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

    # 기존의 매우 긴 사이징 가이드 제거하고 간단한 안내로 대체
    st.markdown("---")
    st.info("💡 **팁**: 포트폴리오 전체의 사이징을 원한다면 '포트폴리오 기반' 탭을 이용해보세요!")
