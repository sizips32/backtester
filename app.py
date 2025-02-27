import streamlit as st
from risk_analysis import show_risk_analysis
from asset_allocation import show_asset_allocation
from backtesting import show_backtesting
from portfolio_rebalancing import show_portfolio_rebalancing
from position_sizing import show_position_sizing
import portfolio_app

# 상수 정의
MENU_OPTIONS = {
    "💼 포트폴리오 관리": portfolio_app.render_portfolio_content,
    "📊 리스크 분석": show_risk_analysis,
    "⚖️ 자산 배분": show_asset_allocation,
    "🔄 포트폴리오 리밸런싱": show_portfolio_rebalancing,
    "📏 포지션 사이징": show_position_sizing,
    "📈 백테스팅": show_backtesting
}


def main():
    st.set_page_config(
        page_title="포트폴리오 자금 관리",
        page_icon="💰",
        layout="wide"
    )
    
    # 메인 타이틀 스타일링
    st.markdown("""
        <h1 style='text-align: center; margin-bottom: 40px;'>
            💰 포트폴리오 자금 관리 시스템
        </h1>
        <p style='text-align: center; color: #666; margin-bottom: 30px;'>
            효율적인 포트폴리오 관리와 리스크 분석을 위한 올인원 솔루션
        </p>
    """, unsafe_allow_html=True)
    
    # 사이드바 스타일링
    st.sidebar.markdown("""
        <h3 style='text-align: center; color: #1f77b4; margin-bottom: 20px;'>
            🎯 메뉴 선택
        </h3>
    """, unsafe_allow_html=True)
    
    menu = st.sidebar.selectbox(
        "메뉴",  # 라벨 추가
        list(MENU_OPTIONS.keys()),
        label_visibility="hidden"  # 라벨을 시각적으로 숨김
    )
    
    MENU_OPTIONS[menu]()


if __name__ == "__main__":
    main() 
