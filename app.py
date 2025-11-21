import warnings

# Streamlit deprecated 경고 숨기기
warnings.filterwarnings("ignore", message=".*use_container_width.*", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*on_change.*", category=DeprecationWarning)

import streamlit as st

# Streamlit 설정은 어떤 Streamlit 호출보다 먼저 수행되어야 함
st.set_page_config(page_title="포트폴리오 백테스터", page_icon="💰", layout="wide")

from risk_analysis import show_risk_analysis
from asset_allocation import show_asset_allocation
from backtesting import show_backtesting
from portfolio_rebalancing import show_portfolio_rebalancing
from position_sizing import show_position_sizing
from components.portfolio_view import render_portfolio_content

# 설정 시스템 import
from config.app_config import get_ui_config

# 향상된 UI 컴포넌트 import
from components.ui_components import (
    theme_manager, enhanced_metrics, loading_manager, alert_system,
    ThemeManager, EnhancedMetrics, LoadingManager, EnhancedAlerts
)

# 로깅 시스템 import
from utils.logger import show_log_dashboard

from components.dashboard_view import show_dashboard

# 상수 정의
MENU_OPTIONS = {
    "🏠 대시보드": show_dashboard,
    "💼 포트폴리오 관리": render_portfolio_content,
    "📈 백테스팅": show_backtesting,
    "📊 리스크 분석": show_risk_analysis,
    "⚖️ 자산 배분": show_asset_allocation,
    "🔄 포트폴리오 리밸런싱": show_portfolio_rebalancing,
    "📏 포지션 사이징": show_position_sizing,
    "📋 시스템 로그": show_log_dashboard
}


def main():
    # UI 설정 가져오기
    ui_config = get_ui_config()
    
    # 테마 시스템 초기화 및 CSS 적용
    theme_manager.apply_custom_css()
    
    # 헤더 영역
    header_container = st.container()
    with header_container:
        # 향상된 메인 타이틀 - 모던하고 화려한 디자인
        current_theme = theme_manager.get_current_theme()
        st.markdown(f"""
            <style>
            @keyframes float {{
                0%, 100% {{ transform: translateY(0px); }}
                50% {{ transform: translateY(-10px); }}
            }}
            .hero-emoji {{
                font-size: 4rem;
                display: inline-block;
                animation: float 3s ease-in-out infinite;
                margin-bottom: 1rem;
            }}
            .hero-title {{
                font-size: clamp(2rem, 5vw, 3.5rem);
                font-weight: 900;
                background: linear-gradient(135deg, {current_theme['primary']}, {current_theme['secondary']}, #00d4ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                letter-spacing: -0.02em;
                line-height: 1.2;
                margin: 0.5rem 0;
                text-shadow: 0 0 40px {current_theme['primary']}40;
            }}
            .hero-subtitle {{
                font-size: clamp(1rem, 2.5vw, 1.3rem);
                color: {current_theme['text_secondary']};
                font-weight: 500;
                margin-top: 1rem;
                line-height: 1.6;
                max-width: 800px;
                margin-left: auto;
                margin-right: auto;
            }}
            .hero-container {{
                text-align: center;
                padding: 2rem 1rem 3rem;
                background: linear-gradient(180deg, {current_theme['surface']}00 0%, {current_theme['surface']}40 100%);
                border-radius: 24px;
                margin-bottom: 2rem;
            }}
            </style>
            <div class='hero-container'>
                <div class='hero-emoji'>💰</div>
                <h1 class='hero-title'>포트폴리오 자금 관리 시스템</h1>
                <p class='hero-subtitle'>
                    💡 효율적인 포트폴리오 관리와 리스크 분석을 위한 올인원 솔루션
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    # 향상된 사이드바
    with st.sidebar:
        current_theme = theme_manager.get_current_theme()
        st.markdown(f"""
            <div style='text-align: center; padding: 1.5rem 0; border-bottom: 2px solid {current_theme["border"]}; margin-bottom: 1rem;'>
                <h2 style='color: {current_theme["primary"]}; margin: 0; font-weight: 700;'>
                    🎯 메뉴
                </h2>
                <div style='color: {current_theme["text_secondary"]}; font-size: 0.9rem; margin-top: 0.5rem;'>
                    원하는 기능을 선택하세요
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 메뉴 선택 (세션 상태와 연동)
        if 'current_menu' not in st.session_state:
            st.session_state.current_menu = "🏠 대시보드"
            
        # 인덱스 찾기
        try:
            menu_index = list(MENU_OPTIONS.keys()).index(st.session_state.current_menu)
        except ValueError:
            menu_index = 0
            
        selected_menu = st.selectbox(
            "메뉴 선택",
            list(MENU_OPTIONS.keys()),
            index=menu_index,
            label_visibility="collapsed",
            key="menu_selector"
        )
        
        # 선택 변경 시 세션 상태 업데이트
        if selected_menu != st.session_state.current_menu:
            st.session_state.current_menu = selected_menu
            st.rerun()
            
        menu = st.session_state.current_menu
        
        # 도움말 섹션
        st.markdown("---")
        with st.expander("📖 사용 가이드", expanded=False):
            st.markdown(f"""
            <div style='color: {current_theme["text"]}; font-size: 0.85rem;'>
                <h4 style='color: {current_theme["primary"]}; margin-top: 0;'>주요 기능</h4>
                
                <p><strong>🏠 대시보드</strong><br/>
                전체 포트폴리오 현황과 주요 지표를 한눈에 확인하세요.</p>
                
                <p><strong>💼 포트폴리오 관리</strong><br/>
                포트폴리오를 생성하고 보유 종목을 추가/수정/삭제할 수 있습니다.</p>
                
                <p><strong>📈 백테스팅</strong><br/>
                과거 데이터로 포트폴리오 전략의 성과를 시뮬레이션합니다.</p>
                
                <p><strong>📊 리스크 분석</strong><br/>
                포트폴리오의 위험 요소를 분석하고 평가합니다.</p>
                
                <p><strong>⚖️ 자산 배분</strong><br/>
                최적의 자산 비중을 찾아 포트폴리오를 최적화합니다.</p>
                
                <p><strong>🔄 리밸런싱</strong><br/>
                목표 비중에 맞춰 포트폴리오를 재조정합니다.</p>
                
                <p><strong>📏 포지션 사이징</strong><br/>
                적절한 매매 수량을 계산합니다.</p>
                
                <h4 style='color: {current_theme["primary"]}; margin-top: 1rem;'>시작하기</h4>
                <ol style='margin: 0; padding-left: 1.2rem;'>
                    <li>포트폴리오 관리에서 새 포트폴리오 생성</li>
                    <li>보유 종목 추가 및 비중 설정</li>
                    <li>백테스팅으로 전략 검증</li>
                    <li>리스크 분석으로 위험 평가</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
    
    # 메뉴 실행
    try:
        with st.spinner("페이지를 로드하는 중..."):
            MENU_OPTIONS[menu]()
    except Exception as e:
        alert_system.show_error(
            "페이지 로드 오류", 
            f"선택한 메뉴를 로드하는 중 오류가 발생했습니다: {str(e)}"
        )


if __name__ == "__main__":
    main() 
