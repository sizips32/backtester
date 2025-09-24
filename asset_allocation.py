import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
from optimization import (
    optimize_minimum_variance,
    optimize_risk_parity,
    optimize_markowitz
)
from services.data_service import data_service

# 데이터베이스 및 리포지토리 import
from utils.database import get_db
from repository.portfolio_repo import get_all_portfolios, get_portfolio_by_id
from repository.target_weights_repo import get_portfolio_target_weights, set_portfolio_target_weights
from repository.holdings_repo import get_portfolio_holdings

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

    # 탭 생성: 저장된 포트폴리오별 + 수동 입력
    tab1, tab2 = st.tabs(["📁 저장된 포트폴리오", "✏️ 수동 입력"])

    with tab1:
        show_saved_portfolio_allocation()

    with tab2:
        show_manual_allocation()

def show_saved_portfolio_allocation():
    """저장된 포트폴리오별 자산 배분 최적화"""
    st.subheader("저장된 포트폴리오 자산 배분 최적화")
    
    # 포트폴리오 목록 새로고침 버튼
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 목록 새로고침", help="포트폴리오 목록을 새로고침합니다", key="allocation_refresh"):
            st.rerun()

    # 저장된 포트폴리오 목록 가져오기
    db = next(get_db())
    try:
        portfolios = get_all_portfolios(db)

        # 목표 비중 또는 보유 종목이 있는 포트폴리오만 필터링
        portfolios_with_data = []
        for portfolio in portfolios:
            weights = get_portfolio_target_weights(db, portfolio.id)
            holdings = get_portfolio_holdings(db, portfolio.id)

            if weights or holdings:
                # 종목 목록 생성 (목표 비중 우선, 없으면 보유 종목)
                symbols = list(weights.keys()) if weights else [h.symbol for h in holdings]
                portfolios_with_data.append({
                    'id': portfolio.id,
                    'name': portfolio.name,
                    'description': portfolio.description,
                    'symbols': symbols,
                    'weights': weights,
                    'holdings': holdings
                })
    finally:
        db.close()

    if not portfolios_with_data:
        st.warning("자산 배분 최적화할 수 있는 포트폴리오가 없습니다. 포트폴리오 관리에서 목표 비중을 설정하거나 종목을 추가해주세요.")
        return

    # 포트폴리오 선택
    portfolio_names = [p['name'] for p in portfolios_with_data]
    selected_portfolio_name = st.selectbox(
        "자산 배분을 최적화할 포트폴리오를 선택하세요:",
        portfolio_names,
        key="allocation_portfolio_selector"
    )

    if not selected_portfolio_name:
        st.stop()

    # 선택된 포트폴리오 정보 가져오기
    selected_portfolio = next(p for p in portfolios_with_data if p['name'] == selected_portfolio_name)
    symbols = selected_portfolio['symbols']

    # 포트폴리오 정보 표시
    st.info(f"**포트폴리오**: {selected_portfolio['name']}")
    if selected_portfolio['description']:
        st.info(f"**설명**: {selected_portfolio['description']}")

    # 분석할 종목 목록 표시
    with st.expander("최적화 대상 종목 확인", expanded=False):
        st.write(f"**최적화 대상 종목** ({len(symbols)}개):")
        for symbol in symbols:
            st.write(f"• {symbol}")

    # 최적화 설정
    st.subheader("최적화 설정")
    col1, col2 = st.columns(2)

    with col1:
        period = st.selectbox(
            "분석 기간",
            ["1개월", "3개월", "6개월", "1년", "3년", "5년"],
            index=3,
            key="saved_allocation_period"
        )

    with col2:
        optimization_method = st.selectbox(
            "최적화 방법",
            ["마코위츠 최적화", "최소분산 포트폴리오", "리스크 패리티", "등가중 포트폴리오"],
            key="saved_allocation_method"
        )

    # 최적화 방법 설명
    with st.expander("선택한 최적화 방법 설명", expanded=False):
        st.markdown(get_strategy_description(optimization_method))

    period_days = {
        "1개월": 30, "3개월": 90, "6개월": 180,
        "1년": 365, "3년": 1095, "5년": 1825
    }

    # 기간 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days[period])

    # 최적화 실행
    if st.button("자산 배분 최적화 실행", type="primary", use_container_width=True, key="saved_allocation_execute"):
        optimize_portfolio_allocation(symbols, optimization_method, start_date, end_date, selected_portfolio)

def optimize_portfolio_allocation(symbols, optimization_method, start_date, end_date, selected_portfolio):
    """포트폴리오 자산 배분 최적화 실행"""
    st.subheader(f"{selected_portfolio['name']} 자산 배분 최적화 결과")

    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # 1. 데이터 수집
        status_text.text("📊 데이터 수집 중...")
        progress_bar.progress(20)

        price_data = pd.DataFrame()
        valid_symbols = []

        for symbol in symbols:
            try:
                df = data_service.fetch_single_stock(symbol, start_date, end_date)
                if df is not None and not df.empty:
                    price_data[symbol] = df['Close'] if 'Close' in df.columns else df.iloc[:, 0]
                    valid_symbols.append(symbol)
                    st.success(f"✅ {symbol}: 데이터 수집 완료")
                else:
                    st.warning(f"⚠️ {symbol}: 데이터 없음")
            except Exception as e:
                st.error(f"❌ {symbol}: {str(e)}")

        if price_data.empty or len(valid_symbols) < 2:
            st.error("최적화를 위해서는 최소 2개 이상의 유효한 종목이 필요합니다.")
            return

        progress_bar.progress(50)

        # 2. 수익률 계산
        status_text.text("📈 수익률 계산 중...")
        returns = price_data.pct_change().dropna()

        progress_bar.progress(70)

        # 3. 최적화 실행
        status_text.text("🔍 포트폴리오 최적화 중...")

        method_mapping = {
            "마코위츠 최적화": "markowitz",
            "최소분산 포트폴리오": "minimum_variance",
            "리스크 패리티": "risk_parity",
            "등가중 포트폴리오": "equal_weight"
        }

        method_key = method_mapping[optimization_method]
        optimal_weights = optimize_portfolio(returns, method_key)

        progress_bar.progress(90)

        # 4. 결과 표시
        status_text.text("📋 결과 표시 중...")

        # 현재 비중 vs 최적 비중 비교
        current_weights = selected_portfolio.get('weights', {})

        comparison_data = []
        for i, symbol in enumerate(valid_symbols):
            current_weight = current_weights.get(symbol, 0) if current_weights else 1/len(valid_symbols)
            optimal_weight = optimal_weights[i]

            comparison_data.append({
                '종목': symbol,
                '현재 비중': f"{current_weight*100:.1f}%",
                '최적 비중': f"{optimal_weight*100:.1f}%",
                '차이': f"{(optimal_weight - current_weight)*100:+.1f}%",
                '권장 조정': '매수' if optimal_weight > current_weight else ('매도' if optimal_weight < current_weight else '유지')
            })

        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True)

        # 최적화 결과 통계
        portfolio_return, portfolio_vol, sharpe_ratio = portfolio_stats(optimal_weights, returns)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("예상 연간 수익률", f"{portfolio_return*100:.2f}%")
        with col2:
            st.metric("예상 연간 변동성", f"{portfolio_vol*100:.2f}%")
        with col3:
            st.metric("Sharpe Ratio", f"{sharpe_ratio:.3f}")

        # 파이 차트로 최적 비중 시각화
        fig = go.Figure(data=[go.Pie(
            labels=valid_symbols,
            values=optimal_weights,
            hole=0.3,
            textinfo='label+percent',
            textposition='auto'
        )])

        fig.update_layout(
            title=f"{optimization_method} - 최적 자산 배분",
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)

        # 포트폴리오에 최적 비중 저장 옵션
        if st.button("최적 비중을 포트폴리오에 저장", use_container_width=True, key="save_optimized_weights"):
            try:
                # 최적 비중을 딕셔너리로 변환
                optimized_weights_dict = {symbol: float(weight) for symbol, weight in zip(valid_symbols, optimal_weights)}

                # 데이터베이스에 저장
                db = next(get_db())
                try:
                    success = set_portfolio_target_weights(db, selected_portfolio['id'], optimized_weights_dict)
                    if success:
                        st.success("✅ 최적 비중이 포트폴리오에 저장되었습니다!")
                    else:
                        st.error("❌ 비중 저장에 실패했습니다.")
                finally:
                    db.close()

            except Exception as e:
                st.error(f"저장 중 오류 발생: {str(e)}")

        progress_bar.progress(100)
        status_text.text("✅ 최적화 완료!")

    except Exception as e:
        st.error(f"최적화 중 오류 발생: {str(e)}")
    finally:
        progress_bar.empty()
        status_text.empty()

def show_manual_allocation():
    """수동 입력 자산 배분 최적화 (기존 코드)"""
    # 자산 입력 받기
    assets_input = st.text_input(
        "분석할 종목코드를 입력하세요 (예: 005930, 000660)",
        value="005930, 000660",
        key="manual_allocation_assets"
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
    
    # 데이터 가져오기 (통합 데이터 서비스 사용)
    data = pd.DataFrame()
    for asset in assets:
        try:
            stock_data = data_service.fetch_single_stock(asset, start_date, end_date)
            if stock_data is None or stock_data.empty:
                st.error(f"{asset}에 대한 데이터가 없습니다.")
                return
            if 'Close' in stock_data.columns:
                data[asset] = stock_data['Close']
            else:
                data[asset] = stock_data.iloc[:, 0]
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
            ["마코위츠 최적화", "최소분산 포트폴리오", "리스크 패리티", "등가중 포트폴리오"],
            key="manual_allocation_method"
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
