import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from scipy import stats
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import FinanceDataReader as fdr

# 데이터베이스 모듈 import
from utils.db import (
    create_portfolio, get_all_portfolios, get_portfolio_by_id,
    update_portfolio, delete_portfolio, add_holding_to_portfolio,
    get_portfolio_holdings, delete_holding, update_holding
)

# 모듈 레벨 초기화 코드는 유지하되 함수 내에서도 초기화하도록 합니다
if 'current_portfolio_id' not in st.session_state:
    st.session_state.current_portfolio_id = None

if 'portfolios' not in st.session_state:
    st.session_state.portfolios = get_all_portfolios()

def refresh_portfolios():
    """포트폴리오 목록을 새로고침"""
    st.session_state.portfolios = get_all_portfolios()

def fetch_current_price(stock):
    """실시간 주가를 가져옵니다."""
    try:
        # 한국 주식인지 확인
        is_korean = (
            (len(stock) in [6, 7] and stock.isdigit()) or 
            stock.endswith('.KS') or 
            stock.endswith('.KQ')
        )
        
        # 심볼 정리
        if is_korean:
            clean_symbol = stock.replace('.KS', '').replace('.KQ', '')
        else:
            clean_symbol = stock.replace('^', '')  # ^GSPC와 같은 특수 심볼 처리
        
        # FinanceDataReader로 현재가 조회
        df = fdr.DataReader(clean_symbol)
        if len(df) > 0:
            return float(df['Close'].iloc[-1]), None
        
        # fdr 실패시 yfinance로 시도
        ticker = yf.Ticker(stock)
        info = ticker.info
        
        if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
            return float(info['regularMarketPrice']), None
        elif 'currentPrice' in info and info['currentPrice'] is not None:
            return float(info['currentPrice']), None
        
        return None, "가격 정보를 가져올 수 없습니다."

    except Exception as e:
        return None, f"오류 발생: {str(e)}"

def fetch_historical_data(symbols, start_date, end_date):
    """여러 종목의 히스토리컬 데이터를 가져옵니다."""
    data = {}
    failures = []
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 세션 상태에 캐시 초기화
    if 'data_cache' not in st.session_state:
        st.session_state.data_cache = {}
    
    cache_key = f"{','.join(sorted(symbols))}_{start_date}_{end_date}"
    
    # 캐시된 데이터가 있으면 사용
    if cache_key in st.session_state.data_cache:
        progress_bar.empty()
        status_text.empty()
        return st.session_state.data_cache[cache_key]
    
    for i, symbol in enumerate(symbols):
        # 진행률 업데이트
        progress_percent = (i / len(symbols))
        progress_bar.progress(progress_percent)
        status_text.text(f"{symbol} 데이터 가져오는 중... ({i+1}/{len(symbols)})")
        
        try:
            # 한국 주식인지 확인
            is_korean = (
                (len(symbol) in [6, 7] and symbol.isdigit()) or 
                symbol.endswith('.KS') or 
                symbol.endswith('.KQ')
            )
            
            # 심볼 정리
            if is_korean:
                clean_symbol = symbol.replace('.KS', '').replace('.KQ', '')
            else:
                clean_symbol = symbol.replace('^', '')  # ^GSPC와 같은 특수 심볼 처리
            
            # FinanceDataReader로 데이터 가져오기
            df = fdr.DataReader(clean_symbol, start_date, end_date)
            if len(df) > 0:
                data[symbol] = df['Close']
                continue
            
            # fdr 실패시 yfinance로 시도
            df = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                progress=False
            )
            
            if len(df) > 0:
                data[symbol] = df['Adj Close']
            else:
                failures.append((symbol, "데이터를 찾을 수 없습니다."))
                
        except Exception as e:
            failures.append((symbol, str(e)))
    
    progress_bar.empty()
    status_text.empty()
    
    if not data:
        if failures:
            st.error("데이터를 가져오는데 실패했습니다:")
            for symbol, reason in failures[:5]:
                st.error(f"• {symbol}: {reason}")
            if len(failures) > 5:
                st.error(f"외 {len(failures)-5}개 종목 실패")
        return pd.DataFrame()
    
    try:
        df = pd.DataFrame(data)
        
        # 결측치 확인 및 처리
        na_percentage = df.isna().mean().mean() * 100
        if na_percentage > 50:
            st.warning(
                f"가져온 데이터의 {na_percentage:.1f}%가 결측치입니다. "
                "결과가 부정확할 수 있습니다."
            )
        
        # NaN 값 처리
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        # 캐시에 저장
        st.session_state.data_cache[cache_key] = df
        
        return df
        
    except Exception as e:
        st.error(f"데이터프레임 생성 중 오류 발생: {str(e)}")
        return pd.DataFrame()

# 포트폴리오 수익률 계산
def calculate_portfolio_returns(hist_data, weights):
    """포트폴리오의 일일 수익률을 계산합니다."""
    # 일일 수익률 계산
    daily_returns = hist_data.pct_change().dropna()
    
    # 포트폴리오 수익률 계산
    portfolio_returns = (daily_returns * weights).sum(axis=1)
    
    return portfolio_returns

# 위험 지표 계산
def calculate_risk_metrics(portfolio_returns, risk_free_rate=0.0):
    """포트폴리오의 위험 지표를 계산합니다."""
    # 연간화 상수
    annualization_factor = 252  # 거래일 기준
    
    # 연간 평균 수익률
    annual_return = portfolio_returns.mean() * annualization_factor
    
    # 연간 표준편차 (변동성)
    annual_volatility = portfolio_returns.std() * np.sqrt(annualization_factor)
    
    # 샤프 비율
    sharpe_ratio = (
        (annual_return - risk_free_rate) / annual_volatility 
        if annual_volatility > 0 else 0
    )
    
    # 최대 낙폭 (MDD)
    cumulative_returns = (1 + portfolio_returns).cumprod()
    rolling_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    # 누적 수익률
    total_return = cumulative_returns.iloc[-1] - 1
    
    # 소티노 비율 (하방 위험 고려)
    downside_returns = portfolio_returns[portfolio_returns < 0]
    downside_deviation = downside_returns.std() * np.sqrt(annualization_factor)
    sortino_ratio = (
        (annual_return - risk_free_rate) / downside_deviation 
        if downside_deviation > 0 else 0
    )
    
    return {
        "연간 기대 수익률": annual_return * 100,
        "연간 변동성": annual_volatility * 100,
        "샤프 비율": sharpe_ratio,
        "소티노 비율": sortino_ratio,
        "최대 낙폭": max_drawdown * 100,
        "총 수익률": total_return * 100
    }

# 포트폴리오 관리 UI
def show_portfolio_management():
    st.subheader("🗂️ 포트폴리오 관리")
    
    # 탭 구성
    tabs = st.tabs(["포트폴리오 목록", "포트폴리오 생성", "포트폴리오 편집"])
    
    # 포트폴리오 목록 탭
    with tabs[0]:
        if not st.session_state.portfolios:
            st.info("생성된 포트폴리오가 없습니다. '포트폴리오 생성' 탭에서 새 포트폴리오를 생성해보세요.")
        else:
            # 포트폴리오 선택 드롭다운
            portfolio_names = {p['id']: p['name'] for p in st.session_state.portfolios}
            
            selected_portfolio = st.selectbox(
                "포트폴리오 선택",
                options=list(portfolio_names.keys()),
                format_func=lambda x: portfolio_names[x],
                key="portfolio_selector"
            )
            
            if selected_portfolio != st.session_state.current_portfolio_id:
                st.session_state.current_portfolio_id = selected_portfolio
                st.rerun()
            
            # 포트폴리오 세부 정보 표시
            if selected_portfolio:
                portfolio = get_portfolio_by_id(selected_portfolio)
                if portfolio:
                    st.markdown(f"### {portfolio['name']}")
                    st.write(f"설명: {portfolio['description']}")
                    st.write(f"생성일: {portfolio['created_at']}")
                    
                    # 포트폴리오 삭제 버튼
                    if st.button("포트폴리오 삭제", key="delete_portfolio"):
                        if delete_portfolio(selected_portfolio):
                            st.session_state.current_portfolio_id = None
                            refresh_portfolios()
                            st.success("포트폴리오가 삭제되었습니다.")
                            st.rerun()
                        else:
                            st.error("포트폴리오 삭제 중 오류가 발생했습니다.")
    
    # 포트폴리오 생성 탭
    with tabs[1]:
        st.write("새 포트폴리오 생성")
        with st.form("create_portfolio_form"):
            name = st.text_input("포트폴리오 이름")
            description = st.text_area("설명 (선택사항)")
            
            submitted = st.form_submit_button("포트폴리오 생성")
            if submitted:
                if not name:
                    st.error("포트폴리오 이름을 입력해주세요.")
                else:
                    new_portfolio_id = create_portfolio(name, description)
                    if new_portfolio_id:
                        refresh_portfolios()
                        st.session_state.current_portfolio_id = new_portfolio_id
                        st.success(f"'{name}' 포트폴리오가 생성되었습니다.")
                        st.rerun()
                    else:
                        st.error("포트폴리오 생성 중 오류가 발생했습니다.")
    
    # 포트폴리오 편집 탭
    with tabs[2]:
        if not st.session_state.portfolios:
            st.info("생성된 포트폴리오가 없습니다. '포트폴리오 생성' 탭에서 새 포트폴리오를 생성해보세요.")
            return

        # 포트폴리오 선택 드롭다운
        portfolio_names = {p['id']: p['name'] for p in st.session_state.portfolios}
        selected_portfolio_id = st.selectbox(
            "수정할 포트폴리오 선택",
            options=list(portfolio_names.keys()),
            format_func=lambda x: portfolio_names[x],
            key="edit_portfolio_selector"
        )
        
        if selected_portfolio_id:
            portfolio = get_portfolio_by_id(selected_portfolio_id)
            if portfolio:
                st.write("---")
                
                # 현재 정보 표시
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"### {portfolio['name']}")
                with col2:
                    st.info(
                        f"생성일: {portfolio['created_at']}\n"
                        f"마지막 수정일: {portfolio['updated_at']}"
                    )
                
                # 수정 폼
                with st.form("edit_portfolio_form"):
                    st.write("#### 포트폴리오 정보 수정")
                    
                    name = st.text_input(
                        "포트폴리오 이름",
                        value=portfolio['name'],
                        help="포트폴리오의 새 이름을 입력하세요"
                    )
                    
                    description = st.text_area(
                        "설명",
                        value=portfolio['description'] or "",
                        height=100,
                        help="포트폴리오에 대한 설명을 입력하세요"
                    )
                    
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col2:
                        submitted = st.form_submit_button(
                            "변경사항 저장",
                            use_container_width=True,
                            type="primary"
                        )
                    
                    if submitted:
                        if not name:
                            st.error("포트폴리오 이름을 입력해주세요.")
                        elif name == portfolio['name'] and description == portfolio['description']:
                            st.warning("변경된 내용이 없습니다.")
                        else:
                            try:
                                if update_portfolio(
                                    portfolio['id'],
                                    name,
                                    description
                                ):
                                    refresh_portfolios()
                                    st.success(
                                        f"'{portfolio['name']}' 포트폴리오가 "
                                        f"'{name}'(으)로 업데이트되었습니다."
                                    )
                                    st.rerun()
                                else:
                                    st.error(
                                        "포트폴리오 업데이트 중 "
                                        "오류가 발생했습니다."
                                    )
                            except Exception as e:
                                st.error(
                                    "포트폴리오 업데이트 중 "
                                    f"오류 발생: {str(e)}"
                                )
                
                # 포트폴리오 삭제 섹션
                st.write("---")
                st.write("#### 포트폴리오 삭제")
                st.warning(
                    "⚠️ 주의: 포트폴리오를 삭제하면 모든 보유 종목 정보도 함께 삭제됩니다. "
                    "이 작업은 되돌릴 수 없습니다."
                )
                
                if st.button(
                    "포트폴리오 삭제",
                    key="delete_portfolio_edit",
                    type="secondary"
                ):
                    if delete_portfolio(portfolio['id']):
                        st.session_state.current_portfolio_id = None
                        refresh_portfolios()
                        st.success(f"'{portfolio['name']}' 포트폴리오가 삭제되었습니다.")
                        st.rerun()
                    else:
                        st.error("포트폴리오 삭제 중 오류가 발생했습니다.")
        else:
            st.info("편집할 포트폴리오를 선택해주세요.")

# 종목 추가 함수
def add_investment(portfolio_id, symbol, quantity, purchase_price, purchase_date, asset_type):
    # 입력값 검증
    error_message = None
    if not symbol:
        error_message = "종목 이름을 입력해주세요."
    elif quantity <= 0:
        error_message = "수량은 0보다 커야 합니다."
    elif purchase_price <= 0:
        error_message = "매수가는 0보다 커야 합니다."

    if error_message:
        st.sidebar.error(error_message)
        return False

    # 주가 정보 가져오기
    try:
        current_price, error_msg = fetch_current_price(symbol)
        if current_price is None:
            st.sidebar.error(error_msg)
            return False

        # 데이터베이스에 저장
        holding_id = add_holding_to_portfolio(
            portfolio_id, 
            symbol, 
            quantity, 
            purchase_price, 
            purchase_date, 
            asset_type
        )
        
        if holding_id:
            return True
        else:
            st.sidebar.error("종목 추가 중 오류가 발생했습니다.")
            return False

    except Exception as e:
        st.sidebar.error(f"종목 정보를 가져오는 중 오류가 발생했습니다: {str(e)}")
        return False

# 종목 편집 함수
def edit_investment(holding_id, quantity, purchase_price, purchase_date, asset_type):
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
        success = update_holding(
            holding_id, 
            quantity, 
            purchase_price, 
            purchase_date, 
            asset_type
        )
        
        if success:
            return True
        else:
            st.error("종목 수정 중 오류가 발생했습니다.")
            return False

    except Exception as e:
        st.error(f"종목 정보 업데이트 중 오류가 발생했습니다: {str(e)}")
        return False

# 포트폴리오 표시
def show_portfolio_holdings():
    if st.session_state.current_portfolio_id:
        st.header('포트폴리오 보유 종목')
        
        # 보유 종목 조회
        holdings = get_portfolio_holdings(st.session_state.current_portfolio_id)
        
        if holdings:
            # 실시간 가격 업데이트
            holdings_data = []
            total_value = 0
            
            with st.spinner("현재가를 가져오는 중..."):
                for holding in holdings:
                    symbol = holding['symbol']
                    current_price = None
                    error_msg = None
                    
                    # 한국 주식 여부 확인
                    is_korean = (
                        (len(symbol) in [6, 7] and symbol.isdigit()) or 
                        symbol.endswith('.KS') or 
                        symbol.endswith('.KQ')
                    )
                    
                    if is_korean:
                        try:
                            clean_symbol = symbol.replace('.KS', '').replace('.KQ', '')
                            df = fdr.DataReader(clean_symbol)
                            if len(df) > 0:
                                current_price = df['Close'].iloc[-1]
                        except Exception:
                            pass
                    
                    # fdr로 실패했거나 해외 주식인 경우
                    if current_price is None:
                        if is_korean and not (
                            symbol.endswith('.KS') or 
                            symbol.endswith('.KQ')
                        ):
                            for suffix in ['.KS', '.KQ']:
                                test_symbol = f"{symbol}{suffix}"
                                price, msg = fetch_current_price(test_symbol)
                                if price is not None:
                                    current_price = price
                                    symbol = test_symbol
                                    break
                        
                        if current_price is None:
                            current_price, error_msg = fetch_current_price(symbol)
                    
                    if current_price is None:
                        st.warning(
                            f"{symbol}: {error_msg or '가격 정보를 가져올 수 없습니다.'}"
                        )
                        current_price = 0
                    
                    market_value = holding['quantity'] * current_price
                    gain_loss = (
                        market_value - 
                        (holding['quantity'] * holding['purchase_price'])
                    )
                    gain_loss_pct = (
                        (gain_loss / 
                         (holding['quantity'] * holding['purchase_price'])) * 100 
                        if holding['purchase_price'] > 0 else 0
                    )
                    
                    total_value += market_value
                    
                    holdings_data.append({
                        'ID': holding['id'],
                        '종목': symbol,
                        '보유수량': holding['quantity'],
                        '매수가': holding['purchase_price'],
                        '현재가': current_price,
                        '시장가치': market_value,
                        '손익': gain_loss,
                        '손익(%)': gain_loss_pct,
                        '자산유형': holding['asset_type'],
                        '매수일': holding['purchase_date'] or '정보 없음'
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
            
            # 포트폴리오 가치 합계 표시
            st.metric("포트폴리오 총 가치", f"${total_value:,.2f}")
            
            # 종목 수정/삭제 섹션
            st.write("---")
            st.subheader("보유 종목 수정")
            
            # 종목 선택
            selected_holding_id = st.selectbox(
                "수정할 종목 선택",
                options=[h['ID'] for h in holdings_data],
                format_func=lambda x: next(
                    h['종목'] for h in holdings_data if h['ID'] == x
                )
            )
            
            if selected_holding_id:
                selected_holding = next(
                    h for h in holdings_data if h['ID'] == selected_holding_id
                )
                
                with st.form("edit_holding_form"):
                    st.write(f"#### {selected_holding['종목']} 수정")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        quantity = st.number_input(
                            "보유수량",
                            min_value=0.0,
                            value=float(selected_holding['보유수량']),
                            step=0.01
                        )
                        
                        purchase_price = st.number_input(
                            "매수가",
                            min_value=0.0,
                            value=float(selected_holding['매수가']),
                            step=0.01
                        )
                    
                    with col2:
                        purchase_date = st.date_input(
                            "매수일",
                            value=datetime.strptime(
                                selected_holding['매수일'], 
                                '%Y-%m-%d'
                            ) if selected_holding['매수일'] != '정보 없음' 
                            else datetime.now()
                        )
                        
                        asset_type = st.selectbox(
                            "자산 유형",
                            options=['Stock', 'Bond', 'ETF', 'Crypto', 'Cash', 'Commodity'],
                            index=['Stock', 'Bond', 'ETF', 'Crypto', 'Cash', 'Commodity'].index(
                                selected_holding['자산유형']
                            )
                        )
                    
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col2:
                        submitted = st.form_submit_button(
                            "변경사항 저장",
                            use_container_width=True,
                            type="primary"
                        )
                    
                    if submitted:
                        if edit_investment(
                            selected_holding_id,
                            quantity,
                            purchase_price,
                            purchase_date.strftime('%Y-%m-%d'),
                            asset_type
                        ):
                            st.success("종목이 성공적으로 수정되었습니다.")
                            st.rerun()
                
                # 종목 삭제 섹션
                st.write("---")
                st.write("#### 종목 삭제")
                st.warning(
                    "⚠️ 주의: 종목을 삭제하면 관련된 모든 정보가 영구적으로 삭제됩니다."
                )
                
                if st.button(
                    "종목 삭제",
                    key=f"delete_holding_{selected_holding_id}",
                    type="secondary"
                ):
                    if delete_holding(selected_holding_id):
                        st.success(
                            f"{selected_holding['종목']} 종목이 삭제되었습니다."
                        )
                        st.rerun()
                    else:
                        st.error("종목 삭제 중 오류가 발생했습니다.")
            
            # 원형 차트로 자산 분포 표시
            st.write("---")
            st.subheader('자산 분포')
            
            valid_data = df[df['시장가치'] > 0].copy()
            if not valid_data.empty:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.pie(
                    valid_data['시장가치'],
                    labels=valid_data['종목'],
                    autopct='%1.1f%%',
                    startangle=90
                )
                ax.axis('equal')
                st.pyplot(fig)
            else:
                st.warning("표시할 자산 분포 데이터가 없습니다.")
        else:
            st.info("포트폴리오에 보유 종목이 없습니다.")
    else:
        st.info("포트폴리오를 먼저 선택해주세요.")

# 포트폴리오 분석 화면
def show_portfolio_analysis():
    st.subheader("📊 포트폴리오 분석")
    
    if not st.session_state.current_portfolio_id:
        st.info("분석할 포트폴리오를 먼저 선택해주세요. 왼쪽 사이드바에서 포트폴리오를 선택하세요.")
        return
        
    # 보유 종목 조회
    holdings = get_portfolio_holdings(st.session_state.current_portfolio_id)
    
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
        symbols = [h['symbol'] for h in holdings]
        
        # 종목 코드 검증
        invalid_symbols = []
        for symbol in symbols:
            valid, error_msg = validate_ticker(symbol)
            if not valid:
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
            holdings = [h for h in holdings if h['symbol'] in symbols]
        
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
            if h['symbol'] in hist_data.columns:
                current_price, _ = fetch_current_price(h['symbol'])
                market_values.append(h['quantity'] * (current_price or 0))
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
            
            # 벤치마크 지수 (S&P 500)
            try:
                # FinanceDataReader로 S&P 500 데이터 가져오기
                benchmark_df = fdr.DataReader('US500', start_date, end_date)
                if len(benchmark_df) > 0:
                    benchmark = benchmark_df['Close']
                    st.success("FinanceDataReader에서 S&P 500 데이터를 성공적으로 가져왔습니다.")
                else:
                    st.warning(
                        "FinanceDataReader에서 S&P 500 데이터를 가져오는데 "
                        "실패했습니다. yfinance로 시도합니다."
                    )
                    # fdr 실패 시 yfinance로 시도
                    benchmark = yf.download(
                        '^GSPC',
                        start=start_date,
                        end=end_date,
                        progress=False
                    )['Adj Close']
                
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
            monthly_returns = daily_returns.groupby(pd.Grouper(freq='M')).apply(
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
            asset_types = [h['asset_type'] for h in holdings]
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
                '종목': [h['symbol'] for h in holdings],
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
    holdings = get_portfolio_holdings(st.session_state.current_portfolio_id)
    
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
            "월간": 'M',
            "분기별": 'Q',
            "반기별": '6M',
            "연간": 'Y'
        }
        rebalance_freq = rebalance_map[rebalance_period]
    
    # 백테스팅 실행 버튼
    if st.button("백테스팅 실행"):
        symbols = [h['symbol'] for h in holdings]
        quantities = [h['quantity'] for h in holdings]
        
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

# 데이터 유효성 검증 함수 강화
def validate_ticker(ticker):
    """종목 코드의 유효성을 검증합니다."""
    if not ticker:
        return False, "종목 코드를 입력해주세요."
    
    try:
        # 먼저 기본 심볼로 시도
        ticker_obj = yf.Ticker(ticker)
        
        # 한국 주식의 경우 접미사 확인
        if not (
            ticker.endswith('.KS') or 
            ticker.endswith('.KQ')
        ) and len(ticker) in [6, 7] and ticker.isdigit():
            # 한국 주식 코드인 경우 접미사 추가 시도
            for suffix in ['.KS', '.KQ']:
                try:
                    test_ticker = yf.Ticker(f"{ticker}{suffix}")
                    test_data = test_ticker.history(period='1d')
                    if len(test_data) > 0:  # empty 대신 len() 사용
                        ticker = f"{ticker}{suffix}"
                        break
                except (ConnectionError, TimeoutError, Exception):
                    continue
        
        # 일반적인 검증 진행
        try:
            info = ticker_obj.info
            
            # 기본 필드 확인
            if 'regularMarketPrice' in info and info.get('regularMarketPrice') is not None:
                return True, None
            # 대체 필드 확인
            elif 'currentPrice' in info and info['currentPrice'] is not None:
                return True, None
            elif 'previousClose' in info and info['previousClose'] is not None:
                return True, None
            
            # 히스토리 데이터로 확인
            test_data = ticker_obj.history(period='1d')
            if len(test_data) > 0:  # empty 대신 len() 사용
                return True, None
                
            return False, "종목 정보를 찾을 수 없습니다."
            
        except Exception as e:
            # info 가져오기 실패, 히스토리로 시도
            try:
                test_data = ticker_obj.history(period='1d')
                if len(test_data) > 0:  # empty 대신 len() 사용
                    return True, None
            except Exception as inner_e:
                return False, f"종목 데이터를 가져올 수 없습니다: {str(inner_e)}"
            
            return False, f"종목 정보를 가져올 수 없습니다: {str(e)}"
        
    except Exception as e:
        error_msg = str(e)
        
        # 일반적인 오류 메시지를 더 사용자 친화적으로 변환
        if "No data found" in error_msg:
            return False, "Yahoo Finance에서 해당 종목의 데이터를 찾을 수 없습니다."
        elif "Invalid ticker" in error_msg:
            return False, "유효하지 않은 종목 코드입니다."
        elif "Connection" in error_msg or "Timeout" in error_msg:
            return False, "네트워크 연결 문제로 종목을 확인할 수 없습니다."
        
        return False, f"종목 검증 중 오류 발생: {error_msg}"

# 포트폴리오 앱의 주요 콘텐츠를 렌더링하는 함수
def render_portfolio_content():
    """포트폴리오 앱의 주요 콘텐츠만 렌더링합니다."""
    # 세션 상태 초기화 - 함수 시작 시점에 반드시 초기화
    if 'current_portfolio_id' not in st.session_state:
        st.session_state.current_portfolio_id = None

    if 'portfolios' not in st.session_state:
        st.session_state.portfolios = get_all_portfolios()
    
    # 메인 타이틀 스타일링
    st.markdown("""
        <h1 style='text-align: center; margin-bottom: 40px;'>
            💰 포트폴리오 백테스터
        </h1>
        <p style='text-align: center; color: #666; margin-bottom: 30px;'>
            효율적인 포트폴리오 관리와 리스크 분석을 위한 올인원 솔루션
        </p>
    """, unsafe_allow_html=True)
    
    # 사이드바 - 포트폴리오 선택
    st.sidebar.markdown("<h3>포트폴리오 선택</h3>", unsafe_allow_html=True)
    
    portfolios = get_all_portfolios()
    portfolio_names = {p['id']: p['name'] for p in portfolios}
    
    if portfolio_names:
        selected_portfolio = st.sidebar.selectbox(
            "포트폴리오",
            options=list(portfolio_names.keys()),
            format_func=lambda x: portfolio_names[x],
            key="sidebar_portfolio_selector"
        )
        
        if selected_portfolio != st.session_state.current_portfolio_id:
            st.session_state.current_portfolio_id = selected_portfolio
            st.rerun()
            
            # 포트폴리오 세부 정보 표시
            if selected_portfolio:
                portfolio = get_portfolio_by_id(selected_portfolio)
                if portfolio:
                    st.markdown(f"### {portfolio['name']}")
                    st.write(f"설명: {portfolio['description']}")
                    st.write(f"생성일: {portfolio['created_at']}")
                    
                    # 포트폴리오 삭제 버튼
                    if st.button("포트폴리오 삭제", key="delete_portfolio"):
                        if delete_portfolio(selected_portfolio):
                            st.session_state.current_portfolio_id = None
                            refresh_portfolios()
                            st.success("포트폴리오가 삭제되었습니다.")
                            st.rerun()
                        else:
                            st.error("포트폴리오 삭제 중 오류가 발생했습니다.")
    else:
        st.sidebar.info("포트폴리오를 생성해주세요.")
    
    # 투자 추가 UI (선택된 포트폴리오가 있을 때만)
    if st.session_state.current_portfolio_id:
        st.sidebar.markdown("---")
        st.sidebar.subheader('투자 추가')
        with st.sidebar.form("investment_form"):
            symbol = st.text_input('종목 이름 (예: AAPL)')
            quantity = st.number_input('수량', min_value=0.0)
            purchase_price = st.number_input('매수가', min_value=0.0)
            purchase_date = st.date_input('매수일', value=datetime.now())
            asset_type = st.selectbox(
                '자산 유형',
                ['Stock', 'Bond', 'ETF', 'Crypto', 'Cash', 'Commodity']
            )
            submitted = st.form_submit_button('추가')

            if submitted:
                if add_investment(
                    st.session_state.current_portfolio_id,
                    symbol,
                    quantity,
                    purchase_price,
                    purchase_date.strftime('%Y-%m-%d'),
                    asset_type
                ):
                    st.success('투자가 성공적으로 추가되었습니다!')
    
    # 메인 콘텐츠
    # 포트폴리오 관리 탭만 표시
    show_portfolio_management()
    if st.session_state.current_portfolio_id:
        show_portfolio_holdings()

# 메인 앱 - 독립 실행 시 호출
def main():
    """독립 실행될 때 호출되는 메인 함수"""
    # 독립적으로 실행될 때만 페이지 설정을 합니다
    st.set_page_config(
        page_title="포트폴리오 백테스터",
        page_icon="💰",
        layout="wide"
    )
    
    # 포트폴리오 앱 콘텐츠 렌더링
    render_portfolio_content()

if __name__ == "__main__":
    main()
