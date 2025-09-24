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

# 상수 정의
MENU_OPTIONS = {
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
    
    # 헤더 영역 - 테마 토글 버튼과 함께
    header_container = st.container()
    with header_container:
        # 테마 토글 버튼
        theme_manager.toggle_theme_button()
        
        # 향상된 메인 타이틀
        current_theme = theme_manager.get_current_theme()
        st.markdown(f"""
            <div class='section-header' style='text-align: center; border: none; margin: 2rem 0;'>
                <span style='font-size: 2rem;'>{ui_config.page_icon}</span>
                <span>포트폴리오 자금 관리 시스템</span>
            </div>
            <div style='text-align: center; color: {current_theme["text_secondary"]}; margin-bottom: 2rem; font-size: 1.1rem;'>
                💡 효율적인 포트폴리오 관리와 리스크 분석을 위한 올인원 솔루션
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
        
        # 메뉴 선택
        menu = st.selectbox(
            "메뉴 선택",
            list(MENU_OPTIONS.keys()),
            label_visibility="collapsed"
        )
        
        # 현재 모드 표시
        mode_info = "🌙 다크 모드" if st.session_state.get('dark_mode', False) else "☀️ 라이트 모드"
        view_info = "📱 모바일 뷰" if st.session_state.get('mobile_view', False) else "💻 데스크톱 뷰"
        
        st.markdown(f"""
            <div style='margin-top: 2rem; padding: 1rem; background: {current_theme["surface"]}; border-radius: 8px; border: 1px solid {current_theme["border"]};'>
                <div style='font-size: 0.875rem; color: {current_theme["text_secondary"]}; text-align: center;'>
                    <div>{mode_info}</div>
                    <div style='margin-top: 0.25rem;'>{view_info}</div>
                </div>
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
