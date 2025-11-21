import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import os
import time
from typing import Optional

# 에러 처리 시스템 import
from utils.error_handler import (
    handle_errors, safe_execute, ErrorRecovery,
    TickerNotFoundError, DataUnavailableError, InsufficientDataError,
    error_handler
)

# 통합 데이터 서비스 import
from services.data_service import data_service
from utils.validators import DataValidator
from config.app_config import get_validation_config
from utils.database import get_db
from repository import portfolio_repo, target_weights_repo, performance_repo

@st.cache_data(ttl=3600)  # 1시간 캐시
def fetch_stock_data(
    ticker: str,
    start_date: datetime,
    end_date: datetime,
    max_retries: int = 3
) -> Optional[pd.Series]:
    """주식 데이터 가져오기 (통합 데이터 서비스 사용)
    
    Args:
        ticker: 종목 코드
        start_date: 시작일
        end_date: 종료일
        max_retries: 최대 재시도 횟수
    
    Returns:
        pd.Series: 종가 데이터. 실패시 None 반환
    """
    try:
        # 통합 데이터 서비스 사용
        stock_data = data_service.fetch_single_stock(
            ticker, start_date, end_date
        )
        
        if stock_data is not None:
            # Close 컬럼만 반환
            if 'Close' in stock_data.columns:
                return stock_data['Close']
            elif len(stock_data.columns) == 1:
                return stock_data.iloc[:, 0]
        
        return None
        
    except Exception as e:
        st.error(f"{ticker} 데이터 로드 실패: {str(e)}")
        return None

from modules.backtesting_engine import BacktestingEngine

def calculate_portfolio_value(data, weights):
    """
    벡터화된 포트폴리오 가치 계산 (BacktestingEngine 위임)
    """
    return BacktestingEngine.calculate_portfolio_value(data, weights)

def calculate_metrics(returns):
    """
    포트폴리오 성과 및 리스크 지표 계산 (BacktestingEngine 위임)
    """
    return BacktestingEngine.calculate_metrics(returns)

def save_portfolio(name, assets, weights):
    """포트폴리오 목표 비중을 DB에 저장"""
    try:
        db = next(get_db())

        # 포트폴리오 생성 또는 가져오기
        portfolio = portfolio_repo.upsert_portfolio(db, name)
        if not portfolio:
            st.error("포트폴리오를 생성/가져오지 못했습니다.")
            db.close()
            return False

        # 목표 비중 저장
        weights_clean = {asset: float(weights[asset]) for asset in assets}
        success = target_weights_repo.set_portfolio_target_weights(db, portfolio.id, weights_clean)

        db.close()

        if not success:
            st.error("포트폴리오 목표 비중 저장에 실패했습니다.")
            return False
        return True
    except Exception as e:
        st.error(f"포트폴리오 저장 중 오류: {str(e)}")
        return False

def get_portfolio_list():
    """목표 비중이 설정된 포트폴리오 이름 목록(DB)"""
    try:
        db = next(get_db())
        portfolios = portfolio_repo.get_all_portfolios(db)

        # 목표 비중이 있는 포트폴리오만 필터링
        portfolios_with_weights = []
        for portfolio in portfolios:
            weights = target_weights_repo.get_portfolio_target_weights(db, portfolio.id)
            if weights:  # 목표 비중이 있는 경우만
                portfolios_with_weights.append(portfolio.name)

        db.close()
        return portfolios_with_weights
    except Exception as e:
        st.error(f"포트폴리오 목록 로드 중 오류: {str(e)}")
        return []

def get_all_portfolio_list():
    """모든 포트폴리오 이름 목록(DB) - 목표 비중 유무와 관계없이"""
    try:
        db = next(get_db())
        portfolios = portfolio_repo.get_all_portfolios(db)
        portfolio_names = [portfolio.name for portfolio in portfolios]
        db.close()
        return portfolio_names
    except Exception as e:
        st.error(f"포트폴리오 목록 로드 중 오류: {str(e)}")
        return []

def load_portfolio(name):
    """저장된 포트폴리오(목표 비중 또는 보유 종목) 불러오기(DB)"""
    try:
        db = next(get_db())

        # 포트폴리오 찾기
        portfolio = portfolio_repo.get_portfolio_by_name(db, name)
        if not portfolio:
            st.error(f"포트폴리오 '{name}'을 찾을 수 없습니다.")
            db.close()
            return None

        # 목표 비중 가져오기
        weights = target_weights_repo.get_portfolio_target_weights(db, portfolio.id)
        
        if weights:
            # 목표 비중이 있는 경우
            db.close()
            return {
                'name': name,
                'assets': list(weights.keys()),
                'weights': weights
            }
        else:
            # 목표 비중이 없는 경우, 보유 종목을 기반으로 동일 비중 설정
            from repository.holdings_repo import get_portfolio_holdings
            holdings = get_portfolio_holdings(db, portfolio.id)
            
            if not holdings:
                st.error("해당 포트폴리오에 목표 비중도 보유 종목도 없습니다.")
                db.close()
                return None
            
            # 보유 종목을 기반으로 동일 비중 설정
            assets = [holding.symbol for holding in holdings]
            equal_weight = 1.0 / len(assets)
            weights = {asset: equal_weight for asset in assets}
            
            db.close()
            return {
                'name': name,
                'assets': assets,
                'weights': weights
            }
    except Exception as e:
        st.error(f"포트폴리오 로드 중 오류: {str(e)}")
        return None

def delete_portfolio(name):
    """포트폴리오 목표 비중 삭제(DB). 포트폴리오 자체는 유지"""
    try:
        db = next(get_db())

        # 포트폴리오 찾기
        portfolio = portfolio_repo.get_portfolio_by_name(db, name)
        if not portfolio:
            st.error(f"포트폴리오 '{name}'을 찾을 수 없습니다.")
            db.close()
            return False

        # 목표 비중 삭제
        result = target_weights_repo.delete_portfolio_target_weights(db, portfolio.id)
        db.close()
        return result
    except Exception as e:
        st.error(f"포트폴리오 삭제 중 오류: {str(e)}")
        return False

def show_backtesting():
    """포트폴리오 백테스팅 페이지"""
    db_gen = get_db()
    db = next(db_gen)
    try:
        # db 세션은 아래 저장/조회 동작에서 사용됩니다.
        # 현재 블록에서는 초기화만 수행합니다.
        pass
    finally:
        db.close()
    # 세션 상태 초기화
    if 'selected_portfolio' not in st.session_state:
        st.session_state['selected_portfolio'] = {
            'assets': [],
            'weights': {},
            'name': '',
            'source': None
        }
    
    st.header("포트폴리오 백테스팅")
    
    # 사이드바에 expander로 백테스팅 설명과 해석 방법 추가
    with st.sidebar:
        st.title("백테스팅 설정")
        
        # 기간 설정
        st.subheader("백테스트 기간")
        
        # 기본 기간 옵션
        period_options = {
            "1년": 365,
            "3년": 365 * 3,
            "5년": 365 * 5,
            "10년": 365 * 10,
            "직접 설정": 0
        }
        
        selected_period = st.selectbox(
            "기간 선택",
            options=list(period_options.keys()),
            index=0
        )
        
        if selected_period == "직접 설정":
            start_date = st.date_input(
                "시작일",
                datetime.now() - timedelta(days=365)
            )
            end_date = st.date_input(
                "종료일",
                datetime.now()
            )
        else:
            end_date = datetime.now().date()
            days = period_options[selected_period]
            start_date = end_date - timedelta(days=days)
            st.info(f"시작일: {start_date.strftime('%Y-%m-%d')}")
            st.info(f"종료일: {end_date.strftime('%Y-%m-%d')}")
        
        st.markdown("---")
        
        st.title("백테스팅 가이드")
        
        # 백테스팅이란?
        with st.expander("백테스팅이란?"):
            st.markdown("""
            백테스팅은 투자 전략이나 포트폴리오의 과거 성과를 시뮬레이션하여 
            해당 전략의 효율성과 위험성을 평가하는 방법입니다.
            
            **백테스팅을 하는 이유:**
            * 투자 전략의 과거 성과 평가
            * 위험 요소 식별 및 평가
            * 포트폴리오 최적화
            * 다양한 시장 상황에서의 성과 비교
            * 투자 의사결정의 신뢰성 확보
            
            백테스팅은 과거 데이터를 기반으로 하므로, 미래 성과를 보장하지는 않습니다. 
            그러나 투자 전략의 강점과 약점을 파악하는 데 유용한 도구입니다.
            """)
        
        # 포트폴리오 가치 변화 해석
        with st.expander("포트폴리오 가치 변화 해석"):
            st.markdown("""
            **포트폴리오 가치 변화 차트**는 초기 투자금액이 1이라고 가정했을 때 
            시간에 따른 포트폴리오 가치의 변화를 보여줍니다.
            
            **해석 방법:**
            * **상승 곡선:** 포트폴리오 가치 증가
            * **하락 곡선:** 포트폴리오 가치 감소
            * **급격한 상승/하락:** 높은 변동성 구간
            * **완만한 곡선:** 안정적인 성과
            
            **주의사항:**
            * 긴 상승 추세 중간의 짧은 하락구간을 주목해서 살펴보세요.
            * 최대 낙폭(Maximum Drawdown) 구간을 확인하세요.
            * 시장 충격 시기에 포트폴리오가 어떻게 반응했는지 체크하세요.
            """)
        
        # 종목 간 상관계수 해석
        with st.expander("종목 간 상관계수 해석"):
            st.markdown("""
            **종목 간 상관계수 히트맵**은 포트폴리오 내 각 자산들 간의 
            가격 움직임 관계를 보여줍니다.
            
            **해석 방법:**
            * **1에 가까운 값(파란색):** 두 자산이 같은 방향으로 움직임
            * **0에 가까운 값(흰색):** 두 자산 간 관계가 약함
            * **-1에 가까운 값(빨간색):** 두 자산이 반대 방향으로 움직임
            
            **포트폴리오 구성 시 활용법:**
            * 다양한 색상(낮은 상관관계)을 가진 자산들로 구성된 포트폴리오가 
              분산투자 효과가 높습니다.
            * 모두 파란색(높은 상관관계)인 포트폴리오는 실제 분산 효과가 낮습니다.
            * 빨간색(음의 상관관계)을 가진 자산들은 시장 충격 시 완충 역할을 할 수 있습니다.
            """)
        
        # 성과 및 리스크 지표 해석
        with st.expander("성과 및 리스크 지표 해석"):
            st.markdown("""
            **수익률 지표:**
            * **연간 수익률:** 연평균 수익률 (높을수록 좋음)
            * **월 평균 수익률:** 월평균 수익률 (높을수록 좋음)
            * **양의 수익 개월 비율:** 전체 기간 중 수익이 발생한 개월 비율 (높을수록 좋음)
            
            **리스크 지표:**
            * **연간 변동성:** 연간 수익률의 표준편차, 변동성의 지표 (낮을수록 안정적)
            * **월간 변동성:** 월간 수익률의 표준편차 (낮을수록 안정적)
            * **Maximum Drawdown:** 최대 낙폭, 최고점에서 최저점까지의 하락 비율 (작을수록 좋음)
            * **VaR (95%):** 95% 신뢰수준에서의 Value at Risk, 하위 5% 수익률 수준 (높을수록 좋음)
            * **CVaR (95%):** 95% VaR 이하 수익률의 평균, 극단적 손실의 평균 (높을수록 좋음)
            
            **효율성 지표:**
            * **Sharpe Ratio:** 단위 위험당 초과수익률 (높을수록 좋음, 1.0 이상이 좋은 수준)
            * **Sortino Ratio:** 하방 위험 대비 수익률 (높을수록 좋음, Sharpe보다 하락위험에 중점)
            * **Calmar Ratio:** 최대 낙폭 대비 연간 수익률 (높을수록 좋음, 낙폭 대비 수익성 평가)
            
            **참고:**
            * 지표들은 상대적으로 평가해야 합니다 (시장 평균, 다른 포트폴리오와 비교)
            * 단기간 백테스트보다 장기간 백테스트가 더 신뢰할 수 있습니다.
            * 지나치게 높은 수익률과 낮은 변동성은 과적합(overfitting)일 수 있으니 주의하세요.
            """)
        
        # 월별 수익률 히트맵 해석
        with st.expander("월별 수익률 히트맵 해석"):
            st.markdown("""
            **월별 수익률 히트맵**은 각 연도의 월별 수익률을 색상으로 표현한 차트입니다.
            
            **해석 방법:**
            * **초록색:** 양의 수익률 (진할수록 높은 수익)
            * **빨간색:** 음의 수익률 (진할수록 큰 손실)
            * **노란색:** 수익률이 0에 가까움
            
            **활용법:**
            * 특정 월이나 시즌별 패턴이 있는지 확인하세요.
            * 경제 위기 기간에 포트폴리오가 어떻게 반응했는지 확인하세요.
            * 연도별 성과 패턴을 비교해보세요.
            * 일관된 수익 패턴과 심한 손실 구간을 파악하세요.
            """)
            
    # 백테스팅에 사용할 데이터를 세션 상태로 관리 (상단에서 이미 초기화됨)
    
    # 탭 생성: 포트폴리오 선택/생성
    tab1, tab2 = st.tabs(["기존 포트폴리오 선택", "새 포트폴리오 생성"])
    
    # 기존 포트폴리오 선택 탭
    with tab1:
        st.subheader("포트폴리오 관리에 저장된 포트폴리오")
        
        # 포트폴리오 목록 새로고침 버튼
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 목록 새로고침", help="포트폴리오 목록을 새로고침합니다", key="backtest_refresh"):
                st.rerun()
        
        # 모든 포트폴리오 목록 가져오기
        all_portfolios = get_all_portfolio_list()
        
        if not all_portfolios:
            st.info("저장된 포트폴리오가 없습니다. 새 포트폴리오를 생성해주세요.")
        else:
            # 모든 포트폴리오 정보를 테이블로 표시
            all_portfolios_data = []
            for p_name in all_portfolios:
                p_data = load_portfolio(p_name)
                if p_data:
                    # 자산과 비중을 문자열로 변환
                    assets_str = ", ".join(p_data['assets'])
                    
                    # weights_str 생성 로직 개선
                    weights_parts = []
                    for asset in p_data['assets']:
                        weight_percent = p_data['weights'][asset] * 100
                        weights_parts.append(f"{asset}: {weight_percent:.1f}%")
                    
                    weights_str = ", ".join(weights_parts)
                    
                    all_portfolios_data.append({
                        "포트폴리오 이름": p_name,
                        "보유 종목": assets_str,
                        "비중": weights_str
                    })
            
            # 포트폴리오 목록 테이블 표시
            if all_portfolios_data:
                portfolios_df = pd.DataFrame(all_portfolios_data)
                # 모든 컬럼이 문자열 타입인지 확인하여 PyArrow 변환 오류 방지
                for col in portfolios_df.columns:
                    portfolios_df[col] = portfolios_df[col].astype(str)
                st.dataframe(portfolios_df, use_container_width=True, hide_index=True)
            
            # 포트폴리오 선택
            selected_portfolio = st.selectbox(
                "백테스팅할 포트폴리오 선택",
                options=all_portfolios,
                index=0,
                key="existing_portfolio_select"
            )
            
            # 포트폴리오 불러오기
            loaded_portfolio = load_portfolio(selected_portfolio)
            
            if loaded_portfolio:
                st.success(f"포트폴리오 '{selected_portfolio}'를 불러왔습니다.")
                
                # 포트폴리오 정보 표시
                st.subheader(f"포트폴리오 정보: {loaded_portfolio['name']}")
                
                # 비중 정보 표시
                weights_df = pd.DataFrame({
                    '자산': loaded_portfolio['assets'],
                    '비중(%)': [loaded_portfolio['weights'][asset] * 100 
                               for asset in loaded_portfolio['assets']]
                })
                
                # 비중 정보 설명 추가
                total_weight = sum(loaded_portfolio['weights'].values())
                if abs(total_weight - 1.0) < 0.01:
                    st.info("✅ 목표 비중이 설정된 포트폴리오입니다.")
                else:
                    st.info("ℹ️ 보유 종목을 기반으로 동일 비중으로 설정된 포트폴리오입니다.")
                
                # 2열 레이아웃으로 표시
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # 파이 차트로 시각화
                    fig_pie = px.pie(
                        weights_df, 
                        values='비중(%)', 
                        names='자산',
                        title='포트폴리오 자산 비중',
                        hover_data=['비중(%)'],
                        labels={'비중(%)': '비중 (%)'}
                    )
                    fig_pie.update_traces(
                        textposition='inside', 
                        textinfo='percent+label'
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    # 비중 테이블 표시 (정렬 기능 추가)
                    st.subheader("자산별 비중")
                    sorted_weights_df = weights_df.sort_values(by='비중(%)', ascending=False)
                    # 먼저 데이터 변환 후 새 DataFrame 생성
                    formatted_weights_df = sorted_weights_df.copy()
                    formatted_weights_df['비중(%)'] = formatted_weights_df['비중(%)'].apply(
                        lambda x: f"{x:.1f}%"
                    )
                    st.dataframe(
                        formatted_weights_df,
                        use_container_width=True,
                        hide_index=True
                    )

                # 목표 비중 바로 편집 UI
                if st.button("🎯 목표 비중 바로 편집", key="bt_toggle_edit_weights"):
                    st.session_state['bt_edit_weights_open'] = not st.session_state.get('bt_edit_weights_open', False)

                with st.expander("목표 비중 편집", expanded=st.session_state.get('bt_edit_weights_open', False)):
                    try:
                        # 현재 목표 비중 로드
                        db_temp = next(get_db())
                        portfolio_temp = portfolio_repo.get_portfolio_by_name(db_temp, selected_portfolio)
                        current_weights = {}
                        if portfolio_temp:
                            current_weights = target_weights_repo.get_portfolio_target_weights(db_temp, portfolio_temp.id) or {}
                        db_temp.close()
                        if not current_weights:
                            # 로드된 포트폴리오의 가중치로 초기화
                            current_weights = loaded_portfolio['weights']

                        tv = get_validation_config()
                        st.caption(
                            f"가중치 합계는 100%여야 하며 허용 오차는 ±{int(tv.weight_tolerance*100)}% 입니다."
                        )

                        weights_df_edit = pd.DataFrame(
                            [
                                {"자산": sym, "비중(%)": round(w*100, 2)}
                                for sym, w in current_weights.items()
                            ]
                        )
                        if weights_df_edit.empty:
                            weights_df_edit = pd.DataFrame([{"자산": "", "비중(%)": 0.0}])

                        edited_df = st.data_editor(
                            weights_df_edit,
                            num_rows="dynamic",
                            use_container_width=True,
                            hide_index=True,
                            key="bt_target_weights_editor"
                        )

                        ca, cb = st.columns(2)
                        with ca:
                            if st.button("정규화(합계 100%)", key="bt_normalize_weights"):
                                df = edited_df.copy()
                                df['자산'] = df['자산'].astype(str).str.strip()
                                df = df[df['자산'] != ""]
                                total = df['비중(%)'].astype(float).sum()
                                if total > 0:
                                    df['비중(%)'] = df['비중(%)'].astype(float) / total * 100
                                    st.session_state['bt_target_weights_editor'] = df
                                    st.rerun()
                                else:
                                    st.warning("정규화할 값이 없습니다.")
                        with cb:
                            if st.button("저장", key="bt_save_target_weights", type="primary"):
                                df = edited_df.copy()
                                df['자산'] = df['자산'].astype(str).str.strip()
                                df = df[df['자산'] != ""]
                                if df.empty:
                                    st.error("최소 1개 이상의 자산을 입력하세요.")
                                elif df['자산'].duplicated().any():
                                    st.error("중복된 자산이 있습니다. 중복을 제거해주세요.")
                                else:
                                    try:
                                        # 벡터화 연산으로 성능 개선
                                        weights_new = dict(zip(df['자산'], df['비중(%)'].astype(float) / 100.0))
                                    except Exception:
                                        st.error("비중(%)는 숫자여야 합니다.")
                                        st.stop()

                                    validator = DataValidator()
                                    valid, errors = validator.validate_portfolio_weights(weights_new)
                                    if not valid:
                                        for err in errors:
                                            st.error(err)
                                    else:
                                        if not portfolio_temp:
                                            st.error("포트폴리오 정보를 찾을 수 없습니다.")
                                        else:
                                            db_save = next(get_db())
                                            ok = target_weights_repo.set_portfolio_target_weights(db_save, portfolio_temp.id, weights_new)
                                            db_save.close()
                                            if ok:
                                                st.success("목표 비중이 저장되었습니다.")
                                                # 세션 상태 갱신
                                                st.session_state.selected_portfolio = {
                                                    'assets': list(weights_new.keys()),
                                                    'weights': weights_new,
                                                    'name': selected_portfolio,
                                                    'source': 'existing'
                                                }
                                                st.rerun()
                                            else:
                                                st.error("목표 비중 저장에 실패했습니다.")
                    except Exception as e:
                        st.error(f"목표 비중 편집 중 오류: {str(e)}")
                
                # 백테스팅 선택 버튼
                if st.button("이 포트폴리오로 백테스팅 실행", key="run_existing"):
                    st.session_state.selected_portfolio = {
                        'assets': loaded_portfolio['assets'],
                        'weights': loaded_portfolio['weights'],
                        'name': loaded_portfolio['name'],
                        'source': 'existing'
                    }
                
                # 삭제 기능
                if st.button(f"'{selected_portfolio}' 포트폴리오 삭제"):
                    if delete_portfolio(selected_portfolio):
                        st.success(f"포트폴리오 '{selected_portfolio}'가 삭제되었습니다.")
                        # 세션 상태 초기화
                        is_same_portfolio = (
                            st.session_state.selected_portfolio['source'] == 'existing' and
                            st.session_state.selected_portfolio['name'] == selected_portfolio
                        )
                        
                        if is_same_portfolio:
                            st.session_state.selected_portfolio = {
                                'assets': [],
                                'weights': {},
                                'name': '',
                                'source': None
                            }
                        st.rerun()
    
    # 새 포트폴리오 생성 탭
    with tab2:
        st.subheader("새 포트폴리오 생성")
        # 포트폴리오 이름 입력
        new_portfolio_name = st.text_input("새 포트폴리오 이름", key="new_name")
        
        # 자산 선택 입력 방식
        assets_input = st.text_input(
            "테스트할 자산의 티커를 입력하세요 (쉼표로 구분, 예: 005930,AAPL)",
            value="005930",
            key="new_assets_input"
        )
        new_assets = [ticker.strip() for ticker in assets_input.split(',') 
                     if ticker.strip()]
        
        if not new_assets:
            st.warning("자산을 입력해주세요.")
        else:
            # 비중 입력 방식 개선
            st.subheader("자산 비중 설정")
            
            # 비중 입력 방식 선택
            weight_method = st.radio(
                "비중 설정 방식",
                options=["수동으로 각 자산 비중 설정", "동일 비중으로 설정"],
                index=0,
                key="weight_method"
            )
            
            new_weights = {}
            total_weight = 0
            
            if weight_method == "동일 비중으로 설정":
                # 각 자산에 동일한 비중 할당
                equal_weight = 100 / len(new_assets)
                for asset in new_assets:
                    new_weights[asset] = equal_weight / 100
                    total_weight = 100
                    
                    # 비중 정보 표시
                    st.info(f"각 자산에 {equal_weight:.1f}%의 동일한 비중이 할당되었습니다.")
                
                # 비중 테이블 표시
                weights_df = pd.DataFrame({
                    '자산': new_assets,
                    '비중(%)': [new_weights[asset] * 100 for asset in new_assets]
                })
                # 데이터 포맷팅을 미리 수행
                formatted_weights_df = weights_df.copy()
                formatted_weights_df['비중(%)'] = formatted_weights_df['비중(%)'].apply(
                    lambda x: f"{x:.1f}%"
                )
                st.dataframe(
                    formatted_weights_df,
                    use_container_width=True,
                    hide_index=True
                )
                
            else:  # 수동 입력
                st.info("각 자산의 비중을 수동으로 설정합니다. 전체 합이 100%가 되어야 합니다.")
                
                # 슬라이더 또는 숫자 입력 선택
                input_type = st.radio(
                    "입력 방식",
                    options=["슬라이더로 입력", "숫자로 입력"],
                    index=0
                )
                
                if input_type == "슬라이더로 입력":
                    # 슬라이더로 비중 입력
                    remainder = 100
                    for i, asset in enumerate(new_assets[:-1]):  # 마지막 자산 제외
                        max_val = min(100, remainder)
                        weight = st.slider(
                            f"{asset} 비중 (%)",
                            min_value=0,
                            max_value=int(max_val),
                            value=min(int(100 / len(new_assets)), int(max_val)),
                            step=1,
                            key=f"slider_{asset}"
                        )
                        new_weights[asset] = weight / 100
                        remainder -= weight
                        total_weight += weight
                    
                    # 마지막 자산은 나머지 비중으로 자동 설정
                    last_asset = new_assets[-1]
                    new_weights[last_asset] = remainder / 100
                    total_weight += remainder
                    st.info(f"마지막 자산 {last_asset}의 비중은 {remainder:.1f}%로 자동 설정되었습니다.")
                    
                else:  # 숫자로 입력
                    cols = st.columns(len(new_assets))
                    for i, asset in enumerate(new_assets):
                        with cols[i]:
                            weight = st.number_input(
                                f"{asset} 비중 (%)",
                                min_value=0,
                                max_value=100,
                                value=100 // len(new_assets),
                                step=1,
                                key=f"new_weight_{asset}"
                            )
                            new_weights[asset] = weight / 100
                            total_weight += weight
            
            # 비중 합계 검증
            if abs(total_weight - 100) > 0.01 and weight_method != "동일 비중으로 설정":
                error_msg = "전체 비중의 합이 100%가 되어야 합니다. " 
                error_msg += f"현재 합계: {total_weight:.1f}%"
                st.error(error_msg)
            else:
                # 비중 차트 표시
                weights_df = pd.DataFrame({
                    '자산': list(new_weights.keys()),
                    '비중(%)': [w * 100 for w in new_weights.values()]
                })
                
                fig_pie = px.pie(
                    weights_df,
                    values='비중(%)',
                    names='자산',
                    title='새 포트폴리오 자산 비중'
                )
                fig_pie.update_traces(
                    textposition='inside', 
                    textinfo='percent+label'
                )
                st.plotly_chart(fig_pie)
                
                col1, col2 = st.columns(2)
                with col1:
                    # 백테스팅 선택 버튼
                    if st.button("이 설정으로 백테스팅 실행", key="run_new"):
                        st.session_state.selected_portfolio = {
                            'assets': new_assets,
                            'weights': new_weights,
                            'name': (new_portfolio_name 
                                    if new_portfolio_name 
                                    else "임시 포트폴리오"),
                            'source': 'new'
                        }
                
                with col2:
                    # 저장 버튼
                    save_disabled = not new_portfolio_name
                    if save_disabled:
                        st.warning("포트폴리오를 저장하려면 이름을 입력하세요.")
                    
                    if not save_disabled and st.button("포트폴리오 저장", key="save_new"):
                        if save_portfolio(new_portfolio_name, new_assets, new_weights):
                            st.success(f"포트폴리오 '{new_portfolio_name}'가 저장되었습니다.")
                            # 세션 상태 업데이트
                            st.session_state.selected_portfolio = {
                                'assets': new_assets,
                                'weights': new_weights,
                                'name': new_portfolio_name,
                                'source': 'new'
                            }
                            # 포트폴리오 목록 새로고침을 위한 플래그 설정
                            st.session_state.portfolio_list_updated = True
                            st.rerun()
    
    # 선택된 포트폴리오가 없는 경우
    if not st.session_state.selected_portfolio['assets']:
        st.info("백테스팅을 실행하려면 포트폴리오를 선택하거나 새로 만드세요.")
        return
    
    # 여기서부터는 선택된 포트폴리오로 백테스팅 실행
    st.markdown("---")
    st.subheader(f"백테스트 대상: {st.session_state.selected_portfolio['name']}")
    
    # 현재 선택된 포트폴리오 정보 표시 (파이 차트 제거)
    weights_df = pd.DataFrame({
        '자산': st.session_state.selected_portfolio['assets'],
        '비중(%)': [st.session_state.selected_portfolio['weights'][asset] * 100 
                  for asset in st.session_state.selected_portfolio['assets']]
    })
    
    # 간략한 표 형태로 비중 정보 표시
    weights_formatted = weights_df.sort_values(by='비중(%)', ascending=False).copy()
    weights_formatted['비중(%)'] = weights_formatted['비중(%)'].apply(
        lambda x: f"{x:.1f}%"
    )
    st.dataframe(
        weights_formatted,
        use_container_width=True,
        hide_index=True
    )
    
    # 데이터 가져오기
    with st.spinner("데이터를 불러오는 중..."):
        data = pd.DataFrame()
        assets = st.session_state.selected_portfolio['assets']
        weights = st.session_state.selected_portfolio['weights']
        
        for asset in assets:
            try:
                stock_data = fetch_stock_data(asset, start_date, end_date)
                if stock_data is not None:
                    data[asset] = stock_data
            except Exception as e:
                st.error(f"{asset} 데이터를 가져오는데 실패했습니다: {str(e)}")
                return
    
    if data.empty:
        st.error("데이터를 가져오는데 실패했습니다.")
        return
    
    # 포트폴리오 가치 계산
    portfolio_value = calculate_portfolio_value(data, weights)
    
    # 결과 시각화
    st.header("백테스트 결과")
    
    # 1. 포트폴리오 가치 변화 차트
    st.subheader("1. 포트폴리오 가치 변화")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=portfolio_value.index,
        y=portfolio_value.values,
        mode='lines',
        name='포트폴리오 가치'
    ))
    fig.update_layout(
        title="포트폴리오 가치 변화",
        xaxis_title="날짜",
        yaxis_title="가치 (초기 투자 = 1)",
        template="plotly_white",
        showlegend=True,
        height=600
    )
    st.plotly_chart(fig, use_container_width=True, theme=None)
    
    # 2. 종목 간 상관계수 히트맵
    st.subheader("2. 종목 간 상관계수")
    # 일별 수익률로 상관계수 계산
    daily_returns = data.pct_change().dropna()
    correlation_matrix = daily_returns.corr()
    
    # 상관계수 히트맵 생성
    fig_corr = go.Figure(data=go.Heatmap(
        z=correlation_matrix.values,
        x=correlation_matrix.columns,
        y=correlation_matrix.index,
        colorscale='RdBu_r',  # Red Blue reversed
        zmin=-1, zmax=1,
        colorbar=dict(title="상관계수"),
        hoverongaps=False
    ))
    fig_corr.update_layout(
        title="종목 간 상관계수 히트맵",
        xaxis_title="종목",
        yaxis_title="종목",
        template="plotly_white",
        height=600
    )
    st.plotly_chart(fig_corr, use_container_width=True, theme=None)
    
    # 3. 포트폴리오 성과 및 리스크 지표
    st.subheader("3. 포트폴리오 성과 및 리스크 지표")
    portfolio_returns = portfolio_value.pct_change().dropna()
    metrics = calculate_metrics(portfolio_returns)
    
    # 성과 지표 표시 (카드 형태로 개선)
    metric_groups = {
        "수익률 지표": ["연간 수익률", "월 평균 수익률", "양의 수익 개월 비율"],
        "리스크 지표": [
            "연간 변동성",
            "월간 변동성", 
            "Maximum Drawdown", 
            "VaR (95%)", 
            "CVaR (95%)"
        ],
        "효율성 지표": ["Sharpe Ratio", "Sortino Ratio", "Calmar Ratio"]
    }
    
    for group_name, metrics_list in metric_groups.items():
        st.write(f"**{group_name}**")
        cols = st.columns(len(metrics_list))
        for i, metric_name in enumerate(metrics_list):
            if metric_name in metrics:
                with cols[i]:
                    # 표기 방식 조정
                    if "비율" in metric_name and "Ratio" not in metric_name:
                        # 포맷팅된 문자열 생성
                        value = metrics[metric_name]
                        # NaN 값 처리
                        if pd.isna(value):
                            metric_value = "N/A"
                        else:
                            metric_value = f"{value:.1%}"
                        st.metric(metric_name, metric_value)
                    elif any(x in metric_name for x in [
                        "Ratio", "VaR", "CVaR"
                    ]):
                        # NaN 값 처리
                        value = metrics[metric_name]
                        if pd.isna(value):
                            metric_value = "N/A"
                        else:
                            metric_value = f"{value:.3f}"
                        st.metric(metric_name, metric_value)
                    else:
                        # 포맷팅된 문자열 생성
                        value = metrics[metric_name]
                        # NaN 값 처리
                        if pd.isna(value):
                            metric_value = "N/A"
                        else:
                            metric_value = f"{value:.2%}"
                        st.metric(metric_name, metric_value)
    
    # 4. 월별 수익률 히트맵
    st.subheader("4. 월별 수익률 히트맵")
    try:
        # 월별 수익률 계산 방식 변경
        monthly_returns = portfolio_returns.groupby(pd.Grouper(freq='ME')).apply(
            lambda x: (1 + x).prod() - 1
        )
        
        # 최소 2개 이상의 데이터가 있어야 히트맵 생성 가능
        if len(monthly_returns) > 1:
            # NaN 값 처리
            monthly_returns = monthly_returns.fillna(0)
            
            # 연도와 월로 그룹화하여 매트릭스 생성
            monthly_returns_matrix = monthly_returns.groupby(
                [monthly_returns.index.year, monthly_returns.index.month]
            ).first().unstack()
            
            # 데이터가 충분한지 확인
            if not monthly_returns_matrix.empty and not monthly_returns_matrix.isnull().all().all():
                fig_monthly = go.Figure(data=go.Heatmap(
                    z=monthly_returns_matrix.values,
                    x=[f"{i}월" for i in monthly_returns_matrix.columns],
                    y=monthly_returns_matrix.index,
                    colorscale='RdYlGn',
                    colorbar=dict(title="수익률"),
                    hoverongaps=False,
                    text=[[f"{val:.1%}" if not pd.isna(val) else "" 
                          for val in row] 
                         for row in monthly_returns_matrix.values],
                    texttemplate="%{text}",
                    textfont={"size": 10}
                ))
                fig_monthly.update_layout(
                    title="월별 수익률 히트맵",
                    xaxis_title="월",
                    yaxis_title="년",
                    template="plotly_white",
                    height=600
                )
                st.plotly_chart(fig_monthly, use_container_width=True, theme=None)
            else:
                st.info("월별 수익률 히트맵을 생성하기 위한 충분한 데이터가 없습니다.")
        else:
            st.info("월별 수익률 히트맵을 생성하기 위한 충분한 데이터가 없습니다.")
    except Exception as e:
        st.error(f"월별 수익률 히트맵 생성 중 오류가 발생했습니다: {str(e)}") 

    # 5. 성과 기록 저장 섹션
    st.subheader("5. 성과 기록 저장")
    default_name = st.session_state.selected_portfolio.get('name') or f"Portfolio-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    perf_name = st.text_input("기록할 포트폴리오 이름", value=default_name, key="perf_record_name")
    if st.button("DB에 성과 기록 저장", key="save_performance_to_db", type="primary"):
        if not perf_name.strip():
            st.error("포트폴리오 이름을 입력하세요.")
        else:
            try:
                # DB 세션 준비
                db = next(get_db())
                try:
                    # 포트폴리오 생성/가져오기
                    portfolio = portfolio_repo.upsert_portfolio(db, perf_name.strip())
                    if not portfolio:
                        st.error("포트폴리오 생성/조회에 실패했습니다.")
                    else:
                        pv = portfolio_value
                        dr = pv.pct_change()
                        saved = 0
                        for dt, val in pv.items():
                            daily = dr.loc[dt] if dt in dr.index else None
                            daily_val = None if (daily is None or pd.isna(daily)) else float(daily)
                            ok = performance_repo.record_portfolio_performance(
                                db,
                                portfolio.id,
                                dt.strftime('%Y-%m-%d'),
                                float(val),
                                daily_val
                            )
                            if ok:
                                saved += 1
                        st.success(f"성과 기록 저장 완료: {saved}건 저장")
                finally:
                    try:
                        db.close()
                    except Exception:
                        pass
            except Exception as e:
                st.error(f"성과 기록 저장 중 오류: {str(e)}")
