import streamlit as st
import pandas as pd
from typing import Dict, Tuple
import requests
from datetime import datetime

# 데이터베이스 및 리포지토리 import (신규 구조)
from utils.database import get_db
from repository.holdings_repo import (
    get_portfolio_holdings, add_holding_to_portfolio, update_holding
)
from repository.portfolio_repo import get_portfolio_by_id
from services.data_service import data_service

def get_exchange_rate():
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
        st.warning(f"환율 정보를 가져오는데 실패했습니다. 기본 환율(1,350원)을 사용합니다. 오류: {e}")
        return 1350.0, "N/A"

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
        # 현재 비중 계산
        current_weight_values = self.calculate_current_weights(positions)
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
    
    # 환율 정보 가져오기
    default_usd_krw, exchange_rate_updated = get_exchange_rate()
    
    # 사이드바에 환율 정보 표시 및 수정 기능
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
        
        st.markdown("---")
        
        rebalancing_method = st.selectbox(
            "리밸런싱 방식",
            ["임계값 기반", "정기 리밸런싱", "복합 방식"],
            label_visibility="visible"
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
            # 정기 리밸런싱 주기 (사용하지 않으면 주석 처리)
            _ = st.selectbox(
                "정기 리밸런싱 주기",
                ["월별", "분기별", "반기별", "연간"]
            )
    
    # 포트폴리오 입력
    st.subheader("현재 포트폴리오")
    
    # 현재 포트폴리오 로드 버튼
    if st.session_state.get('current_portfolio_id'):
        # DB 세션 준비
        db_gen = get_db()
        db = next(db_gen)
        try:
            portfolio = get_portfolio_by_id(db, st.session_state.current_portfolio_id)
        finally:
            db.close()
        if portfolio:
            st.info(f"현재 선택된 포트폴리오: **{portfolio['name']}**")
            if st.button("현재 포트폴리오 정보 로드", use_container_width=True):
                # 현재 포트폴리오 정보 가져오기
                db_gen = get_db()
                db = next(db_gen)
                try:
                    holdings = get_portfolio_holdings(db, st.session_state.current_portfolio_id)
                finally:
                    db.close()
                if holdings:
                    # 포지션에 현재 데이터 채우기
                    st.session_state.positions = {}
                    for holding in holdings:
                        # 현재가 조회 (데이터 서비스 사용)
                        current_price, _ = data_service.get_current_price(holding['symbol'])
                        if current_price is None:
                            current_price = holding['purchase_price']  # 현재가를 가져올 수 없을 경우 매수가 사용
                        
                        st.session_state.positions[holding['symbol']] = (
                            holding['quantity'], 
                            current_price
                        )
                    st.success(f"{len(holdings)}개 종목이 성공적으로 로드되었습니다.")
                else:
                    st.warning("현재 포트폴리오에 종목이 없습니다.")
    else:
        st.warning("포트폴리오 관리에서 포트폴리오를 먼저 선택해주세요.")
    
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
                '현재가($)': price,
                '현재가(원)': price * usd_krw,
                '평가금액($)': qty * price,
                '평가금액(원)': qty * price * usd_krw
            }
            for asset, (qty, price) in st.session_state.positions.items()
        ])
        
        total_value_usd = portfolio_df['평가금액($)'].sum()
        portfolio_df['비중'] = portfolio_df['평가금액($)'] / total_value_usd
        
        st.dataframe(portfolio_df.style.format({
            '수량': '{:.2f}',
            '현재가($)': '{:,.2f}',
            '현재가(원)': '{:,.0f}',
            '평가금액($)': '{:,.2f}',
            '평가금액(원)': '{:,.0f}',
            '비중': '{:.1%}'
        }))
        
        # 총 포트폴리오 가치 표시
        col1, col2 = st.columns(2)
        with col1:
            st.metric("총 포트폴리오 가치($)", f"${total_value_usd:,.2f}")
        with col2:
            st.metric("총 포트폴리오 가치(원)", f"{total_value_usd * usd_krw:,.0f}원")
        
        # 리밸런싱 분석
        st.subheader("리밸런싱 분석")
        
        # 목표 비중 설정 옵션 추가
        st.write("### 목표 비중 설정 방식")
        weight_option = st.radio(
            "비중 설정 방식을 선택하세요:",
            ["동일 비중으로 설정", "수기 입력"],
            horizontal=True
        )
        
        # 목표 비중 설정
        target_weights = {}
        
        # 동일 비중일 경우 자동 계산
        equal_weight_value = None
        if weight_option == "동일 비중으로 설정":
            equal_weight_value = int(100 / len(st.session_state.positions))
            st.success(f"모든 종목이 동일하게 {equal_weight_value}%로 설정됩니다.")
            
            # 동일 비중 자동 설정
            for asset in st.session_state.positions.keys():
                target_weights[asset] = equal_weight_value / 100
            
            # 시각적 표시
            cols = st.columns(len(st.session_state.positions))
            for i, (asset, weight) in enumerate(target_weights.items()):
                with cols[i]:
                    st.metric(f"{asset}", f"{weight*100:.1f}%")
        
        # 수기 입력 옵션
        else:
            cols = st.columns(len(st.session_state.positions))
            for i, asset in enumerate(st.session_state.positions.keys()):
                with cols[i]:
                    # 기본값은 동일 비중의 값으로 설정
                    default_value = int(100 / len(st.session_state.positions))
                    target_weights[asset] = st.number_input(
                        f"{asset} 목표비중 (%)",
                        min_value=0,
                        max_value=100,
                        value=default_value
                    ) / 100
            
            # 합계 표시 및 확인
            total_weight = sum(target_weights.values()) * 100
            st.metric("총 비중 합계", f"{total_weight:.1f}%", 
                      delta=f"{total_weight-100:.1f}%" if abs(total_weight-100) > 0.1 else None)
        
        if abs(sum(target_weights.values()) - 1) > 0.01:
            st.warning("목표 비중의 합이 100%와 차이가 있습니다. 필요시 조정해주세요.")
        
        # 리밸런싱 진행 확인 버튼
        proceed = st.checkbox("위 비중으로 리밸런싱 분석을 진행합니다", value=True)
        
        if not proceed:
            st.stop()
            
        # 리밸런서 초기화 및 분석
        rebalancer = PortfolioRebalancer(target_weights, threshold)
        
        # 현금 입력 필드 변경
        col1, col2 = st.columns(2)
        with col1:
            cash_usd = st.number_input(
                "투자 가능 현금($)",
                min_value=0.0,
                value=0.0,
                step=100.0,
                format="%.2f"
            )
        
        with col2:
            # 원화 환산 표시
            cash_krw = cash_usd * usd_krw
            st.metric("원화 환산", f"{cash_krw:,.0f}원")
        
        trades = rebalancer.calculate_trades(
            st.session_state.positions,
            cash=cash_usd
        )
        
        # 리밸런싱 결과 표시
        st.subheader("필요한 리밸런싱 거래")
        
        # 환율 변동 리스크 알림
        st.info("""
        💱 **환율 변동 리스크 안내**
        
        해외 자산 거래 시 환율 변동에 따라 실제 원화 금액이 달라질 수 있습니다.
        현재 USD/KRW 환율: **{:.2f}원**
        """.format(usd_krw))
        
        trades_df = pd.DataFrame([
            {
                '자산': asset,
                '거래수량': qty,
                '예상금액($)': qty * st.session_state.positions[asset][1],
                '예상금액(원)': qty * st.session_state.positions[asset][1] * usd_krw
            }
            for asset, qty in trades.items()
            if abs(qty) > 0.000001  # 미미한 거래는 제외
        ])
        
        if not trades_df.empty:
            trades_df['거래유형'] = trades_df['거래수량'].apply(
                lambda x: '매수' if x > 0 else '매도'
            )
            
            # 매수/매도 종목 분리하여 시각적으로 표시
            st.write("### 종목별 거래 내역")
            
            # 매수/매도 별 색상 설정을 위한 스타일링
            def color_trades(val):
                if val == '매수':
                    return 'background-color: #d4f1d4'  # 연한 녹색
                elif val == '매도':
                    return 'background-color: #ffd6d6'  # 연한 빨간색
                return ''
            
            # 데이터프레임 스타일링 및 출력
            styled_df = trades_df.style.format({
                '거래수량': '{:+.2f}',
                '예상금액($)': '{:+,.2f}',
                '예상금액(원)': '{:+,.0f}'
            }).applymap(color_trades, subset=['거래유형'])
            
            st.dataframe(styled_df)
            
            # 매수/매도 종목 분리 요약
            col1, col2 = st.columns(2)
            
            with col1:
                buy_df = trades_df[trades_df['거래유형'] == '매수']
                if not buy_df.empty:
                    st.write("#### 매수 종목")
                    buy_total_usd = buy_df['예상금액($)'].sum()
                    buy_total_krw = buy_df['예상금액(원)'].sum()
                    st.markdown(f"""
                    **총 매수 금액**: ${buy_total_usd:,.2f} (≈ {buy_total_krw:,.0f}원)
                    
                    환율 변동 시 예상 원화 금액:
                    * 환율 5% 상승 시: {buy_total_usd * usd_krw * 1.05:,.0f}원
                    * 환율 5% 하락 시: {buy_total_usd * usd_krw * 0.95:,.0f}원
                    """)
                    
                    st.dataframe(buy_df[['자산', '거래수량', '예상금액($)', '예상금액(원)']].style.format({
                        '거래수량': '{:.2f}',
                        '예상금액($)': '{:,.2f}',
                        '예상금액(원)': '{:,.0f}'
                    }))
                else:
                    st.info("매수할 종목이 없습니다.")
            
            with col2:
                sell_df = trades_df[trades_df['거래유형'] == '매도']
                if not sell_df.empty:
                    st.write("#### 매도 종목")
                    sell_total_usd = sell_df['예상금액($)'].sum()
                    sell_total_krw = sell_df['예상금액(원)'].sum()
                    st.markdown(f"""
                    **총 매도 금액**: ${abs(sell_total_usd):,.2f} (≈ {abs(sell_total_krw):,.0f}원)
                    
                    환율 변동 시 예상 원화 금액:
                    * 환율 5% 상승 시: {abs(sell_total_usd) * usd_krw * 1.05:,.0f}원
                    * 환율 5% 하락 시: {abs(sell_total_usd) * usd_krw * 0.95:,.0f}원
                    """)
                    
                    st.dataframe(sell_df[['자산', '거래수량', '예상금액($)', '예상금액(원)']].style.format({
                        '거래수량': '{:.2f}',
                        '예상금액($)': '{:,.2f}',
                        '예상금액(원)': '{:,.0f}'
                    }))
                else:
                    st.info("매도할 종목이 없습니다.")
            
            # 환율 변동에 따른 전체 리밸런싱 비용 요약
            st.markdown("### 환율 변동에 따른 전체 리밸런싱 비용")
            # 매수 총액 - 매도 총액 = 필요 자금
            net_cost_usd = buy_df['예상금액($)'].sum() + sell_df['예상금액($)'].sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("현재 환율 기준", f"${net_cost_usd:,.2f} (≈ {net_cost_usd * usd_krw:,.0f}원)")
            with col2:
                st.metric("환율 5% 상승 시", f"{net_cost_usd * usd_krw * 1.05:,.0f}원")
            with col3:
                st.metric("환율 5% 하락 시", f"{net_cost_usd * usd_krw * 0.95:,.0f}원")
                
            # 리밸런싱 결과를 CSV로 다운로드 기능 추가
            csv = trades_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="리밸런싱 결과 CSV 다운로드",
                data=csv,
                file_name="rebalancing_trades.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            # 리밸런싱 거래 종목코드 일괄 복사
            trade_symbols = ", ".join(trades_df['자산'].tolist())
            
            st.subheader("거래 종목 코드")
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.code(trade_symbols, language=None)
            
            with col2:
                if st.button("복사", key="copy_trade_symbols_button", use_container_width=True):
                    st.session_state.clipboard = trade_symbols
                    st.toast("거래 종목 목록이 클립보드에 복사되었습니다!")
            
            # 리밸런싱 후 포트폴리오 모의 적용 결과 표시
            st.subheader("리밸런싱 후 예상 포트폴리오")
            
            # 리밸런싱 후 포지션 계산
            new_positions = {}
            for asset, (qty, price) in st.session_state.positions.items():
                new_qty = qty
                if asset in trades:
                    new_qty += trades[asset]
                if new_qty > 0:  # 수량이 0 이상인 경우만 포함
                    new_positions[asset] = (new_qty, price)
            
            # 리밸런싱 후 포트폴리오 표시
            if new_positions:
                new_portfolio_df = pd.DataFrame([
                    {
                        '자산': asset,
                        '수량': qty,
                        '현재가($)': price,
                        '현재가(원)': price * usd_krw,
                        '평가금액($)': qty * price,
                        '평가금액(원)': qty * price * usd_krw
                    }
                    for asset, (qty, price) in new_positions.items()
                ])
                
                new_total_value_usd = new_portfolio_df['평가금액($)'].sum()
                new_portfolio_df['비중'] = new_portfolio_df['평가금액($)'] / new_total_value_usd
                
                st.dataframe(new_portfolio_df.style.format({
                    '수량': '{:.2f}',
                    '현재가($)': '{:,.2f}',
                    '현재가(원)': '{:,.0f}',
                    '평가금액($)': '{:,.2f}',
                    '평가금액(원)': '{:,.0f}',
                    '비중': '{:.1%}'
                }))
                
                # 리밸런싱 후 총 포트폴리오 가치 표시
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("리밸런싱 후 총 가치($)", f"${new_total_value_usd:,.2f}")
                with col2:
                    st.metric("리밸런싱 후 총 가치(원)", f"{new_total_value_usd * usd_krw:,.0f}원")
                
                # 리밸런싱 결과를 현재 포트폴리오에 적용하는 기능
                if st.session_state.get('current_portfolio_id') and st.button(
                    "리밸런싱 결과를 현재 포트폴리오에 적용", 
                    use_container_width=True,
                    key="apply_rebalancing"
                ):
                    # 포트폴리오 ID
                    portfolio_id = st.session_state.current_portfolio_id
                    
                    # 현재 포트폴리오의 모든 종목 정보
                    db_gen = get_db()
                    db = next(db_gen)
                    try:
                        current_holdings = get_portfolio_holdings(db, portfolio_id)
                    finally:
                        db.close()
                    current_holdings_dict = {h['symbol']: h for h in current_holdings}
                    
                    # 종목별 처리
                    success_count = 0
                    for asset, (qty, price) in new_positions.items():
                        try:
                            # 현재 포트폴리오에 있는 종목인 경우 수량 업데이트
                            if asset in current_holdings_dict:
                                holding = current_holdings_dict[asset]
                                db_gen = get_db()
                                db = next(db_gen)
                                try:
                                    update_holding(
                                        db,
                                        holding['id'],
                                        qty,
                                        holding['purchase_price'],
                                        holding['purchase_date'],
                                        holding['asset_type']
                                    )
                                finally:
                                    db.close()
                            # 새로운 종목인 경우 추가
                            else:
                                from datetime import datetime
                                db_gen = get_db()
                                db = next(db_gen)
                                try:
                                    add_holding_to_portfolio(
                                        db,
                                        portfolio_id,
                                        asset,
                                        qty,
                                        price,  # 현재가를 매수가로 사용
                                        datetime.now().strftime('%Y-%m-%d'),
                                        'Stock'  # 기본 자산유형으로 Stock 설정
                                    )
                                finally:
                                    db.close()
                            success_count += 1
                        except Exception as e:
                            st.error(f"{asset} 업데이트 실패: {str(e)}")
                    
                    if success_count > 0:
                        st.success(f"{success_count}개 종목의 리밸런싱 결과가 포트폴리오에 적용되었습니다.")
                        st.session_state.refresh_required = True
                        # 세션 상태를 초기화하여 포트폴리오 관리 화면에 반영되도록 함
                        if 'positions' in st.session_state:
                            del st.session_state.positions
                    else:
                        st.error("리밸런싱 결과 적용에 실패했습니다.")
        else:
            st.info("현재 설정에서는 필요한 리밸런싱 거래가 없습니다.") 
