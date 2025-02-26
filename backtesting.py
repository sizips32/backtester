import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import FinanceDataReader as fdr
import yfinance as yf
from utils.db import get_portfolio_holdings
# fetch_current_price는 현재 사용하지 않으므로 주석 처리
# from portfolio_app import fetch_current_price
import requests

def convert_ticker_format(ticker):
    """티커 형식을 FinanceDataReader에 맞게 변환"""
    # 한국 주식 티커 변환 (005930.KS -> 005930)
    if ticker.endswith('.KS') or ticker.endswith('.KQ'):
        return ticker.split('.')[0]
    return ticker

@st.cache_data(ttl=3600)  # 1시간 캐시
def fetch_stock_data(ticker, start_date, end_date):
    """주식 데이터 가져오기 (캐시 적용)"""
    try:
        # 티커 형식 변환
        original_ticker = ticker  # 원본 티커 저장
        ticker = convert_ticker_format(ticker)
        
        # 날짜 형식 변환 확인
        if isinstance(start_date, datetime.date):
            start_date = start_date.strftime('%Y-%m-%d')
        if isinstance(end_date, datetime.date):
            end_date = end_date.strftime('%Y-%m-%d')
            
        # 한국 주식인지 확인
        is_korean = (
            (len(ticker) in [6, 7] and ticker.isdigit()) or 
            ticker.endswith('.KS') or 
            ticker.endswith('.KQ')
        )
        
        # 심볼 정리
        if is_korean:
            clean_symbol = ticker.replace('.KS', '').replace('.KQ', '')
        else:
            clean_symbol = ticker.replace('^', '')  # ^GSPC와 같은 특수 심볼 처리
        
        # 1. FinanceDataReader로 데이터 가져오기 시도
        try:
            stock = fdr.DataReader(clean_symbol, start_date, end_date)
            
            if not stock.empty and 'Close' in stock.columns:
                close_series = stock['Close']
                
                if not isinstance(close_series, pd.Series):
                    close_series = pd.Series(close_series)
                    
                # 숫자형 데이터로 변환
                close_series = pd.to_numeric(close_series, errors='coerce')
                
                # NaN 값 제거
                close_series = close_series.dropna()
                
                if not close_series.empty:
                    return close_series
        except Exception as e:
            # 오류 로깅 (실제 표시하지는 않음)
            print(
                f"FinanceDataReader 실패 ({clean_symbol}): {str(e)}"
            )
            pass
        
        # 2. yfinance로 시도 (원본 티커 사용)
        try:
            # 원본 티커로 시도
            ticker_yf = yf.Ticker(original_ticker)
            stock_yf = ticker_yf.history(start=start_date, end=end_date)
            
            if not stock_yf.empty and 'Close' in stock_yf.columns:
                close_series = stock_yf['Close']
                
                if not isinstance(close_series, pd.Series):
                    close_series = pd.Series(close_series)
                    
                # 숫자형 데이터로 변환
                close_series = pd.to_numeric(close_series, errors='coerce')
                
                # NaN 값 제거
                close_series = close_series.dropna()
                
                if not close_series.empty:
                    return close_series
        except Exception as e:
            # 오류 로깅 (실제 표시하지는 않음)
            print(
                f"yfinance 실패 ({original_ticker}): {str(e)}"
            )
            
            # 한국 주식인 경우 .KS 또는 .KQ 접미사 추가 시도
            if (is_korean and 
                not (original_ticker.endswith('.KS') or 
                     original_ticker.endswith('.KQ'))):
                for suffix in ['.KS', '.KQ']:
                    try:
                        test_symbol = f"{clean_symbol}{suffix}"
                        ticker_yf = yf.Ticker(test_symbol)
                        stock_yf = ticker_yf.history(start=start_date, end=end_date)
                        
                        if not stock_yf.empty and 'Close' in stock_yf.columns:
                            close_series = stock_yf['Close']
                            
                            if not isinstance(close_series, pd.Series):
                                close_series = pd.Series(close_series)
                                
                            # 숫자형 데이터로 변환
                            close_series = pd.to_numeric(close_series, errors='coerce')
                            
                            # NaN 값 제거
                            close_series = close_series.dropna()
                            
                            if not close_series.empty:
                                return close_series
                    except Exception:
                        continue
        
        # 3. 대안 방법: yfinance의 download 함수 직접 사용
        try:
            stock_data = yf.download(original_ticker, start=start_date, end=end_date, progress=False)
            
            if not stock_data.empty and 'Close' in stock_data.columns:
                close_series = stock_data['Close']
                
                if not isinstance(close_series, pd.Series):
                    close_series = pd.Series(close_series)
                    
                # 숫자형 데이터로 변환
                close_series = pd.to_numeric(close_series, errors='coerce')
                
                # NaN 값 제거
                close_series = close_series.dropna()
                
                if not close_series.empty:
                    return close_series
        except Exception:
            pass
        
        # 4. 한국 주식인 경우 네이버 금융 API 시도
        if is_korean:
            try:
                naver_data = get_korean_stock_data_from_api(
                    clean_symbol, start_date, end_date
                )
                if naver_data is not None and not naver_data.empty:
                    return naver_data
            except Exception:
                pass
        
        # 모든 방법 실패
        st.warning(f"{original_ticker} 데이터를 가져올 수 없습니다.")
        return None
            
    except Exception as e:
        # HTTP 429 에러 처리 (Too Many Requests)
        if "429" in str(e):
            st.warning(
                f"{ticker}: 너무 많은 요청으로 인해 데이터를 가져올 수 없습니다. "
                f"잠시 후 다시 시도하세요."
            )
        else:
            st.error(f"{ticker} 데이터 로드 실패: {str(e)}")
        return None

def calculate_portfolio_value(data, weights):
    """벡터화된 포트폴리오 가치 계산"""
    if data.empty:
        return pd.Series()
        
    returns = data.pct_change()
    weighted_returns = (returns * pd.Series(weights)).sum(axis=1)
    return (1 + weighted_returns).cumprod()

def calculate_metrics(returns):
    """포트폴리오 성과 지표 계산"""
    # 데이터 유효성 검사
    if returns.empty or len(returns) < 2:
        return {
            "연간 수익률": 0.0,
            "연간 변동성": 0.0,
            "Sharpe Ratio": 0.0,
            "Maximum Drawdown": 0.0,
            "Sortino Ratio": 0.0,
            "Calmar Ratio": 0.0,
            "양수 수익 비율": 0.0
        }
    
    # 기본 지표
    annual_return = returns.mean() * 252
    annual_vol = returns.std() * np.sqrt(252)
    sharpe_ratio = annual_return / annual_vol if annual_vol != 0 else 0
    
    # Maximum Drawdown
    cum_returns = (1 + returns).cumprod()
    rolling_max = cum_returns.expanding().max()
    drawdowns = cum_returns/rolling_max - 1
    max_drawdown = drawdowns.min()
    
    # 추가 지표
    # Sortino 비율 (하락 위험만 고려)
    downside_returns = returns[returns < 0]
    downside_deviation = (
        downside_returns.std() * np.sqrt(252)
        if len(downside_returns) > 0 else 0.0001
    )
    sortino_ratio = (annual_return / downside_deviation 
                     if downside_deviation != 0 else 0)
    
    # Calmar 비율 (최대 낙폭 대비 수익률)
    calmar_ratio = (
        annual_return / abs(max_drawdown)
        if max_drawdown != 0 else 0
    )
    
    # 양수 수익 비율
    positive_days = (
        (returns > 0).sum() / len(returns)
        if len(returns) > 0 else 0
    )
    
    return {
        "연간 수익률": annual_return,
        "연간 변동성": annual_vol,
        "Sharpe Ratio": sharpe_ratio,
        "Maximum Drawdown": max_drawdown,
        "Sortino Ratio": sortino_ratio,
        "Calmar Ratio": calmar_ratio,
        "양수 수익 비율": positive_days
    }

def get_portfolio_data(holdings):
    """포트폴리오 정보 추출"""
    if not holdings or len(holdings) == 0:
        return [], {}
    
    assets = []
    weights = {}
    for holding in holdings:
        ticker = holding['symbol']
        assets.append(ticker)
    
    # 보유 수량을 비중으로 변환
    total_quantity = sum([holding['quantity'] for holding in holdings])
    for holding in holdings:
        ticker = holding['symbol']
        weights[ticker] = (
            holding['quantity'] / total_quantity
            if total_quantity > 0 else 0
        )
    
    return assets, weights

def get_korean_stock_data_from_api(ticker, start_date, end_date):
    """네이버 금융 API를 활용하여 한국 주식 데이터 가져오기 시도"""
    try:
        # 티커에서 숫자만 추출
        ticker_code = ''.join(filter(str.isdigit, ticker))
        
        # 날짜 형식 변환
        if isinstance(start_date, datetime):
            start_date_str = start_date.strftime('%Y%m%d')
        elif isinstance(start_date, str):
            start_date_str = start_date.replace('-', '')
        else:
            start_date_str = datetime.strftime(start_date, '%Y%m%d')
            
        if isinstance(end_date, datetime):
            end_date_str = end_date.strftime('%Y%m%d')
        elif isinstance(end_date, str):
            end_date_str = end_date.replace('-', '')
        else:
            end_date_str = datetime.strftime(end_date, '%Y%m%d')
        
        # 네이버 금융 API URLs
        url = f"https://api.finance.naver.com/siseJson.naver?symbol={ticker_code}&requestType=1&startTime={start_date_str}&endTime={end_date_str}&timeframe=day"
        
        response = requests.get(url)
        
        if response.status_code != 200:
            return None
        
        # 응답 파싱 (네이버 API는 약간 변형된 JSON 형식을 반환)
        content = response.text.strip()
        content = content.replace('\'', '"')
        content = content.replace('null', 'null')
        
        # 데이터 변환
        data_list = []
        for line in content.split('\n'):
            if line.strip().startswith('[') and line.strip().endswith(']'):
                items = eval(line.strip())
                if len(items) >= 5:
                    data_list.append(items)
        
        # 헤더 제거
        if len(data_list) > 0:
            headers = data_list[0]
            data_list = data_list[1:]
            
            # 날짜 및 종가 추출 (인덱스 0: 날짜, 인덱스 4: 종가)
            dates = [item[0] for item in data_list]
            closes = [float(item[4]) for item in data_list]
            
            # Series 생성
            if dates and closes:
                # 날짜 문자열을 datetime으로 변환
                dates = [datetime.strptime(str(date), '%Y%m%d') for date in dates]
                return pd.Series(closes, index=dates)
        
        return None
    except Exception as e:
        print(f"네이버 금융 API 요청 실패: {str(e)}")
        return None

def show_backtesting():
    st.header("포트폴리오 백테스팅")
    
    # 포트폴리오 설정 영역
    st.subheader("포트폴리오 설정")
    
    col1, col2 = st.columns([3, 2])
    with col1:
        # 포트폴리오 선택 옵션
        portfolio_source = st.radio(
            "포트폴리오 데이터 소스",
            ["현재 포트폴리오 사용", "직접 입력"],
            horizontal=True
        )
    
    # 포트폴리오 데이터 초기화
    assets = []
    weights = {}
    
    with col2:
        # 사용할 포트폴리오 선택 (현재 포트폴리오 사용 시)
        if portfolio_source == "현재 포트폴리오 사용":
            if 'current_portfolio_id' not in st.session_state:
                st.warning("먼저 포트폴리오를 선택하세요.")
                return
            
            holdings = get_portfolio_holdings(
                st.session_state.current_portfolio_id
            )
            if not holdings:
                st.warning("현재 포트폴리오에 보유 자산이 없습니다.")
                return
            
            assets, weights = get_portfolio_data(holdings)
            
            # 현재 보유 종목 표시
            st.markdown("#### 현재 포트폴리오 구성")
            weight_df = pd.DataFrame({
                '종목코드': list(weights.keys()),
                '비중(%)': [w * 100 for w in weights.values()]
            })
            st.dataframe(weight_df, hide_index=True)
    
    # 직접 입력 모드
    if portfolio_source == "직접 입력":
        # 자산 선택 입력 방식
        assets_input = st.text_input(
            "테스트할 자산의 티커를 입력하세요 (쉼표로 구분)",
            placeholder="005930,035720,000660",
            help="한국 주식은 종목코드만 입력 (예: 005930), "
                 "미국 주식은 심볼 그대로 입력 (예: AAPL)"
        )
        assets = [ticker.strip() for ticker in assets_input.split(',') 
                  if ticker.strip()]
        
        if not assets:
            st.warning("자산을 입력해주세요.")
            return
        
        # 비중 입력 모드 선택
        weight_mode = st.radio(
            "비중 설정 방법",
            ["동일 비중", "직접 설정"],
            horizontal=True
        )
        
        weights = {}
        
        if weight_mode == "동일 비중":
            # 동일 비중 자동 설정
            equal_weight = 1.0 / len(assets)
            for asset in assets:
                weights[asset] = equal_weight
            
            # 현재 설정된 비중 표시
            weight_df = pd.DataFrame({
                '종목코드': assets,
                '비중(%)': [w * 100 for w in weights.values()]
            })
            st.dataframe(weight_df, hide_index=True)
        else:
            # 직접 비중 설정
            st.markdown("#### 자산 비중 설정 (합계 100%)")
            total_weight = 0
            
            # 화면 공간을 효율적으로 사용하기 위해 3개씩 열 구성
            num_cols = 3
            rows = [
                assets[i:i + num_cols] 
                for i in range(0, len(assets), num_cols)
            ]
            
            for row_assets in rows:
                cols = st.columns(num_cols)
                for i, asset in enumerate(row_assets):
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
                st.warning(
                    f"전체 비중의 합이 {total_weight:.1f}%입니다. "
                    f"100%가 되도록 조정하세요."
                )
    
    # 기간 설정
    st.subheader("백테스트 기간 설정")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        period_option = st.selectbox(
            "기간 선택",
            ["직접 설정", "1년", "3년", "5년", "10년", "전체 기간"]
        )
    
    end_date = datetime.now()
    
    if period_option == "직접 설정":
        with col2:
            start_date = st.date_input(
                "시작일",
                datetime.now() - timedelta(days=365)
            )
        with col3:
            end_date = st.date_input("종료일", datetime.now())
    else:
        # 미리 정의된 기간 설정
        period_days = {
            "1년": 365,
            "3년": 365 * 3,
            "5년": 365 * 5,
            "10년": 365 * 10,
            "전체 기간": 365 * 20  # 최대 20년으로 설정
        }
        start_date = datetime.now() - timedelta(
            days=period_days[period_option]
        )
        with col2:
            st.info(f"시작일: {start_date.date()}")
        with col3:
            st.info(f"종료일: {end_date.date()}")
    
    # 누적 수익률 곡선 표시 여부
    show_cumulative_return = st.checkbox(
        "누적 수익률 곡선 표시",
        value=True,
        help="포트폴리오의 누적 수익률 곡선을 함께 표시합니다"
    )
    
    # 백테스트 실행 버튼
    run_backtest = st.button("백테스트 실행", type="primary")
    
    if not run_backtest:
        return
    
    with st.spinner("백테스트 실행 중..."):
        # 데이터 가져오기
        data = pd.DataFrame()
        
        # 진행 상황을 표시할 프로그레스 바 추가
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        total_assets = len(assets)
        for idx, asset in enumerate(assets):
            progress = int((idx / total_assets) * 100)
            progress_bar.progress(progress)
            progress_text.text(f"데이터 로드 중... ({idx+1}/{total_assets}): {asset}")
            
            try:
                stock_data = fetch_stock_data(asset, start_date, end_date)
                if stock_data is not None:
                    data[asset] = stock_data
            except Exception as e:
                st.error(f"{asset} 데이터를 가져오는데 실패했습니다: {str(e)}")
        
        # 프로그레스 바 완료 및 제거
        progress_bar.progress(100)
        progress_text.empty()
        progress_bar.empty()
        
        if data.empty:
            st.error("유효한 데이터가 없습니다.")
            return
        
        # 데이터 전처리: 누락된 데이터가 많은지 확인
        missing_pct = data.isna().mean().mean() * 100
        if missing_pct > 30:
            st.warning(f"전체 데이터의 {missing_pct:.1f}%가 누락되었습니다. 결과가 부정확할 수 있습니다.")
        
        # 결측치 처리
        data = data.fillna(method='ffill').fillna(method='bfill')
        
        # 최소 행 개수 확인
        if len(data) < 10:
            st.error("분석에 필요한 충분한 데이터가 없습니다.")
            return
        
        # 각 자산의 데이터 범위 확인
        for asset in data.columns:
            valid_data_pct = data[asset].count() / len(data) * 100
            if valid_data_pct < 70:
                st.warning(f"{asset}의 데이터가 {100-valid_data_pct:.1f}% 누락되었습니다.")
        
        # 포트폴리오 가치 계산
        portfolio_value = calculate_portfolio_value(data, weights)
        
        if portfolio_value.empty:
            st.error("포트폴리오 가치를 계산할 수 없습니다.")
            return
        
        # 포트폴리오 수익률 계산
        portfolio_returns = portfolio_value.pct_change().fillna(0)
        portfolio_cumulative_return = (1 + portfolio_returns).cumprod() - 1

        # Series 객체에서 단일 값 추출
        if hasattr(portfolio_cumulative_return, 'iloc'):
            portfolio_end_value = portfolio_cumulative_return.iloc[-1]
        else:
            portfolio_end_value = portfolio_cumulative_return
        
        start_to_end_return = portfolio_end_value * 100
        
        # 성과 지표 계산
        portfolio_returns_for_metrics = portfolio_returns.dropna()
        metrics = calculate_metrics(portfolio_returns_for_metrics)
        
        # 결과 시각화 영역
        st.header("백테스트 결과")
        
        # 1. 포트폴리오 가치 변화 차트
        st.subheader("포트폴리오 가치 변화")
        
        fig = go.Figure()
        
        # 포트폴리오 가치 곡선
        fig.add_trace(go.Scatter(
            x=portfolio_value.index,
            y=portfolio_value.values,
            mode='lines',
            name='포트폴리오',
            line=dict(color='rgb(49, 130, 189)', width=2)
        ))
        
        # 포트폴리오 수익률 계산 및 누적 수익률 표시
        if show_cumulative_return:
            fig.add_trace(go.Scatter(
                x=portfolio_cumulative_return.index,
                y=portfolio_cumulative_return.values,
                mode='lines',
                name='누적 수익률',
                line=dict(color='rgba(220, 20, 60, 0.8)', width=1.5)
            ))
        
        fig.update_layout(
            title="포트폴리오 가치 변화",
            xaxis_title="날짜",
            yaxis_title="상대 가치 (첫날=1)",
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
        
        # 2. 성과 지표 계산
        st.subheader("성과 지표")
        
        # 성과 지표 표시
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "총 수익률", 
                f"{start_to_end_return:.2f}%",
                delta=None
            )
            
        with col2:
            st.metric(
                "연간 수익률", 
                f"{metrics['연간 수익률']:.2f}%",
                delta=None
            )
            
        with col3:
            st.metric(
                "변동성 (연간)", 
                f"{metrics['연간 변동성']:.2f}%",
                delta=None
            )
        
        # 2-1. 주요 성과 지표 표시
        st.subheader("주요 성과 지표")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("연간 수익률", f"{metrics['연간 수익률']:.2%}")
        with col2:
            st.metric("샤프 비율", f"{metrics['Sharpe Ratio']:.2f}")
        with col3:
            st.metric("최대 낙폭(MDD)", f"{metrics['Maximum Drawdown']:.2%}")
        with col4:
            st.metric("소티노 비율", f"{metrics['Sortino Ratio']:.2f}")
        
        # 2-2. 상세 지표 (2개 열로 분할)
        st.subheader("상세 성과 분석")
        col1, col2 = st.columns(2)
        
        # 2-2-1. 수익률 분포 히스토그램
        with col1:
            st.markdown("#### 일간 수익률 분포")
            daily_returns_fig = px.histogram(
                portfolio_returns, 
                nbins=50,
                labels={'value': '일간 수익률', 'count': '빈도'},
                title="일간 수익률 분포",
                color_discrete_sequence=['rgba(49, 130, 189, 0.7)']
            )
            daily_returns_fig.add_vline(
                x=0, 
                line_dash="dash", 
                line_color="red"
            )
            daily_returns_fig.add_vline(
                x=portfolio_returns.mean(), 
                line_dash="dash", 
                line_color="green",
                annotation_text=f"평균: {portfolio_returns.mean():.2%}"
            )
            st.plotly_chart(daily_returns_fig, use_container_width=True)
        
        # 2-2-2. 롤링 변동성
        with col2:
            st.markdown("#### 롤링 변동성 (21일)")
            rolling_vol = portfolio_returns.rolling(21).std() * np.sqrt(252)
            rolling_vol_fig = px.line(
                rolling_vol, 
                labels={'value': '연율화 변동성', 'index': '날짜'},
                title="21일 롤링 변동성",
                color_discrete_sequence=['rgba(189, 30, 30, 0.7)']
            )
            st.plotly_chart(rolling_vol_fig, use_container_width=True)
        
        # 3. 낙폭 분석
        st.subheader("낙폭 분석")
        col1, col2 = st.columns(2)
        
        with col1:
            # 3-1. 낙폭 차트
            cum_returns = (1 + portfolio_returns).cumprod()
            rolling_max = cum_returns.expanding().max()
            drawdowns = (cum_returns/rolling_max - 1) * 100
            
            drawdown_fig = px.area(
                drawdowns, 
                labels={'value': '낙폭 (%)', 'index': '날짜'},
                title="포트폴리오 낙폭",
                color_discrete_sequence=['rgba(189, 30, 30, 0.7)']
            )
            drawdown_fig.update_layout(yaxis={'tickformat': '.1f'})
            st.plotly_chart(drawdown_fig, use_container_width=True)
        
        with col2:
            # 3-2. 낙폭 기간 분석
            st.markdown("#### 낙폭 회복 기간 분석")
            
            # 5% 이상 낙폭 횟수
            drawdown_5pct = int((drawdowns <= -5).sum())
            # 10% 이상 낙폭 횟수
            drawdown_10pct = int((drawdowns <= -10).sum())
            # 20% 이상 낙폭 횟수
            drawdown_20pct = int((drawdowns <= -20).sum())
            
            # 데이터프레임 생성 시 문자열로 변환하여 타입 일관성 유지
            drawdown_data = pd.DataFrame({
                '낙폭 수준': ['5% 이상', '10% 이상', '20% 이상'],
                '발생 횟수': [str(drawdown_5pct), str(drawdown_10pct), str(drawdown_20pct)]
            })
            
            # 차트 생성을 위해 발생 횟수 열을 숫자로 변환
            drawdown_data['발생 횟수'] = pd.to_numeric(drawdown_data['발생 횟수'])
            
            drawdown_bar = px.bar(
                drawdown_data,
                x='낙폭 수준',
                y='발생 횟수',
                title="낙폭 발생 횟수",
                color='낙폭 수준',
                color_discrete_sequence=['#91c8e4', '#4682b4', '#1e3f66']
            )
            st.plotly_chart(drawdown_bar, use_container_width=True)
        
        # 4. 월별 수익률 히트맵
        st.subheader("월별 수익률 분석")
        
        # 데이터가 충분한지 확인
        if len(portfolio_returns) < 30:  # 최소 30일 이상의 데이터가 필요
            st.info("월별 수익률 분석을 위한 충분한 데이터가 없습니다. 더 긴 기간을 선택하세요.")
        else:
            monthly_returns = portfolio_returns.resample('M').apply(
                lambda x: (1 + x).prod() - 1
            )
            
            # 데이터가 있는지 확인
            if not monthly_returns.empty:
                # 연도와 월별로 재구성
                monthly_returns_df = pd.DataFrame(monthly_returns)
                monthly_returns_df['Year'] = monthly_returns_df.index.year
                monthly_returns_df['Month'] = monthly_returns_df.index.month
                
                # 피벗 테이블 생성 전 데이터 확인
                if not monthly_returns_df.empty and len(monthly_returns_df) > 1:
                    monthly_returns_df = monthly_returns_df.pivot_table(
                        index='Year', 
                        columns='Month', 
                        values=0
                    )
                    
                    # 히트맵 생성
                    month_names = [
                        '1월', '2월', '3월', '4월', '5월', '6월', 
                        '7월', '8월', '9월', '10월', '11월', '12월'
                    ]
                    
                    # 컬럼이 있는지 확인
                    if not monthly_returns_df.empty and len(monthly_returns_df.columns) > 0:
                        # 컬럼 이름 변경
                        try:
                            # 컬럼 타입 확인 및 변환
                            monthly_returns_df.columns = pd.to_numeric(
                                monthly_returns_df.columns, errors='coerce'
                            )
                            
                            # 유효한 월 컬럼만 필터링
                            valid_columns = [
                                col for col in monthly_returns_df.columns 
                                if pd.notna(col) and 1 <= col <= 12
                            ]
                            monthly_returns_df = monthly_returns_df[valid_columns]
                            
                            # 컬럼 이름 변경
                            monthly_returns_df.columns = [
                                month_names[int(i)-1] 
                                for i in monthly_returns_df.columns
                                if 1 <= i <= 12
                            ]
                            
                            # 데이터 타입 확인 및 변환
                            monthly_returns_df = monthly_returns_df.astype(float)
                            
                            # 데이터 타입 확인 - NaN이나 무한값 처리
                            monthly_returns_df = monthly_returns_df.fillna(0)
                            monthly_returns_df = monthly_returns_df.replace([np.inf, -np.inf], 0)
                            
                            # 값이 있는지 확인
                            if monthly_returns_df.size == 0:
                                st.info("월별 수익률 데이터가 충분하지 않습니다.")
                                return
                            
                            try:
                                monthly_heatmap = px.imshow(
                                    monthly_returns_df.values,
                                    x=monthly_returns_df.columns,
                                    y=monthly_returns_df.index,
                                    color_continuous_scale='RdYlGn',
                                    labels=dict(x="월", y="년", color="수익률"),
                                    text_auto='.1%',
                                    title="월별 수익률 히트맵"
                                )
                                
                                monthly_heatmap.update_layout(
                                    xaxis_title="월",
                                    yaxis_title="년",
                                    coloraxis_colorbar=dict(title="수익률")
                                )
                                st.plotly_chart(monthly_heatmap, use_container_width=True)
                            except Exception as e:
                                st.warning(f"월별 수익률 차트 생성 중 오류 발생: {str(e)}")
                                st.info("월별 수익률 데이터 형식이 적절하지 않습니다.")
                        except Exception as e:
                            st.warning(f"월별 수익률 차트 생성 중 오류 발생: {str(e)}")
                            st.info("월별 수익률 데이터 형식이 적절하지 않습니다.")
                else:
                    st.info("월별 수익률 데이터가 충분하지 않습니다.")
            else:
                st.info("월별 수익률 데이터가 없습니다.")
        
        # 5. 자산 상관관계 분석
        if len(assets) > 1:
            st.subheader("자산 상관관계 분석")
            
            # 상관관계 행렬 계산
            returns_matrix = data.pct_change().dropna()
            
            # 데이터가 충분한지 확인
            if not returns_matrix.empty and len(returns_matrix) > 5:
                try:
                    correlation_matrix = returns_matrix.corr()
                    
                    # 상관관계 히트맵
                    corr_heatmap = px.imshow(
                        correlation_matrix,
                        text_auto='.2f',
                        color_continuous_scale='RdBu_r',
                        labels=dict(x="종목", y="종목", color="상관계수"),
                        title="자산 간 상관관계"
                    )
                    
                    corr_heatmap.update_layout(
                        xaxis_title="종목",
                        yaxis_title="종목"
                    )
                    st.plotly_chart(corr_heatmap, use_container_width=True)
                    
                    # 평균 상관계수
                    avg_corr = correlation_matrix.values[
                        np.triu_indices(len(correlation_matrix), k=1)
                    ].mean()
                    
                    st.info(
                        f"포트폴리오 내 자산들의 평균 상관계수: {avg_corr:.4f} "
                        f"(낮을수록 분산투자 효과가 큼)"
                    )
                except Exception as e:
                    st.warning(f"상관관계 분석 중 오류 발생: {str(e)}")
                    st.info("상관관계 분석을 위한 데이터 형식이 적절하지 않습니다.")
            else:
                st.info("상관관계 분석을 위한 충분한 데이터가 없습니다.")
        
        # 6. 결론 및 인사이트
        st.subheader("백테스트 요약 및 인사이트")
        
        # 성과 요약
        performance_summary = f"""
        ##### 📊 성과 요약
        - 연간 수익률: **{metrics['연간 수익률']:.2%}**
        - 연간 변동성: **{metrics['연간 변동성']:.2%}**
        - 샤프 비율: **{metrics['Sharpe Ratio']:.2f}**
        - 소티노 비율: **{metrics['Sortino Ratio']:.2f}**
        - 칼마 비율: **{metrics['Calmar Ratio']:.2f}**
        - 최대 낙폭: **{metrics['Maximum Drawdown']:.2%}**
        - 양수 수익일 비율: **{metrics['양수 수익 비율']:.2%}**
        """
        
        # 리스크 평가
        risk_level = "낮음"
        if metrics['연간 변동성'] > 0.15:
            risk_level = "높음"
        elif metrics['연간 변동성'] > 0.10:
            risk_level = "중간"
        
        sharpe_quality = "낮음"
        if metrics['Sharpe Ratio'] > 1.0:
            sharpe_quality = "우수"
        elif metrics['Sharpe Ratio'] > 0.5:
            sharpe_quality = "양호"
        
        risk_summary = f"""
        ##### 🔍 리스크 평가
        - 리스크 수준: **{risk_level}**
        - 리스크 대비 수익: **{sharpe_quality}**
        - 하락장 대응력: **{"우수" if metrics['Maximum Drawdown'] > -0.15 else "개선 필요"}**
        """
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(performance_summary)
        with col2:
            st.markdown(risk_summary) 
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
