import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from components.ui_components import theme_manager, enhanced_metrics
from repository import portfolio_repo, holdings_repo, performance_repo
from utils.database import get_db

def show_dashboard():
    """메인 대시보드 화면 표시"""
    
    # 테마 정보 가져오기
    theme = theme_manager.get_current_theme()
    
    # 1. 환영 메시지 및 헤더
    current_time = datetime.now().strftime("%Y년 %m월 %d일")
    st.markdown(f"""
        <div style='margin-bottom: 2rem;'>
            <h1 class='neon-text' style='font-size: clamp(2rem, 5vw, 3rem); margin-bottom: 0.5rem; white-space: nowrap;'>Welcome Back!</h1>
            <div style='color: {theme['text_secondary']}; font-size: 1.2rem;'>
                오늘은 {current_time}입니다. 포트폴리오 현황을 확인하세요.
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # 데이터베이스 연결
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 2. 시스템 요약 메트릭 (Total AUM, Active Portfolios, etc.)
        portfolios = portfolio_repo.get_all_portfolios(db)
        total_portfolios = len(portfolios)
        
        total_aum = 0
        total_holdings_count = 0
        
        for p in portfolios:
            holdings = holdings_repo.get_portfolio_holdings(db, p.id)
            if holdings:
                total_holdings_count += len(holdings)
                # 간단한 AUM 계산 (실시간 가격 연동은 복잡하므로 매수가 기준 추정)
                # 실제 구현에서는 holdings_repo나 service에서 현재가 기반 가치를 가져와야 함
                for h in holdings:
                    total_aum += h.quantity * h.purchase_price

        # 메트릭 카드 그리드
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            enhanced_metrics.display_metric_card(
                title="총 운용 자산 (AUM)",
                value=total_aum,
                format_func=lambda x: f"${x:,.2f}",
                icon="💰"
            )
            
        with col2:
            enhanced_metrics.display_metric_card(
                title="활성 포트폴리오",
                value=total_portfolios,
                format_func=lambda x: f"{x}개",
                icon="📁"
            )
            
        with col3:
            enhanced_metrics.display_metric_card(
                title="총 보유 종목",
                value=total_holdings_count,
                format_func=lambda x: f"{x}개",
                icon="📊"
            )
            
        with col4:
            # 시스템 상태 (예시)
            enhanced_metrics.display_metric_card(
                title="시스템 상태",
                value="정상",
                color=theme['success'],
                icon="✅"
            )

        # 3. 퀵 액션 버튼 (카드 형태)
        st.markdown("<h3 style='margin-top: 2rem; margin-bottom: 1rem;'>🚀 Quick Actions</h3>", unsafe_allow_html=True)
        
        ac1, ac2, ac3 = st.columns(3)
        
        with ac1:
            st.markdown(f"""
            <div class="glass-card" style="text-align: center; height: 100%;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">💼</div>
                <h3 style="color: {theme['text']};">포트폴리오 관리</h3>
                <p style="color: {theme['text_secondary']};">포트폴리오를 생성하고 종목을 추가하세요.</p>
            </div>
            """, unsafe_allow_html=True)

        with ac2:
            st.markdown(f"""
            <div class="glass-card" style="text-align: center; height: 100%;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">📈</div>
                <h3 style="color: {theme['text']};">백테스팅 실행</h3>
                <p style="color: {theme['text_secondary']};">과거 데이터로 전략을 검증하세요.</p>
            </div>
            """, unsafe_allow_html=True)

        with ac3:
            st.markdown(f"""
            <div class="glass-card" style="text-align: center; height: 100%;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">⚖️</div>
                <h3 style="color: {theme['text']};">자산 배분 최적화</h3>
                <p style="color: {theme['text_secondary']};">최적의 자산 비중을 찾아보세요.</p>
            </div>
            """, unsafe_allow_html=True)

        # 두 번째 행 (리스크 분석, 리밸런싱, 포지션 사이징)
        ac4, ac5, ac6 = st.columns(3)
        
        with ac4:
            st.markdown(f"""
            <div class="glass-card" style="text-align: center; height: 100%;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">📊</div>
                <h3 style="color: {theme['text']};">리스크 분석</h3>
                <p style="color: {theme['text_secondary']};">포트폴리오의 위험 요소를 분석하세요.</p>
            </div>
            """, unsafe_allow_html=True)

        with ac5:
            st.markdown(f"""
            <div class="glass-card" style="text-align: center; height: 100%;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🔄</div>
                <h3 style="color: {theme['text']};">포트폴리오 리밸런싱</h3>
                <p style="color: {theme['text_secondary']};">목표 비중으로 포트폴리오를 조정하세요.</p>
            </div>
            """, unsafe_allow_html=True)

        with ac6:
            st.markdown(f"""
            <div class="glass-card" style="text-align: center; height: 100%;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">📏</div>
                <h3 style="color: {theme['text']};">포지션 사이징</h3>
                <p style="color: {theme['text_secondary']};">적절한 매매 수량을 계산하세요.</p>
            </div>
            """, unsafe_allow_html=True)

    finally:
        db.close()
