import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from scipy import stats
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from sqlalchemy.orm import Session
from services.data_service import data_service
from utils.database import get_db
from repository import holdings_repo

# 설정 시스템 import
from config.app_config import get_config, get_ui_config, get_trading_config, get_validation_config

# 에러 처리 시스템 import
from utils.error_handler import (
    handle_errors, safe_execute, ErrorRecovery,
    TickerNotFoundError, DataUnavailableError, InsufficientDataError,
    error_handler
)

# 데이터 검증 시스템 import
from utils.validators import (
    DataValidator, DataQualityChecker, PortfolioValidator,
    validate_ticker_input, validate_weights_input, validate_date_input,
    show_validation_results,
    validate_ticker
)

# 로깅 시스템 import
from utils.logger import (
    portfolio_logger, log_user_action, log_data_operation, 
    log_calculation_result, show_log_dashboard
)

# 통합 데이터 서비스 import
from services.data_service import data_service
from services.analyzer import calculate_portfolio_returns, calculate_risk_metrics

# 데이터베이스 모듈 import
from utils.database import get_db
from repository import portfolio_repo, holdings_repo, target_weights_repo, performance_repo

# 모듈 레벨 초기화 코드는 유지하되 함수 내에서도 초기화하도록 합니다
def initialize_session_state():
    """세션 상태를 안전하게 초기화합니다."""
    if 'current_portfolio_id' not in st.session_state:
        st.session_state.current_portfolio_id = None
    
    if 'portfolios' not in st.session_state:
        # DB에서 포트폴리오 목록 초기 로드
        try:
            db_gen = get_db()
            db = next(db_gen)
            try:
                st.session_state.portfolios = portfolio_repo.get_all_portfolios(db)
            finally:
                db.close()
        except Exception:
            st.session_state.portfolios = []
    
    if 'data_cache' not in st.session_state:
        st.session_state.data_cache = {}

# 초기화 함수 호출
initialize_session_state()

def refresh_portfolios():
    """포트폴리오 목록을 새로고침"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            st.session_state.portfolios = portfolio_repo.get_all_portfolios(db)
        finally:
            db.close()
    except Exception:
        st.session_state.portfolios = []

def fetch_current_price(stock):
    """실시간 주가를 가져옵니다. (통합 데이터 서비스 사용)"""
    return data_service.get_current_price(stock)

def fetch_historical_data(symbols, start_date, end_date):
    """여러 종목의 히스토리컬 데이터를 가져옵니다. (통합 데이터 서비스 사용)"""
    # 날짜를 datetime 객체로 변환
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    
    # 통합 데이터 서비스 사용
    data_dict = data_service.fetch_multiple_stocks(
        symbols, start_date, end_date, show_progress=True
    )
    
    # 데이터프레임으로 변환
    if data_dict:
        return data_service.combine_price_data(data_dict)
    else:
        return pd.DataFrame()

# 포트폴리오 관리 UI
def show_portfolio_management(db: Session):
    st.subheader("🗂️ 포트폴리오 관리")
    
    tabs = st.tabs(["포트폴리오 목록", "포트폴리오 생성", "포트폴리오 편집"])
    
    with tabs[0]:
        # 목록 상단 새로고침 버튼
        c1, c2 = st.columns([3, 1])
        with c2:
            if st.button("🔄 목록 새로고침", help="포트폴리오 목록을 새로고침합니다", key="pm_list_refresh"):
                refresh_portfolios()
                st.rerun()

        portfolios = st.session_state.get('portfolios', [])
        if not portfolios:
            st.info("생성된 포트폴리오가 없습니다.")
        else:
            portfolio_names = {p.id: p.name for p in portfolios}
            selected_portfolio_id = st.selectbox("포트폴리오 선택", options=list(portfolio_names.keys()), format_func=lambda x: portfolio_names.get(x, ""), key="portfolio_selector")
            
            if selected_portfolio_id != st.session_state.get('current_portfolio_id'):
                st.session_state.current_portfolio_id = selected_portfolio_id
                st.rerun()
            
            if selected_portfolio_id:
                portfolio = portfolio_repo.get_portfolio_by_id(db, selected_portfolio_id)
                if portfolio:
                    st.markdown(f"### {portfolio.name}")
                    st.write(f"설명: {portfolio.description}")
                    st.write(f"생성일: {portfolio.created_at}")
                    if st.button("포트폴리오 삭제", key="delete_portfolio_main"):
                        if portfolio_repo.delete_portfolio(db, selected_portfolio_id):
                            st.session_state.current_portfolio_id = None
                            st.session_state.portfolios = portfolio_repo.get_all_portfolios(db)
                            st.success("포트폴리오가 삭제되었습니다.")
                            st.rerun()
                        else:
                            st.error("포트폴리오 삭제 중 오류가 발생했습니다.")

    with tabs[1]:
        with st.form("create_portfolio_form"):
            name = st.text_input("포트폴리오 이름")
            description = st.text_area("설명 (선택사항)")
            if st.form_submit_button("포트폴리오 생성"):
                if name:
                    new_p = portfolio_repo.create_portfolio(db, name, description)
                    st.session_state.portfolios = portfolio_repo.get_all_portfolios(db)
                    st.session_state.current_portfolio_id = new_p.id
                    st.success(f"'{name}' 포트폴리오가 생성되었습니다.")
                    st.rerun()
                else:
                    st.error("포트폴리오 이름을 입력해주세요.")

    with tabs[2]:
        # 편집 탭 상단 새로고침 버튼
        c1, c2 = st.columns([3, 1])
        with c2:
            if st.button("🔄 목록 새로고침", help="포트폴리오 목록을 새로고침합니다", key="pm_edit_refresh"):
                refresh_portfolios()
                st.rerun()

        portfolios = st.session_state.get('portfolios', [])
        if not portfolios:
            st.info("편집할 포트폴리오가 없습니다.")
            return

        portfolio_names = {p.id: p.name for p in portfolios}
        selected_portfolio_id = st.selectbox("수정할 포트폴리오 선택", options=list(portfolio_names.keys()), format_func=lambda x: portfolio_names.get(x, ""), key="edit_portfolio_selector")
        
        if selected_portfolio_id:
            portfolio = portfolio_repo.get_portfolio_by_id(db, selected_portfolio_id)
            if portfolio:
                with st.form("edit_portfolio_form"):
                    name = st.text_input("포트폴리오 이름", value=portfolio.name)
                    description = st.text_area("설명", value=portfolio.description or "")
                    if st.form_submit_button("변경사항 저장"):
                        if name:
                            portfolio_repo.update_portfolio(db, portfolio.id, name, description)
                            st.session_state.portfolios = portfolio_repo.get_all_portfolios(db)
                            st.success("포트폴리오가 업데이트되었습니다.")
                            st.rerun()
                        else:
                            st.error("포트폴리오 이름을 입력해주세요.")
                
                if st.button("포트폴리오 삭제", key="delete_portfolio_edit"):
                    portfolio_repo.delete_portfolio(db, portfolio.id)
                    st.session_state.current_portfolio_id = None
                    st.session_state.portfolios = portfolio_repo.get_all_portfolios(db)
                    st.success("포트폴리오가 삭제되었습니다.")
                    st.rerun()

                current_weights = target_weights_repo.get_portfolio_target_weights(db, portfolio.id)
                edited_df = st.data_editor(pd.DataFrame([{"종목": sym, "비중(%)": w*100} for sym, w in current_weights.items()] or [{"종목": "", "비중(%)": 0.0}]), num_rows="dynamic")
                if st.button("목표 비중 저장"):
                    # 벡터화 연산으로 성능 개선 - 빈 종목 필터링
                    valid_rows = edited_df[edited_df['종목'] != ''].copy()
                    weights = dict(zip(valid_rows['종목'], valid_rows['비중(%)'].astype(float) / 100.0))
                    target_weights_repo.set_portfolio_target_weights(db, portfolio.id, weights)
                    st.success("목표 비중이 저장되었습니다.")

# 종목 추가 함수
def add_investment(db: Session, portfolio_id, symbol, quantity, purchase_price, purchase_date, asset_type):
    # 사용자 액션 로깅
    log_user_action("add_investment", 
                   portfolio_id=portfolio_id, 
                   symbol=symbol, 
                   asset_type=asset_type)
    
    # 종목 코드 검증
    valid, msg = validate_ticker(symbol)
    if not valid:
        error_msg = msg if msg else "종목 코드 검증 실패"
        st.sidebar.error(f"{symbol}: {error_msg}")
        return False
    
    # 자산 데이터 검증
    validator = DataValidator()
    asset_valid, asset_errors = validator.validate_asset_data(
        asset_type, quantity, purchase_price
    )
    
    if not asset_valid:
        for error in asset_errors:
            st.sidebar.error(error)
        return False

    # 데이터베이스에 저장
    try:
        holding = holdings_repo.add_holding_to_portfolio(
            db,
            portfolio_id, 
            symbol, 
            quantity, 
            purchase_price, 
            purchase_date, 
            asset_type
        )
        
        if holding:
            return True
        else:
            st.sidebar.error("종목 추가 중 오류가 발생했습니다.")
            return False
    except Exception as e:
        st.sidebar.error(f"종목 추가 중 데이터베이스 오류 발생: {str(e)}")
        return False

# 종목 편집 함수
def edit_investment(db: Session, holding_id, quantity, purchase_price, purchase_date, asset_type):
    # 입력값 검증
    error_message = None
    if quantity <= 0:
        error_message = "수량은 0보다 커야 합니다."
    elif purchase_price <= 0:
        error_message = "매수가는 0보다 커야 합니다."

    if error_message:
        st.error(error_message)
        return False

    # 데이터베이스에 업데이트
    try:
        updated = holdings_repo.update_holding(
            db,
            holding_id, 
            quantity, 
            purchase_price, 
            purchase_date, 
            asset_type
        )
        
        if updated:
            return True
        else:
            st.error("종목 수정 중 오류가 발생했습니다.")
            return False

    except Exception as e:
        st.error(f"종목 정보 업데이트 중 오류가 발생했습니다: {str(e)}")
        return False

# 포트폴리오 표시
def show_portfolio_holdings(db: Session):
    if st.session_state.current_portfolio_id:
        st.header('포트폴리오 보유 종목')
        
        # 보유 종목 조회
        holdings = holdings_repo.get_portfolio_holdings(db, st.session_state.current_portfolio_id)
        
        if holdings:
            # 티커 목록 추출 및 표시
            tickers = [holding.symbol for holding in holdings]
            ticker_string = ", ".join(tickers)
            
            st.subheader("티커 목록")
            ticker_col1, ticker_col2 = st.columns([4, 1])
            
            with ticker_col1:
                st.code(ticker_string, language=None)
            
            with ticker_col2:
                if st.button("복사", key="copy_tickers_button", use_container_width=True):
                    st.session_state.clipboard = ticker_string
                    st.toast("티커 목록이 클립보드에 복사되었습니다! (Ctrl+V로 붙여넣기 가능)")
            
            st.markdown("---")
            
            # 실시간 가격 업데이트
            holdings_data = []
            total_value = 0
            
            with st.spinner("현재가를 가져오는 중..."):
                for holding in holdings:
                    symbol = holding.symbol
                    current_price = None
                    error_msg = None
                    
                    # 한국 주식 여부 확인
                    is_korean = (
                        (len(symbol) in [6, 7] and symbol.isdigit()) or 
                        symbol.endswith('.KS') or 
                        symbol.endswith('.KQ')
                    )
                    
                    # 통합 데이터 서비스 기반 현재가 조회 (필요 시 접미사 시도)
                    if is_korean and not (symbol.endswith('.KS') or symbol.endswith('.KQ')):
                        for suffix in ['.KS', '.KQ']:
                            test_symbol = f"{symbol}{suffix}"
                            price, msg = fetch_current_price(test_symbol)
                            if price is not None:
                                current_price = price
                                symbol = test_symbol
                                break
                    
                    if current_price is None:
                        current_price, error_msg = fetch_current_price(symbol)
                    
                    # 가격 값 정규화: None/NaN/비수치 → 0 으로 처리해 합계가 NaN이 되지 않도록 함
                    try:
                        if current_price is None or (isinstance(current_price, (float, int)) and not np.isfinite(current_price)):
                            if error_msg:
                                st.warning(f"{symbol}: {error_msg}")
                            current_price = 0.0
                        else:
                            current_price = float(current_price)
                    except Exception:
                        if error_msg:
                            st.warning(f"{symbol}: {error_msg}")
                        current_price = 0.0
                    
                    market_value = holding.quantity * current_price
                    gain_loss = (
                        market_value - 
                        (holding.quantity * holding.purchase_price)
                    )
                    gain_loss_pct = (
                        (gain_loss / 
                         (holding.quantity * holding.purchase_price)) * 100 
                        if holding.purchase_price > 0 else 0
                    )
                    
                    total_value += market_value
                    
                    holdings_data.append({
                        'ID': holding.id,
                        '종목': symbol,
                        '보유수량': holding.quantity,
                        '매수가': holding.purchase_price,
                        '현재가': current_price,
                        '시장가치': market_value,
                        '손익': gain_loss,
                        '손익(%)': gain_loss_pct,
                        '자산유형': holding.asset_type,
                        '매수일': holding.purchase_date or '정보 없음'
                    })
            
            # 데이터프레임 생성
            df = pd.DataFrame(holdings_data)
            
            # 종목별 시장가치 비중 계산
            if total_value > 0:
                df['비중(%)'] = (df['시장가치'] / total_value) * 100
            else:
                df['비중(%)'] = 0
            
            # 표시용 데이터프레임 생성 및 포맷팅
            display_df = df.copy()
            
            # 숫자 포맷팅
            display_df['현재가'] = display_df['현재가'].map('${:,.2f}'.format)
            display_df['시장가치'] = display_df['시장가치'].map('${:,.2f}'.format)
            display_df['손익'] = display_df['손익'].map('${:,.2f}'.format)
            display_df['손익(%)'] = display_df['손익(%)'].map('{:,.2f}%'.format)
            display_df['비중(%)'] = display_df['비중(%)'].map('{:,.2f}%'.format)
            
            # 데이터프레임 표시
            st.dataframe(display_df, use_container_width=True)
            
            # 포트폴리오 현황 정보 표시
            col1, col2 = st.columns(2)
            
            with col1:
                # 포트폴리오 총 가치
                st.metric("포트폴리오 총 가치", f"${total_value:,.2f}")
                
                # 순자산가치(NAV) 계산 및 표시
                total_shares = sum([holding.quantity for holding in holdings])
                nav = total_value / total_shares if total_shares > 0 else 0
                st.metric("NAV (순자산가치)", f"${nav:,.2f}")
                
                # 자산유형별 비중 계산
                asset_types = {}
                for item in holdings_data:
                    asset_type = item['자산유형']
                    market_value = item['시장가치']
                    if asset_type in asset_types:
                        asset_types[asset_type] += market_value
                    else:
                        asset_types[asset_type] = market_value
                
                # 자산유형별 비중 표시
                st.subheader("자산유형별 비중")
                asset_type_df = pd.DataFrame({
                    '자산유형': list(asset_types.keys()),
                    '시장가치': list(asset_types.values()),
                    '비중(%)': [value/total_value*100 for value in asset_types.values()] if total_value > 0 else [0] * len(asset_types)
                })
                
                # 모든 컬럼이 문자열 타입인지 확인하여 PyArrow 변환 오류 방지
                asset_type_df['자산유형'] = asset_type_df['자산유형'].astype(str)
                
                # 자산유형별 비중 테이블 표시
                asset_type_df['시장가치'] = asset_type_df['시장가치'].map('${:,.2f}'.format)
                asset_type_df['비중(%)'] = asset_type_df['비중(%)'].map('{:,.2f}%'.format)
                st.dataframe(asset_type_df, use_container_width=True)
            
            with col2:
                # 포트폴리오 수익률 정보
                total_investment = sum([holding.quantity * holding.purchase_price for holding in holdings])
                total_gain_loss = total_value - total_investment
                total_gain_loss_pct = (total_gain_loss / total_investment) * 100 if total_investment > 0 else 0
                
                # 총 수익/손실 표시
                st.metric(
                    "총 수익/손실", 
                    f"${total_gain_loss:,.2f}", 
                    f"{total_gain_loss_pct:,.2f}%",
                    delta_color="normal" if total_gain_loss >= 0 else "inverse"
                )
                
                # 포트폴리오 요약 정보
                st.subheader("포트폴리오 요약")
                summary_data = {
                    "총 투자액": f"${total_investment:,.2f}",
                    "총 종목 수": str(len(holdings)),
                    "평균 종목 비중": f"{100/len(holdings):,.2f}%" if holdings else "0%",
                    "최대 비중 종목": df.loc[df['시장가치'].idxmax(), '종목'] if not df.empty else "없음",
                    "최대 수익 종목": df.loc[df['손익(%)'].idxmax(), '종목'] if not df.empty else "없음",
                    "최대 손실 종목": df.loc[df['손익(%)'].idxmin(), '종목'] if not df.empty else "없음"
                }
                
                summary_df = pd.DataFrame({
                    '항목': list(summary_data.keys()),
                    '값': list(summary_data.values())
                })
                
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
            
            # 포트폴리오 현황 시각화 - 비중 파이 차트
            if len(holdings_data) > 0:
                st.subheader("포트폴리오 비중 분포")
                fig = go.Figure(data=[go.Pie(
                    labels=df['종목'],
                    values=df['시장가치'],
                    hole=.3,
                    textinfo='label+percent',
                    marker_colors=px.colors.qualitative.Pastel
                )])
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

            # 성과 이력(저장된 DB) 섹션
            st.markdown("---")
            st.subheader("📈 성과 이력 (DB)")

            # 모든 성과를 불러와 기간 선택에 사용
            all_perf_rows = performance_repo.get_portfolio_performance(db, st.session_state.current_portfolio_id)
            if not all_perf_rows:
                st.info("저장된 성과 이력이 없습니다. 백테스트 결과 화면에서 '성과 기록 저장'을 먼저 수행하세요.")
            else:
                # ORM 객체를 안전하게 DataFrame으로 변환
                base_df = pd.DataFrame([
                    {
                        'date': getattr(row, 'date', None),
                        'total_value': getattr(row, 'total_value', None),
                        'daily_return': getattr(row, 'daily_return', None),
                    }
                    for row in all_perf_rows
                    if row is not None
                ])
                if base_df.empty or 'date' not in base_df.columns:
                    st.info("저장된 성과 이력이 없습니다. 백테스트 결과 화면에서 '성과 기록 저장'을 먼저 수행하세요.")
                    return
                base_df['date'] = pd.to_datetime(base_df['date'], errors='coerce')
                base_df = base_df.dropna(subset=['date'])
                base_df = base_df.sort_values('date')
                base_df['total_value'] = pd.to_numeric(base_df['total_value'], errors='coerce')
                if 'daily_return' in base_df.columns:
                    base_df['daily_return'] = pd.to_numeric(base_df['daily_return'], errors='coerce')

                min_d = base_df['date'].min().date()
                max_d = base_df['date'].max().date()

                # 기간 선택 + 사용자 지정
                period = st.selectbox(
                    "기간",
                    options=["1개월", "3개월", "6개월", "1년", "3년", "전체", "사용자 지정"],
                    index=5,
                    key="perf_history_period"
                )

                start_dt, end_dt = None, None
                if period == "전체":
                    start_dt, end_dt = min_d, max_d
                elif period == "사용자 지정":
                    c1, c2 = st.columns(2)
                    with c1:
                        start_dt = st.date_input("시작일", value=max(min_d, max_d - timedelta(days=180)), min_value=min_d, max_value=max_d, key="perf_start_date")
                    with c2:
                        end_dt = st.date_input("종료일", value=max_d, min_value=min_d, max_value=max_d, key="perf_end_date")
                    if start_dt > end_dt:
                        st.warning("시작일은 종료일보다 이전이어야 합니다.")
                        start_dt, end_dt = end_dt, start_dt
                else:
                    days_map = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365, "3년": 365*3}
                    end_dt = max_d
                    start_dt = max(min_d, end_dt - timedelta(days=days_map[period]))

                # 기간 필터링
                perf_df = base_df[(base_df['date'] >= pd.to_datetime(start_dt)) & (base_df['date'] <= pd.to_datetime(end_dt))].copy()
                if perf_df.empty:
                    st.info("선택한 기간에 데이터가 없습니다.")
                else:
                    # 총가치 라인 차트
                    fig_tv = go.Figure()
                    fig_tv.add_trace(go.Scatter(
                        x=perf_df['date'], y=perf_df['total_value'], mode='lines', name='총 가치'
                    ))
                    fig_tv.update_layout(
                        title='총 가치 추이', xaxis_title='날짜', yaxis_title='총 가치', height=350
                    )
                    st.plotly_chart(fig_tv, use_container_width=True)

                    # 일간 수익률 막대 차트(가능 시)
                    has_dr = 'daily_return' in perf_df.columns and perf_df['daily_return'].notna().any()
                    if has_dr:
                        fig_dr = go.Figure()
                        fig_dr.add_trace(go.Bar(
                            x=perf_df['date'], y=perf_df['daily_return']*100.0, name='일간 수익률(%)',
                            marker_color=['#2ca02c' if v >= 0 else '#d62728' for v in perf_df['daily_return'].fillna(0)]
                        ))
                        fig_dr.update_layout(
                            title='일간 수익률(%)', xaxis_title='날짜', yaxis_title='수익률(%)', height=250
                        )
                        st.plotly_chart(fig_dr, use_container_width=True)

                    # 요약 메트릭 계산
                    try:
                        # 인덱스화 (날짜 인덱스 사용)
                        tv_series = perf_df.set_index('date')['total_value']
                        idx = tv_series / tv_series.iloc[0]
                        daily_ret = perf_df.set_index('date')['daily_return'].dropna() if has_dr else idx.pct_change().dropna()
                        n = len(daily_ret)
                        ann_factor = 252
                        total_return = idx.iloc[-1] - 1
                        ann_return = (1 + total_return) ** (ann_factor / max(n, 1)) - 1 if n > 0 else 0
                        ann_vol = daily_ret.std() * np.sqrt(ann_factor) if n > 1 else 0
                        # MDD
                        roll_max = idx.cummax()
                        drawdown = idx / roll_max - 1
                        mdd = drawdown.min() if len(drawdown) else 0
                        # Sharpe (연 환산, 무위험 수익률 config 사용)
                        from config.app_config import get_trading_config
                        rf = get_trading_config().risk_free_rate
                        sharpe = (ann_return - rf) / ann_vol if ann_vol > 0 else 0
                        # VaR/CVaR (95%)
                        if n > 0:
                            var_95 = np.percentile(daily_ret.values, 5)
                            cvar_95 = daily_ret[daily_ret <= var_95].mean() if (daily_ret <= var_95).any() else 0.0
                        else:
                            var_95, cvar_95 = 0.0, 0.0
                        # 승률
                        win_rate = float((daily_ret > 0).mean()) if n > 0 else 0.0

                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("총 수익률", f"{total_return*100:.2f}%")
                        col2.metric("연환산 수익률", f"{ann_return*100:.2f}%")
                        col3.metric("연환산 변동성", f"{ann_vol*100:.2f}%")
                        col4.metric("MDD", f"{mdd*100:.2f}%")
                        # 두 번째 줄
                        col5, col6 = st.columns(2)
                        col5.metric("Sharpe Ratio", f"{sharpe:.3f}")
                        if mdd and mdd != 0:
                            calmar = ann_return / abs(mdd)
                            col6.metric("Calmar Ratio", f"{calmar:.3f}")

                        # 추가 메트릭 (VaR/CVaR/승률)
                        col7, col8, col9 = st.columns(3)
                        col7.metric("VaR (95%)", f"{var_95*100:.2f}%")
                        col8.metric("CVaR (95%)", f"{(cvar_95 if not np.isnan(cvar_95) else 0)*100:.2f}%")
                        col9.metric("승률", f"{win_rate*100:.1f}%")

                        # 월별 성과 요약 표
                        monthly_summary = (1 + daily_ret).groupby(pd.Grouper(freq='ME')).prod() - 1
                        if not monthly_summary.empty:
                            ms_df = monthly_summary.to_frame(name='월 수익률').reset_index()
                            ms_df['연도'] = ms_df['date'].dt.year
                            ms_df['월'] = ms_df['date'].dt.month
                            ms_df['월 수익률'] = (ms_df['월 수익률'] * 100).round(2)
                            st.dataframe(
                                ms_df[['연도','월','월 수익률']],
                                use_container_width=True,
                                hide_index=True
                            )

                        # CSV 다운로드 버튼들
                        st.write("")
                        c1, c2 = st.columns(2)
                        with c1:
                            csv_hist = perf_df[['date','total_value'] + (['daily_return'] if has_dr else [])].copy()
                            csv_bytes = csv_hist.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                "성과 이력 CSV 다운로드",
                                data=csv_bytes,
                                file_name=f"performance_history_{start_dt}_{end_dt}.csv",
                                mime='text/csv'
                            )
                        with c2:
                            summary_df = pd.DataFrame([
                                {"항목": "총 수익률", "값": total_return},
                                {"항목": "연환산 수익률", "값": ann_return},
                                {"항목": "연환산 변동성", "값": ann_vol},
                                {"항목": "MDD", "값": mdd},
                                {"항목": "Sharpe Ratio", "값": sharpe},
                                {"항목": "VaR (95%)", "값": var_95},
                                {"항목": "CVaR (95%)", "값": float(0 if np.isnan(cvar_95) else cvar_95)},
                                {"항목": "승률", "값": win_rate},
                            ])
                            csv_sum = summary_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                "요약 메트릭 CSV 다운로드",
                                data=csv_sum,
                                file_name=f"performance_summary_{start_dt}_{end_dt}.csv",
                                mime='text/csv'
                            )
                    except Exception as e:
                        st.warning(f"요약 메트릭 계산 중 오류: {str(e)}")

                    # 벤치마크 비교 (상대 성과)
                    st.write("")
                    with st.expander("벤치마크 비교", expanded=False):
                        bm_name_map = {
                            "S&P500": ["^GSPC"],
                            "KOSPI": ["^KS11"],
                            "나스닥": ["^IXIC"],
                            "다우존스": ["^DJI"],
                            "Nikkei225": ["^N225"],
                        }
                        bm_options = list(bm_name_map.keys())
                        selected_bm = st.multiselect("벤치마크(복수 선택 가능)", bm_options, default=["S&P500"], key="perf_bm_multi")
                        custom_input = st.text_input(
                            "사용자 정의 심볼 (콤마로 여러 개)",
                            value="",
                            help="예: ^GSPC, SPY, 005930.KS",
                            key="perf_bm_custom_multi"
                        )
                        custom_syms = [s.strip() for s in custom_input.split(',') if s.strip()]

                        # 벤치마크 시리즈 수집: {label: pd.Series}
                        bm_series_map = {}
                        # 내장 선택
                        for name in selected_bm:
                            for sym in bm_name_map[name]:
                                try:
                                    df_bm = data_service.fetch_single_stock(sym, pd.to_datetime(start_dt), pd.to_datetime(end_dt))
                                    if df_bm is not None and not df_bm.empty:
                                        s = df_bm['Close'] if 'Close' in df_bm.columns else df_bm.iloc[:,0]
                                        bm_series_map[name] = s.copy()
                                        break
                                except Exception:
                                    continue
                        # 사용자 정의: 각 심볼을 별도 라인으로 추가
                        for sym in custom_syms:
                            try:
                                df_bm = data_service.fetch_single_stock(sym, pd.to_datetime(start_dt), pd.to_datetime(end_dt))
                                if df_bm is not None and not df_bm.empty:
                                    s = df_bm['Close'] if 'Close' in df_bm.columns else df_bm.iloc[:,0]
                                    bm_series_map[sym] = s.copy()
                            except Exception:
                                continue

                        if not bm_series_map:
                            st.info("선택된 벤치마크 데이터를 불러올 수 없습니다.")
                        else:
                            # 누적 수익률 비교 멀티라인
                            fig_cmp = go.Figure()
                            fig_cmp.add_trace(go.Scatter(x=tv_series.index, y=(tv_series/tv_series.iloc[0]-1)*100, name='포트폴리오(%)'))
                            # 상대 메트릭 집계
                            rel_rows = []
                            for label, s in bm_series_map.items():
                                s.index = pd.to_datetime(s.index)
                                common_idx = s.index.intersection(tv_series.index)
                                if len(common_idx) < 3:
                                    continue
                                pv_idx = tv_series.loc[common_idx] / tv_series.loc[common_idx].iloc[0]
                                bm_idx = s.loc[common_idx] / s.loc[common_idx].iloc[0]
                                fig_cmp.add_trace(go.Scatter(x=common_idx, y=(bm_idx-1)*100, name=f'{label}(%)'))

                                # 상대 메트릭 계산
                                pv_dr = pv_idx.pct_change().dropna()
                                bm_dr = bm_idx.pct_change().dropna()
                                com = pv_dr.index.intersection(bm_dr.index)
                                pv_dr = pv_dr.loc[com]
                                bm_dr = bm_dr.loc[com]
                                ann_factor = 252
                                pv_ann = pv_dr.mean()*ann_factor
                                bm_ann = bm_dr.mean()*ann_factor
                                excess = pv_ann - bm_ann
                                corr = pv_dr.corr(bm_dr)
                                te = (pv_dr - bm_dr).std() * np.sqrt(ann_factor)
                                ir = (excess / te) if te > 0 else 0
                                rel_rows.append({
                                    '벤치마크': label,
                                    '초과 수익률(연)': excess,
                                    '상관계수': corr,
                                    '추적오차(연)': te,
                                    '정보비율': ir
                                })

                            fig_cmp.update_layout(title='누적 수익률 비교(%)', xaxis_title='날짜', yaxis_title='수익률(%)', height=350)
                            st.plotly_chart(fig_cmp, use_container_width=True)

                            if rel_rows:
                                rel_df = pd.DataFrame(rel_rows)
                                # 포맷팅 뷰 제공
                                display_rel = rel_df.copy()
                                display_rel['초과 수익률(연)'] = (display_rel['초과 수익률(연)']*100).map(lambda x: f"{x:.2f}%")
                                display_rel['추적오차(연)'] = (display_rel['추적오차(연)']*100).map(lambda x: f"{x:.2f}%")
                                display_rel['상관계수'] = display_rel['상관계수'].map(lambda x: f"{x:.3f}")
                                display_rel['정보비율'] = display_rel['정보비율'].map(lambda x: f"{x:.3f}")
                                st.dataframe(display_rel, use_container_width=True, hide_index=True)

            # 종목 관리 섹션
            st.markdown("---")
            st.subheader("📋 종목 관리")
            
            col1, col2 = st.columns(2)
            
            # 종목 추가
            with col1:
                st.markdown("#### ➕ 종목 추가")
                with st.form("add_investment_form"):
                    symbol = st.text_input('종목 코드 (예: AAPL, 005930.KS)', key='main_symbol')
                    quantity = st.number_input('수량', min_value=0.0, key='main_quantity')
                    purchase_price = st.number_input('매수가', min_value=0.0, key='main_price')
                    purchase_date = st.date_input('매수일', value=datetime.now(), key='main_date')
                    asset_type = st.selectbox(
                        '자산 유형',
                        ['Stock', 'Bond', 'ETF', 'Crypto', 'Cash', 'Commodity'],
                        key='main_asset_type'
                    )
                    submitted = st.form_submit_button('종목 추가', use_container_width=True)
                    
                    if submitted:
                        if add_investment(
                            db,
                            st.session_state.current_portfolio_id,
                            symbol,
                            quantity,
                            purchase_price,
                            purchase_date.strftime('%Y-%m-%d'),
                            asset_type
                        ):
                            st.success('종목이 성공적으로 추가되었습니다!')
                            st.rerun()
            
            # 종목 수정
            with col2:
                st.markdown("#### ✏️ 종목 수정")
                holdings = holdings_repo.get_portfolio_holdings(db, st.session_state.current_portfolio_id)
                if holdings:
                    with st.form("edit_investment_form"):
                        # 수정할 종목 선택
                        holdings_dict = {
                            h.id: f"{h.symbol} ({h.quantity}주, ${h.purchase_price:.2f})" 
                            for h in holdings
                        }
                        selected_holding_id = st.selectbox(
                            "수정할 종목 선택",
                            options=list(holdings_dict.keys()),
                            format_func=lambda x: holdings_dict[x],
                            key='edit_holding_select'
                        )
                        
                        # 선택된 종목 정보 가져오기
                        selected_holding = next(
                            (h for h in holdings if h.id == selected_holding_id), 
                            None
                        )
                        
                        if selected_holding:
                            quantity = st.number_input(
                                '수량',
                                min_value=0.0,
                                value=float(selected_holding.quantity),
                                key='edit_quantity'
                            )
                            purchase_price = st.number_input(
                                '매수가',
                                min_value=0.0,
                                value=float(selected_holding.purchase_price),
                                key='edit_price'
                            )
                            purchase_date = st.date_input(
                                '매수일',
                                value=datetime.strptime(
                                    selected_holding.purchase_date, 
                                    '%Y-%m-%d'
                                ) if selected_holding.purchase_date else datetime.now(),
                                key='edit_date'
                            )
                            asset_type = st.selectbox(
                                '자산 유형',
                                ['Stock', 'Bond', 'ETF', 'Crypto', 'Cash', 'Commodity'],
                                index=['Stock', 'Bond', 'ETF', 'Crypto', 'Cash', 'Commodity'].index(
                                    selected_holding.asset_type
                                ),
                                key='edit_asset_type'
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                submitted = st.form_submit_button(
                                    '종목 수정',
                                    use_container_width=True,
                                    type='primary'
                                )
                            with col2:
                                delete = st.form_submit_button(
                                    '종목 삭제',
                                    use_container_width=True,
                                    type='secondary'
                                )
                            
                            if submitted:
                                if edit_investment(
                                    db,
                                    selected_holding_id,
                                    quantity,
                                    purchase_price,
                                    purchase_date.strftime('%Y-%m-%d'),
                                    asset_type
                                ):
                                    st.success('종목이 성공적으로 수정되었습니다!')
                                    st.rerun()
                            
                            if delete:
                                if holdings_repo.delete_holding(db, selected_holding_id):
                                    st.success('종목이 성공적으로 삭제되었습니다!')
                                    st.rerun()
                else:
                    st.info("수정할 종목이 없습니다. 먼저 종목을 추가해주세요.")
            
            # 구분선
            st.markdown("---")
            
            # 포트폴리오 수정 섹션 추가
            st.subheader("📝 포트폴리오 수정")
            
            # 현재 선택된 포트폴리오 정보 가져오기
            current_portfolio = portfolio_repo.get_portfolio_by_id(db, st.session_state.current_portfolio_id)
            
            if current_portfolio:
                with st.expander("포트폴리오 정보 수정", expanded=True):
                    # 수정 폼
                    with st.form("edit_current_portfolio_form"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**현재 포트폴리오**: {current_portfolio.name}")
                        
                        with col2:
                            st.write(f"생성일: {current_portfolio.created_at}")
                        
                        # 포트폴리오 이름 및 설명 입력 필드
                        new_name = st.text_input(
                            "포트폴리오 이름",
                            value=current_portfolio.name,
                            key="edit_current_portfolio_name"
                        )
                        
                        new_description = st.text_area(
                            "포트폴리오 설명",
                            value=current_portfolio.description or "",
                            key="edit_current_portfolio_desc"
                        )
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            submit_button = st.form_submit_button(
                                "변경사항 저장",
                                use_container_width=True,
                                type="primary"
                            )
                        
                        with col2:
                            delete_button = st.form_submit_button(
                                "포트폴리오 삭제",
                                use_container_width=True,
                                type="secondary"
                            )
                    
                    # 폼 제출 후 처리
                    if submit_button:
                        if not new_name:
                            st.error("포트폴리오 이름을 입력해주세요.")
                        elif new_name == current_portfolio.name and new_description == current_portfolio.description:
                            st.warning("변경된 내용이 없습니다.")
                        else:
                            try:
                                updated = portfolio_repo.update_portfolio(
                                    db,
                                    current_portfolio.id,
                                    new_name,
                                    new_description
                                )
                                if updated:
                                    refresh_portfolios()
                                    st.success(
                                        f"포트폴리오가 '{new_name}'(으)로 업데이트되었습니다."
                                    )
                                    st.rerun()
                                else:
                                    st.error("포트폴리오 업데이트 중 오류가 발생했습니다.")
                            except Exception as e:
                                st.error(f"포트폴리오 업데이트 중 오류 발생: {str(e)}")
                    
                    # 삭제 버튼 처리
                    if delete_button:
                        # 삭제 확인을 위한 추가 UI
                        st.warning("⚠️ 정말로 이 포트폴리오를 삭제하시겠습니까? 모든 보유 종목 정보가 함께 삭제됩니다.")
                        
                        confirm_col1, confirm_col2 = st.columns(2)
                        
                        with confirm_col1:
                            if st.button("예, 삭제합니다", key="confirm_delete_portfolio", type="primary"):
                                if portfolio_repo.delete_portfolio(db, current_portfolio.id):
                                    st.session_state.current_portfolio_id = None
                                    refresh_portfolios()
                                    st.success(f"'{current_portfolio.name}' 포트폴리오가 삭제되었습니다.")
                                    st.rerun()
                                else:
                                    st.error("포트폴리오 삭제 중 오류가 발생했습니다.")
                        
                        with confirm_col2:
                            if st.button("아니오, 취소합니다", key="cancel_delete_portfolio"):
                                st.info("삭제가 취소되었습니다.")
                                st.rerun()
        else:
            st.info("편집할 포트폴리오를 선택해주세요.")

# 포트폴리오 분석 화면
def show_portfolio_analysis():
    st.subheader("📊 포트폴리오 분석")
    
    if not st.session_state.current_portfolio_id:
        st.info("분석할 포트폴리오를 먼저 선택해주세요. 왼쪽 사이드바에서 포트폴리오를 선택하세요.")
        return
        
    # 보유 종목 조회
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            holdings = holdings_repo.get_portfolio_holdings(db, st.session_state.current_portfolio_id)
        finally:
            db.close()
    except Exception as e:
        st.error(f"보유 종목 조회 중 오류가 발생했습니다: {e}")
        return
    
    if not holdings:
        st.info("이 포트폴리오에는 아직 종목이 없습니다. 포트폴리오에 종목을 먼저 추가해주세요.")
        return
    
    # 분석 기간 설정
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "분석 시작 날짜",
            value=datetime.now() - timedelta(days=365),
            max_value=datetime.now() - timedelta(days=1)
        )
    
    with col2:
        end_date = st.date_input(
            "분석 종료 날짜",
            value=datetime.now(),
            min_value=start_date,
            max_value=datetime.now()
        )
    
    # 종목 검증 버튼 추가
    if st.button("분석 시작", key="start_analysis"):
        # 포트폴리오 정보 준비
        symbols = [h.symbol for h in holdings]
        
        # 종목 코드 검증
        invalid_symbols = []
        for symbol in symbols:
            valid, error_msg = validate_ticker(symbol)
            if not valid:
                error_msg = error_msg if error_msg else "종목 코드 검증 실패"
                invalid_symbols.append((symbol, error_msg))
        
        if invalid_symbols:
            st.error("일부 종목 코드가 유효하지 않습니다:")
            for symbol, error_msg in invalid_symbols:
                st.warning(f"• {symbol}: {error_msg}")
            
            st.info("유효하지 않은 종목 코드를 제외하고 분석을 진행하려면 다시 '분석 시작' 버튼을 클릭하세요.")
            
            # 유효하지 않은 종목들을 제외
            valid_symbols = [
                s for s in symbols 
                if s not in [inv[0] for inv in invalid_symbols]
            ]
            if not valid_symbols:
                st.error("유효한 종목이 없습니다. 종목 정보를 수정한 후 다시 시도해주세요.")
                return
            
            symbols = valid_symbols
            # 유효한 종목에 해당하는 holdings만 필터링
            holdings = [h for h in holdings if h.symbol in symbols]
        
        # 히스토리컬 데이터 가져오기
        with st.spinner("데이터를 가져오는 중입니다..."):
            try:
                hist_data = fetch_historical_data(symbols, start_date, end_date)
                
                if hist_data.empty:
                    st.error("히스토리컬 데이터를 가져오는데 실패했습니다. 다음을 확인해보세요:")
                    st.error("1. 인터넷 연결이 안정적인지 확인하세요.")
                    st.error("2. 종목 코드가 정확한지 확인하세요 (예: 미국 주식 'AAPL', 한국 주식 '005930.KS').")
                    st.error("3. 분석 기간을 더 짧게 설정해보세요.")
                    st.error("4. 나중에 다시 시도해보세요. (Yahoo Finance API 일시적 제한일 수 있습니다)")
                    return
            except Exception as e:
                st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {str(e)}")
                st.error("다시 시도하거나 다른 종목을 선택해보세요.")
                return
        
        # 성공적으로 데이터를 가져왔을 때만 아래 코드 실행
        market_values = []
        for h in holdings:
            if h.symbol in hist_data.columns:
                current_price, _ = fetch_current_price(h.symbol)
                market_values.append(h.quantity * (current_price or 0))
            else:
                # 데이터를 가져오지 못한 종목은 0으로 처리
                market_values.append(0)
        
        total_value = sum(market_values)
        weights = [mv / total_value for mv in market_values] if total_value > 0 else [0] * len(symbols)
        
        # 분석 탭 생성
        analysis_tabs = st.tabs([
            "수익률 분석", 
            "위험 지표", 
            "자산 배분", 
            "상관관계 분석", 
            "종목별 성과"
        ])
        
        # 수익률 분석 탭
        with analysis_tabs[0]:
            st.write("### 포트폴리오 수익률")
            
            # 일일 수익률 계산
            daily_returns = calculate_portfolio_returns(hist_data, weights)
            
            # 누적 수익률 계산
            cumulative_returns = (1 + daily_returns).cumprod() - 1
            
            # 벤치마크 지수 (S&P 500) - 데이터 서비스 사용
            try:
                benchmark_series = None
                for sym in ['^GSPC']:
                    df = data_service.fetch_single_stock(sym, start_date, end_date)
                    if df is not None and not df.empty:
                        benchmark_series = df['Close'] if 'Close' in df.columns else df.iloc[:, 0]
                        break
                
                if benchmark_series is None or len(benchmark_series) == 0:
                    st.error("벤치마크 데이터를 가져오는데 실패했습니다.")
                    return
                
                benchmark = benchmark_series
                
                if len(benchmark) == 0:
                    st.error("벤치마크 데이터를 가져오는데 실패했습니다.")
                    return
                
                benchmark_returns = benchmark.pct_change().dropna()
                benchmark_cumulative = (1 + benchmark_returns).cumprod() - 1
                
                # 복잡한 그래프를 그리기 위해 plotly 사용
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=cumulative_returns.index, 
                    y=cumulative_returns.values * 100,
                    mode='lines',
                    name='포트폴리오',
                    line=dict(color='royalblue', width=2)
                ))
                
                fig.add_trace(go.Scatter(
                    x=benchmark_cumulative.index, 
                    y=benchmark_cumulative.values * 100,
                    mode='lines',
                    name='S&P 500',
                    line=dict(color='crimson', width=2, dash='dash')
                ))
                
                fig.update_layout(
                    title='누적 수익률 (%) - 포트폴리오 vs S&P 500',
                    xaxis_title='날짜',
                    yaxis_title='누적 수익률 (%)',
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01
                    ),
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"벤치마크 데이터를 가져오는데 실패했습니다: {str(e)}")
                # 벤치마크 없이 포트폴리오만 표시
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=cumulative_returns.index, 
                    y=cumulative_returns.values * 100,
                    mode='lines',
                    name='포트폴리오',
                    line=dict(color='royalblue', width=2)
                ))
                
                fig.update_layout(
                    title='포트폴리오 누적 수익률 (%)',
                    xaxis_title='날짜',
                    yaxis_title='누적 수익률 (%)',
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # 월별 수익률 표시
            st.write("### 월별 수익률 (%)")
            
            # 날짜 인덱스를 기준으로 월별 수익률 계산
            monthly_returns = daily_returns.groupby(pd.Grouper(freq='ME')).apply(
                lambda x: (1 + x).prod() - 1
            ) * 100
            
            # 월별 수익률 히트맵
            monthly_returns_pivot = monthly_returns.reset_index()
            monthly_returns_pivot['Year'] = monthly_returns_pivot['Date'].dt.year
            monthly_returns_pivot['Month'] = monthly_returns_pivot['Date'].dt.month
            monthly_returns_pivot = monthly_returns_pivot.pivot(index='Year', columns='Month', values=0)
            
            # 월 이름으로 컬럼명 변경
            month_names = {
                1: '1월', 2: '2월', 3: '3월', 4: '4월', 5: '5월', 6: '6월',
                7: '7월', 8: '8월', 9: '9월', 10: '10월', 11: '11월', 12: '12월'
            }
            monthly_returns_pivot.columns = [month_names.get(c, c) for c in monthly_returns_pivot.columns]
            
            # 히트맵 표시
            fig, ax = plt.subplots(figsize=(12, len(monthly_returns_pivot) * 0.8))
            sns.heatmap(
                monthly_returns_pivot,
                annot=True,
                fmt='.2f',
                cmap='RdYlGn',
                center=0,
                linewidths=1,
                ax=ax,
                cbar_kws={'label': '수익률 (%)'}
            )
            plt.title('월별 포트폴리오 수익률 (%)')
            st.pyplot(fig)
        
        # 위험 지표 탭
        with analysis_tabs[1]:
            st.write("### 포트폴리오 위험 지표")
            
            # 위험 지표 계산
            risk_free_rate = 0.02 / 252  # 일일 기준 무위험 수익률 (2% 연간)
            
            risk_metrics = calculate_risk_metrics(daily_returns, risk_free_rate * 252)
            
            # 위험 지표 표시
            col1, col2 = st.columns(2)
            
            with col1:
                metrics_df1 = pd.DataFrame({
                    '지표': ['연간 기대 수익률', '연간 변동성', '총 수익률'],
                    '값': [
                        f"{risk_metrics['연간 기대 수익률']:.2f}%",
                        f"{risk_metrics['연간 변동성']:.2f}%",
                        f"{risk_metrics['총 수익률']:.2f}%"
                    ]
                })
                st.dataframe(metrics_df1, hide_index=True, use_container_width=True)
            
            with col2:
                metrics_df2 = pd.DataFrame({
                    '지표': ['샤프 비율', '소티노 비율', '최대 낙폭'],
                    '값': [
                        f"{risk_metrics['샤프 비율']:.2f}",
                        f"{risk_metrics['소티노 비율']:.2f}",
                        f"{risk_metrics['최대 낙폭']:.2f}%"
                    ]
                })
                st.dataframe(metrics_df2, hide_index=True, use_container_width=True)
            
            # 분포 그래프 표시
            fig = make_subplots(rows=1, cols=2, 
                              subplot_titles=('일일 수익률 분포', '수익률 QQ 플롯'))
            
            # 히스토그램
            fig.add_trace(
                go.Histogram(
                    x=daily_returns * 100,
                    nbinsx=50,
                    name='일일 수익률',
                    marker_color='royalblue'
                ),
                row=1, col=1
            )
            
            # 정규 분포 라인 추가
            x = np.linspace(min(daily_returns * 100), max(daily_returns * 100), 100)
            mu, std = daily_returns.mean() * 100, daily_returns.std() * 100
            pdf = stats.norm.pdf(x, mu, std)
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=pdf * (len(daily_returns) * (max(daily_returns * 100) - min(daily_returns * 100)) / 50),
                    mode='lines',
                    name='정규 분포',
                    line=dict(color='crimson')
                ),
                row=1, col=1
            )
            
            # QQ 플롯 데이터
            theoretical_quantiles = np.sort(stats.norm.rvs(size=len(daily_returns)))
            ordered_returns = np.sort(daily_returns * 100)
            
            fig.add_trace(
                go.Scatter(
                    x=theoretical_quantiles,
                    y=ordered_returns,
                    mode='markers',
                    name='수익률',
                    marker=dict(color='royalblue')
                ),
                row=1, col=2
            )
            
            # 기준선 추가
            min_val = min(theoretical_quantiles.min(), ordered_returns.min())
            max_val = max(theoretical_quantiles.max(), ordered_returns.max())
            fig.add_trace(
                go.Scatter(
                    x=[min_val, max_val],
                    y=[min_val, max_val],
                    mode='lines',
                    name='정규 분포 기준선',
                    line=dict(color='crimson', dash='dash')
                ),
                row=1, col=2
            )
            
            fig.update_layout(
                height=500,
                title_text="포트폴리오 수익률 분석",
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 롤링 변동성 및 샤프 비율
            st.write("### 롤링 지표 (60일)")
            
            # 롤링 변동성 (60일)
            rolling_vol = daily_returns.rolling(window=60).std() * np.sqrt(252) * 100
            
            # 롤링 샤프 비율 (60일)
            rolling_return = daily_returns.rolling(window=60).mean() * 252
            rolling_sharpe = (
                (rolling_return - risk_free_rate * 252) / 
                (daily_returns.rolling(window=60).std() * np.sqrt(252))
            )
            
            # 그래프 그리기
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('롤링 연간 변동성 (%)', '롤링 샤프 비율'),
                vertical_spacing=0.10
            )
            
            fig.add_trace(
                go.Scatter(
                    x=rolling_vol.index,
                    y=rolling_vol.values,
                    mode='lines',
                    name='롤링 변동성',
                    line=dict(color='crimson', width=2)
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=rolling_sharpe.index,
                    y=rolling_sharpe.values,
                    mode='lines',
                    name='롤링 샤프 비율',
                    line=dict(color='royalblue', width=2)
                ),
                row=2, col=1
            )
            
            fig.update_layout(
                height=600,
                hovermode="x unified",
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # 자산 배분 탭
        with analysis_tabs[2]:
            st.write("### 포트폴리오 자산 배분")
            
            # 자산 유형별 분포
            asset_types = [h.asset_type for h in holdings]
            asset_values = market_values
            
            # 자산 유형별 합계
            asset_type_sums = {}
            for asset_type, value in zip(asset_types, asset_values):
                asset_type_sums[asset_type] = asset_type_sums.get(asset_type, 0) + value
            
            # 자산 유형별 분포 파이 차트
            asset_type_df = pd.DataFrame({
                '자산 유형': list(asset_type_sums.keys()),
                '시장 가치': list(asset_type_sums.values())
            })
            
            fig = px.pie(
                asset_type_df,
                values='시장 가치',
                names='자산 유형',
                title='자산 유형별 분포',
                color_discrete_sequence=px.colors.qualitative.Set1
            )
            
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hole=0.4,
                pull=[0.1 if i == asset_type_df['시장 가치'].idxmax() else 0 for i in range(len(asset_type_df))]
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 종목별 분포 트리맵
            holdings_df = pd.DataFrame({
                '종목': [h.symbol for h in holdings],
                '자산 유형': asset_types,
                '시장 가치': market_values
            })
            
            fig = px.treemap(
                holdings_df,
                path=['자산 유형', '종목'],
                values='시장 가치',
                color='자산 유형',
                color_discrete_sequence=px.colors.qualitative.Set1,
                title='종목별 자산 분포'
            )
            
            fig.update_layout(
                margin=dict(t=50, l=25, r=25, b=25)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # 상관관계 분석 탭
        with analysis_tabs[3]:
            st.write("### 종목 간 상관관계 분석")
            
            # 상관관계 매트릭스 계산
            returns_data = hist_data.pct_change().dropna()
            correlation_matrix = returns_data.corr()
            
            # 히트맵으로 상관관계 표시
            fig = px.imshow(
                correlation_matrix,
                text_auto='.2f',
                aspect='auto',
                color_continuous_scale='RdBu_r',
                title='종목 간 상관관계 매트릭스',
                zmin=-1, zmax=1
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 상관관계 설명
            st.write("""
            **상관관계 해석:**
            - **1.0**: 완벽한 양의 상관관계 (두 종목이 항상 같은 방향으로 움직임)
            - **0.0**: 상관관계 없음 (한 종목의 움직임이 다른 종목의 움직임을 예측하는데 도움이 되지 않음)
            - **-1.0**: 완벽한 음의 상관관계 (두 종목이 항상 반대 방향으로 움직임)
            
            **포트폴리오 다각화:**
            - 상관관계가 낮은 종목들을 조합하면 전체 포트폴리오의 위험을 줄일 수 있습니다.
            - 음의 상관관계를 가진 종목들은 시장 변동성을 상쇄하는 효과가 있습니다.
            """)
            
            # PCA를 사용한 종목 관계 시각화
            if len(symbols) >= 3:  # PCA는 최소 3개 이상의 종목이 필요
                st.write("### 종목 간 관계 시각화 (PCA)")
                st.write("주성분 분석(PCA)을 통해 종목 간 관계를 2차원으로 시각화합니다.")
                
                from sklearn.preprocessing import StandardScaler
                from sklearn.decomposition import PCA
                
                # 데이터 준비
                X = StandardScaler().fit_transform(returns_data)
                
                # PCA 수행
                pca = PCA(n_components=2)
                pca_result = pca.fit_transform(X.T)  # 종목을 행으로 변환
                
                # 결과 데이터프레임
                pca_df = pd.DataFrame({
                    '종목': symbols,
                    'PC1': pca_result[:, 0],
                    'PC2': pca_result[:, 1],
                    '자산 유형': asset_types,
                    '비중(%)': [w * 100 for w in weights]
                })
                
                # 모든 컬럼이 사용 가능한 타입인지 확인하여 PyArrow 변환 오류 방지
                pca_df['종목'] = pca_df['종목'].astype(str)
                pca_df['자산 유형'] = pca_df['자산 유형'].astype(str)
                
                # PCA 산점도
                fig = px.scatter(
                    pca_df,
                    x='PC1', y='PC2',
                    text='종목',
                    color='자산 유형',
                    size='비중(%)',
                    size_max=30,
                    title='주성분 분석(PCA)을 통한 종목 관계 시각화',
                    labels={
                        'PC1': f'주성분 1 ({pca.explained_variance_ratio_[0]:.2%})',
                        'PC2': f'주성분 2 ({pca.explained_variance_ratio_[1]:.2%})'
                    }
                )
                
                fig.update_traces(
                    textposition='bottom center',
                    textfont=dict(size=12)
                )
                
                fig.update_layout(
                    height=600,
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="right",
                        x=0.99
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        # 종목별 성과 탭
        with analysis_tabs[4]:
            st.write("### 종목별 성과 분석")
            
            # 종목별 누적 수익률 계산
            stock_returns = hist_data.pct_change().dropna()
            stock_cumulative_returns = (1 + stock_returns).cumprod() - 1
            
            # 종목별 성과 그래프
            fig = go.Figure()
            
            for symbol in symbols:
                # 일부 데이터가 누락될 수 있으므로 확인
                if symbol in stock_cumulative_returns.columns:
                    fig.add_trace(go.Scatter(
                        x=stock_cumulative_returns.index, 
                        y=stock_cumulative_returns[symbol] * 100,
                        mode='lines',
                        name=symbol
                    ))
            
            fig.update_layout(
                title='종목별 누적 수익률 (%)',
                xaxis_title='날짜',
                yaxis_title='누적 수익률 (%)',
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 종목별 성과 표
            performance_metrics = []
            
            for symbol in symbols:
                if symbol in stock_returns.columns:
                    # 종목별 수익률 계산
                    annual_return = stock_returns[symbol].mean() * 252 * 100
                    annual_volatility = stock_returns[symbol].std() * np.sqrt(252) * 100
                    sharpe = annual_return / annual_volatility if annual_volatility > 0 else 0
                    total_return = stock_cumulative_returns[symbol].iloc[-1] * 100
                    
                    # 최대 낙폭 계산
                    cumulative = (1 + stock_returns[symbol]).cumprod()
                    running_max = cumulative.cummax()
                    drawdown = (cumulative - running_max) / running_max
                    max_drawdown = drawdown.min() * 100
                    
                    performance_metrics.append({
                        '종목': symbol,
                        '연간 수익률(%)': annual_return,
                        '연간 변동성(%)': annual_volatility,
                        '샤프 비율': sharpe,
                        '최대 낙폭(%)': max_drawdown,
                        '총 수익률(%)': total_return
                    })
            
            # 데이터프레임으로 변환
            performance_df = pd.DataFrame(performance_metrics)
            
            if not performance_df.empty:
                # 소수점 자리수 설정
                for col in ['연간 수익률(%)', '연간 변동성(%)', '샤프 비율', '최대 낙폭(%)', '총 수익률(%)']:
                    performance_df[col] = performance_df[col].round(2)
                
                # 정렬 (총 수익률 기준)
                performance_df = performance_df.sort_values(by='총 수익률(%)', ascending=False)
                
                st.dataframe(performance_df, hide_index=True, use_container_width=True)
            else:
                st.warning("종목별 성과 지표를 계산할 수 없습니다.")

# 백테스팅 화면 개선 
def show_backtesting():
    st.subheader("📈 포트폴리오 백테스팅")
    
    if not st.session_state.current_portfolio_id:
        st.info("백테스팅할 포트폴리오를 먼저 선택해주세요.")
        return
    
    # 보유 종목 조회
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            holdings = holdings_repo.get_portfolio_holdings(db, st.session_state.current_portfolio_id)
        finally:
            db.close()
    except Exception as e:
        st.error(f"보유 종목 조회 중 오류가 발생했습니다: {e}")
        return
    
    if not holdings:
        st.info("이 포트폴리오에는 아직 종목이 없습니다.")
        return
    
    # 백테스팅 기간 및 초기 설정
    col1, col2, col3 = st.columns(3)
    
    with col1:
        start_date = st.date_input(
            "백테스팅 시작 날짜",
            value=datetime.now() - timedelta(days=365 * 3),
            max_value=datetime.now() - timedelta(days=30)
        )
    
    with col2:
        end_date = st.date_input(
            "백테스팅 종료 날짜",
            value=datetime.now(),
            min_value=start_date + timedelta(days=30),
            max_value=datetime.now()
        )
    
    with col3:
        initial_capital = st.number_input(
            "초기 자본금 ($)",
            min_value=1000,
            value=10000,
            step=1000
        )
    
    # 백테스팅 전략 선택
    strategy_options = [
        "현재 포트폴리오 비중 적용",
        "동일 비중 (Equal Weight)",
        "최소 분산 포트폴리오",
        "주기적 리밸런싱"
    ]
    
    selected_strategy = st.selectbox("백테스팅 전략", strategy_options)
    
    # 전략별 추가 파라미터
    rebalance_period = None
    if selected_strategy == "주기적 리밸런싱":
        rebalance_options = ["월간", "분기별", "반기별", "연간"]
        rebalance_period = st.selectbox("리밸런싱 주기", rebalance_options)
        
        rebalance_map = {
            "월간": 'ME',
            "분기별": 'Q',
            "반기별": '6ME',
            "연간": 'Y'
        }
        rebalance_freq = rebalance_map[rebalance_period]
    
    # 백테스팅 실행 버튼
    if st.button("백테스팅 실행"):
        symbols = [h.symbol for h in holdings]
        quantities = [h.quantity for h in holdings]
        
        # 종목 검증 및 데이터 가져오기
        with st.spinner("데이터를 가져오는 중입니다..."):
            hist_data = fetch_historical_data(symbols, start_date, end_date)
            
            if not hist_data.empty:
                # 포트폴리오 가치 계산
                portfolio_value = initial_capital
                current_quantities = quantities.copy()
                
                # 리밸런싱 날짜 계산
                if selected_strategy == "주기적 리밸런싱":
                    rebalance_dates = pd.date_range(
                        start=start_date,
                        end=end_date,
                        freq=rebalance_freq
                    )
                
                # 여기에 실제 백테스팅 로직 구현
                st.info("백테스팅 기능이 개발 중입니다...")
            else:
                st.error("히스토리컬 데이터를 가져오는데 실패했습니다. 다음을 확인해보세요:")
                st.error("1. 인터넷 연결이 안정적인지 확인하세요.")
                st.error("2. 종목 코드가 정확한지 확인하세요 (예: 미국 주식 'AAPL', 한국 주식 '005930.KS').")
                st.error("3. 백테스팅 기간을 더 짧게 설정해보세요.")
                st.error("4. 나중에 다시 시도해보세요. (Yahoo Finance API 일시적 제한일 수 있습니다)")
                return

# 포트폴리오 앱의 주요 콘텐츠를 렌더링하는 함수
def render_portfolio_content():
    """포트폴리오 콘텐츠를 렌더링합니다."""
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 세션 상태가 없으면 기본값 사용
        current_portfolio_id = getattr(st.session_state, 'current_portfolio_id', None)
        
        if 'portfolios' not in st.session_state:
            st.session_state.portfolios = portfolio_repo.get_all_portfolios(db)

        portfolios = st.session_state.portfolios
        
        # 사이드바에 포트폴리오 선택기 표시
        if portfolios:
            portfolio_names = {p.id: p.name for p in portfolios}
            
            selected_portfolio_id = st.sidebar.selectbox(
                "포트폴리오 선택",
                options=list(portfolio_names.keys()),
                format_func=lambda x: portfolio_names.get(x, "선택 없음"),
                key="sidebar_portfolio_selector",
                index=list(portfolio_names.keys()).index(current_portfolio_id) if current_portfolio_id in portfolio_names else 0
            )
            
            if selected_portfolio_id != current_portfolio_id:
                st.session_state.current_portfolio_id = selected_portfolio_id
                st.rerun()
        else:
            st.sidebar.info("포트폴리오를 생성해주세요.")
        
        # 포트폴리오 생성 UI
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3>새 포트폴리오 생성</h3>", unsafe_allow_html=True)
        with st.sidebar.form("create_portfolio_sidebar_form"):
            name = st.text_input("포트폴리오 이름")
            description = st.text_area("설명 (선택사항)", height=100)
            submitted = st.form_submit_button("포트폴리오 생성", use_container_width=True)
            
            if submitted:
                if not name:
                    st.sidebar.error("포트폴리오 이름을 입력해주세요.")
                else:
                    new_portfolio = portfolio_repo.create_portfolio(db, name, description)
                    if new_portfolio:
                        st.session_state.portfolios = portfolio_repo.get_all_portfolios(db)
                        st.session_state.current_portfolio_id = new_portfolio.id
                        st.sidebar.success(f"'{name}' 포트폴리오가 생성되었습니다.")
                        st.rerun()
                    else:
                        st.sidebar.error("포트폴리오 생성 중 오류가 발생했습니다.")
        
        # 신규 포트폴리오 종목 추가 UI
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3>신규 포트폴리오 종목 추가</h3>", unsafe_allow_html=True)
        with st.sidebar.form("add_new_investment_form"):
            symbol = st.text_input('종목 코드 (예: AAPL, 005930.KS)')
            quantity = st.number_input('수량', min_value=0.0)
            purchase_price = st.number_input('매수가', min_value=0.0)
            purchase_date = st.date_input('매수일', value=datetime.now())
            asset_type = st.selectbox(
                '자산 유형',
                ['Stock', 'Bond', 'ETF', 'Crypto', 'Cash', 'Commodity']
            )
            submitted = st.form_submit_button('종목 추가', use_container_width=True)

            if submitted:
                if not st.session_state.current_portfolio_id:
                    st.sidebar.error("먼저 포트폴리오를 선택해주세요.")
                else:
                    if add_investment(
                        db,
                        st.session_state.current_portfolio_id,
                        symbol,
                        quantity,
                        purchase_price,
                        purchase_date.strftime('%Y-%m-%d'),
                        asset_type
                    ):
                        st.sidebar.success('종목이 성공적으로 추가되었습니다!')
                        st.rerun()

        # 메인 콘텐츠
        if st.session_state.current_portfolio_id:
            portfolio = portfolio_repo.get_portfolio_by_id(db, st.session_state.current_portfolio_id)
            if portfolio:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.header(f"📊 {portfolio.name}")
                    st.write(f"**설명:** {portfolio.description}")
                with col2:
                    st.write("")
                    st.write("")
                    st.info(f"생성일: {portfolio.created_at.strftime('%Y-%m-%d')}\n마지막 수정일: {portfolio.updated_at.strftime('%Y-%m-%d') if portfolio.updated_at else 'N/A'}")
                
                st.subheader("📈 보유 종목 현황")
                show_portfolio_holdings(db)
                st.markdown("---")
            else:
                st.info("포트폴리오를 찾을 수 없습니다. 다른 포트폴리오를 선택해주세요.")
                st.session_state.current_portfolio_id = None

    finally:
        db.close()

