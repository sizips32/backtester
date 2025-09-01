"""
향상된 UI 컴포넌트 라이브러리
반응형 디자인, 다크모드, 향상된 사용자 경험을 위한 컴포넌트들
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple
import json
from datetime import datetime

# 설정 시스템 import
from config.app_config import get_ui_config, get_config

class ThemeManager:
    """테마 관리자 (다크모드/라이트모드)"""
    
    def __init__(self):
        self.ui_config = get_ui_config()
        self._init_session_state()
    
    def _init_session_state(self) -> None:
        """세션 상태 초기화"""
        if 'dark_mode' not in st.session_state:
            st.session_state.dark_mode = self.ui_config.default_theme == 'dark'
        if 'mobile_view' not in st.session_state:
            st.session_state.mobile_view = False
    
    def toggle_theme_button(self) -> None:
        """테마 토글 버튼"""
        col1, col2, col3 = st.columns([6, 2, 2])
        
        with col2:
            theme_icon = "🌙" if not st.session_state.dark_mode else "☀️"
            if st.button(f"{theme_icon}", help="다크/라이트 모드 전환", key="theme_toggle"):
                st.session_state.dark_mode = not st.session_state.dark_mode
                st.rerun()
        
        with col3:
            mobile_icon = "📱" if not st.session_state.mobile_view else "💻"
            if st.button(f"{mobile_icon}", help="모바일/데스크톱 뷰 전환", key="view_toggle"):
                st.session_state.mobile_view = not st.session_state.mobile_view
                st.rerun()
    
    def get_current_theme(self) -> Dict[str, str]:
        """현재 테마 색상 반환"""
        base_colors = self.ui_config.colors.copy()
        
        if st.session_state.dark_mode:
            return {
                'background': '#0E1117',
                'surface': '#1C1C1C',
                'primary': base_colors['primary'],
                'secondary': '#03DAC6',
                'text': '#FAFAFA',
                'text_secondary': '#B0B0B0',
                'border': '#404040',
                'success': base_colors['success'],
                'warning': base_colors['warning'],
                'danger': base_colors['danger'],
                'info': base_colors['info'],
                'card_shadow': 'rgba(255,255,255,0.1)'
            }
        else:
            return {
                'background': '#FFFFFF',
                'surface': base_colors['light'],
                'primary': base_colors['primary'],
                'secondary': '#DC004E',
                'text': base_colors['dark'],
                'text_secondary': '#6C757D',
                'border': '#DEE2E6',
                'success': base_colors['success'],
                'warning': base_colors['warning'],
                'danger': base_colors['danger'],
                'info': base_colors['info'],
                'card_shadow': 'rgba(0,0,0,0.1)'
            }
    
    def apply_custom_css(self) -> None:
        """향상된 커스텀 CSS 적용"""
        theme = self.get_current_theme()
        is_mobile = st.session_state.mobile_view
        
        css = f"""
        <style>
        /* 전역 스타일 */
        .main .block-container {{
            padding-top: {'1rem' if is_mobile else '2rem'};
            padding-bottom: 2rem;
            padding-left: {'0.5rem' if is_mobile else '1rem'};
            padding-right: {'0.5rem' if is_mobile else '1rem'};
            max-width: {'100%' if is_mobile else '1200px'};
        }}
        
        /* 향상된 메트릭 카드 */
        .enhanced-metric-card {{
            background: linear-gradient(135deg, {theme['surface']}, {theme['background']});
            padding: {'1rem' if is_mobile else '1.5rem'};
            border-radius: 16px;
            border: 1px solid {theme['border']};
            margin-bottom: 1rem;
            box-shadow: 0 4px 12px {theme['card_shadow']};
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }}
        
        .enhanced-metric-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 24px {theme['card_shadow']};
            border-color: {theme['primary']};
        }}
        
        .metric-title {{
            color: {theme['text_secondary']};
            font-size: {'0.8rem' if is_mobile else '0.875rem'};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }}
        
        .metric-value {{
            color: {theme['text']};
            font-size: {'1.5rem' if is_mobile else '2rem'};
            font-weight: 700;
            margin-bottom: 0.25rem;
            background: linear-gradient(45deg, {theme['primary']}, {theme['secondary']});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .metric-delta {{
            font-size: {'0.75rem' if is_mobile else '0.875rem'};
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }}
        
        /* 반응형 차트 컨테이너 */
        .chart-container {{
            background: {theme['surface']};
            border-radius: 16px;
            padding: {'0.5rem' if is_mobile else '1rem'};
            border: 1px solid {theme['border']};
            margin-bottom: 1rem;
            box-shadow: 0 4px 12px {theme['card_shadow']};
        }}
        
        /* 모바일 최적화 */
        @media (max-width: 768px) {{
            .main .block-container {{
                padding-left: 0.5rem;
                padding-right: 0.5rem;
            }}
            
            .enhanced-metric-card {{
                padding: 1rem;
                margin-bottom: 0.75rem;
            }}
            
            .metric-value {{
                font-size: 1.25rem;
            }}
        }}
        
        /* 향상된 프로그레스 바 */
        .custom-progress-container {{
            background: {theme['border']};
            border-radius: 10px;
            height: 10px;
            overflow: hidden;
            margin: 0.75rem 0;
            position: relative;
        }}
        
        .custom-progress-fill {{
            background: linear-gradient(90deg, {theme['primary']}, {theme['secondary']});
            height: 100%;
            border-radius: 10px;
            transition: width 0.8s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .custom-progress-fill::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            animation: shimmer 2s infinite;
        }}
        
        @keyframes shimmer {{
            0% {{ transform: translateX(-100%); }}
            100% {{ transform: translateX(100%); }}
        }}
        
        /* 향상된 버튼 스타일 */
        .stButton > button {{
            background: linear-gradient(135deg, {theme['primary']}, {theme['secondary']});
            color: white;
            border: none;
            border-radius: 12px;
            padding: {'0.5rem 1rem' if is_mobile else '0.75rem 1.5rem'};
            font-weight: 600;
            font-size: {'0.875rem' if is_mobile else '1rem'};
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
            filter: brightness(1.1);
        }}
        
        .stButton > button:active {{
            transform: translateY(0);
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        
        /* 향상된 알림 스타일 */
        .custom-alert {{
            padding: {'0.75rem' if is_mobile else '1rem'};
            border-radius: 12px;
            margin: 1rem 0;
            border-left: 4px solid;
            backdrop-filter: blur(10px);
            font-weight: 500;
        }}
        
        .alert-success {{
            background: linear-gradient(135deg, {theme['success']}20, {theme['success']}10);
            border-color: {theme['success']};
            color: {theme['success']};
        }}
        
        .alert-warning {{
            background: linear-gradient(135deg, {theme['warning']}20, {theme['warning']}10);
            border-color: {theme['warning']};
            color: {theme['warning']};
        }}
        
        .alert-error {{
            background: linear-gradient(135deg, {theme['danger']}20, {theme['danger']}10);
            border-color: {theme['danger']};
            color: {theme['danger']};
        }}
        
        .alert-info {{
            background: linear-gradient(135deg, {theme['info']}20, {theme['info']}10);
            border-color: {theme['info']};
            color: {theme['info']};
        }}
        
        /* 로딩 애니메이션 */
        .custom-loading {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2rem;
            text-align: center;
        }}
        
        .loading-spinner {{
            width: 50px;
            height: 50px;
            border: 4px solid {theme['border']};
            border-top: 4px solid {theme['primary']};
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 1rem;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .loading-dots {{
            display: flex;
            gap: 0.25rem;
            justify-content: center;
        }}
        
        .loading-dot {{
            width: 8px;
            height: 8px;
            background: {theme['primary']};
            border-radius: 50%;
            animation: bounce 1.4s ease-in-out infinite both;
        }}
        
        .loading-dot:nth-child(1) {{ animation-delay: -0.32s; }}
        .loading-dot:nth-child(2) {{ animation-delay: -0.16s; }}
        
        @keyframes bounce {{
            0%, 80%, 100% {{
                transform: scale(0);
            }} 40% {{
                transform: scale(1);
            }}
        }}
        
        /* 섹션 헤더 개선 */
        .section-header {{
            color: {theme['text']};
            font-size: {'1.25rem' if is_mobile else '1.5rem'};
            font-weight: 700;
            margin: {'1rem 0 0.75rem 0' if is_mobile else '2rem 0 1rem 0'};
            padding-bottom: 0.5rem;
            border-bottom: 3px solid;
            border-image: linear-gradient(90deg, {theme['primary']}, {theme['secondary']}) 1;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        /* 데이터 테이블 개선 */
        .stDataFrame {{
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid {theme['border']};
            box-shadow: 0 4px 12px {theme['card_shadow']};
        }}
        
        /* 사이드바 개선 */
        .css-1d391kg {{
            background: {theme['surface']};
        }}
        
        /* 스크롤바 개선 */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: {theme['surface']};
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: linear-gradient(135deg, {theme['primary']}, {theme['secondary']});
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: {theme['primary']};
        }}
        
        /* 입력 필드 개선 */
        .stSelectbox > div > div {{
            border-radius: 8px;
            border: 2px solid {theme['border']};
            transition: border-color 0.3s ease;
        }}
        
        .stSelectbox > div > div:focus-within {{
            border-color: {theme['primary']};
            box-shadow: 0 0 0 3px {theme['primary']}33;
        }}
        
        .stTextInput > div > div > input {{
            border-radius: 8px;
            border: 2px solid {theme['border']};
            transition: border-color 0.3s ease;
        }}
        
        .stTextInput > div > div > input:focus {{
            border-color: {theme['primary']};
            box-shadow: 0 0 0 3px {theme['primary']}33;
        }}
        </style>
        """
        
        st.markdown(css, unsafe_allow_html=True)

class UITheme:
    """UI 테마 설정 (호환성 유지)"""
    def __init__(self):
        self.theme_manager = ThemeManager()
        theme = self.theme_manager.get_current_theme()
        self.COLORS = theme
        self.CHART_TEMPLATE = 'plotly_white' if not st.session_state.get('dark_mode', False) else 'plotly_dark'
        self.FONT_FAMILY = get_ui_config().font_family

class ProgressTracker:
    """개선된 진행 상황 추적기"""
    
    def __init__(self, title: str = "처리 중...", total_steps: int = 100):
        """
        Args:
            title: 진행 상황 제목
            total_steps: 전체 단계 수
        """
        self.container = st.container()
        with self.container:
            self.title = st.empty()
            self.progress_bar = st.progress(0)
            self.status = st.empty()
            self.details = st.expander("상세 정보", expanded=False)
            
        self.total_steps = total_steps
        self.current_step = 0
        self.title.markdown(f"### {title}")
        
    def update(self, step: int, message: str, detail: str = None):
        """진행 상황 업데이트"""
        self.current_step = step
        progress = min(step / self.total_steps, 1.0)
        
        self.progress_bar.progress(progress)
        self.status.text(f"[{step}/{self.total_steps}] {message}")
        
        if detail:
            with self.details:
                st.text(f"• {detail}")
    
    def complete(self, message: str = "완료!"):
        """작업 완료"""
        self.progress_bar.progress(1.0)
        self.status.success(message)
        
    def error(self, message: str):
        """에러 표시"""
        self.status.error(message)
        
    def clear(self):
        """컨테이너 정리"""
        self.container.empty()

class EnhancedMetrics:
    """향상된 메트릭 표시 컴포넌트"""
    
    def __init__(self, theme_manager: ThemeManager):
        self.theme = theme_manager.get_current_theme()
    
    def display_metric_card(self, 
                           title: str, 
                           value: Union[str, float, int], 
                           delta: Optional[Union[str, float]] = None,
                           format_func: Optional[callable] = None,
                           icon: str = "",
                           color: Optional[str] = None) -> None:
        """향상된 메트릭 카드 표시"""
        
        # 값 포맷팅
        if format_func:
            formatted_value = format_func(value)
        elif isinstance(value, float):
            if abs(value) >= 1_000_000:
                formatted_value = f"{value/1_000_000:.1f}M"
            elif abs(value) >= 1_000:
                formatted_value = f"{value/1_000:.1f}K"
            else:
                formatted_value = f"{value:,.2f}"
        elif isinstance(value, int):
            if abs(value) >= 1_000_000:
                formatted_value = f"{value/1_000_000:.1f}M"
            elif abs(value) >= 1_000:
                formatted_value = f"{value/1_000:.1f}K"
            else:
                formatted_value = f"{value:,}"
        else:
            formatted_value = str(value)
        
        # 델타 처리
        delta_html = ""
        if delta is not None:
            if isinstance(delta, (int, float)):
                delta_color = self.theme['success'] if delta >= 0 else self.theme['danger']
                delta_symbol = "▲" if delta >= 0 else "▼"
                delta_text = f"{delta:+.2f}%" if abs(delta) < 100 else f"{delta:+,.0f}"
            else:
                delta_color = self.theme['info']
                delta_symbol = ""
                delta_text = str(delta)
            
            delta_html = f"""
                <div class='metric-delta' style='color: {delta_color};'>
                    <span>{delta_symbol}</span>
                    <span>{delta_text}</span>
                </div>
            """
        
        # 색상 설정
        value_color = color or self.theme['primary']
        
        # 아이콘 처리
        icon_html = f"<span style='margin-right: 0.5rem;'>{icon}</span>" if icon else ""
        
        card_html = f"""
            <div class='enhanced-metric-card'>
                <div class='metric-title'>
                    {icon_html}{title}
                </div>
                <div class='metric-value' style='
                    background: linear-gradient(45deg, {value_color}, {self.theme["secondary"]});
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                '>
                    {formatted_value}
                </div>
                {delta_html}
            </div>
        """
        
        st.markdown(card_html, unsafe_allow_html=True)
    
    def display_kpi_grid(self, kpis: List[Dict[str, Any]], columns: int = 4) -> None:
        """KPI 그리드 표시"""
        cols = st.columns(columns)
        
        for i, kpi in enumerate(kpis):
            with cols[i % columns]:
                self.display_metric_card(
                    title=kpi.get('title', ''),
                    value=kpi.get('value', 0),
                    delta=kpi.get('delta'),
                    format_func=kpi.get('format_func'),
                    icon=kpi.get('icon', ''),
                    color=kpi.get('color')
                )
    
    def display_progress_indicator(self, 
                                 title: str, 
                                 current: float, 
                                 target: float,
                                 format_func: Optional[callable] = None) -> None:
        """진행률 표시기"""
        percentage = min((current / target) * 100, 100) if target > 0 else 0
        
        # 값 포맷팅
        if format_func:
            current_text = format_func(current)
            target_text = format_func(target)
        else:
            current_text = f"{current:,.0f}"
            target_text = f"{target:,.0f}"
        
        # 색상 결정
        if percentage >= 100:
            color = self.theme['success']
        elif percentage >= 75:
            color = self.theme['info']
        elif percentage >= 50:
            color = self.theme['warning']
        else:
            color = self.theme['danger']
        
        progress_html = f"""
            <div class='enhanced-metric-card'>
                <div class='metric-title'>{title}</div>
                <div class='custom-progress-container'>
                    <div class='custom-progress-fill' style='width: {percentage}%; background: {color};'></div>
                </div>
                <div style='display: flex; justify-content: space-between; margin-top: 0.5rem; color: {self.theme["text_secondary"]}; font-size: 0.875rem;'>
                    <span>{current_text} / {target_text}</span>
                    <span>{percentage:.1f}%</span>
                </div>
            </div>
        """
        
        st.markdown(progress_html, unsafe_allow_html=True)

class MetricCard:
    """메트릭 카드 컴포넌트 (호환성 유지)"""
    
    @staticmethod
    def render(
        title: str,
        value: Any,
        delta: Optional[float] = None,
        delta_color: str = "normal",
        format_str: str = "{:.2f}",
        suffix: str = ""
    ):
        """기본 메트릭 카드 렌더링"""
        if isinstance(value, (int, float)):
            formatted_value = format_str.format(value) + suffix
        else:
            formatted_value = str(value) + suffix
            
        st.metric(
            label=title,
            value=formatted_value,
            delta=delta,
            delta_color=delta_color
        )

class InteractiveChart:
    """인터랙티브 차트 컴포넌트 (향상된 차트로 연결)"""
    
    @staticmethod
    def portfolio_performance(
        data: pd.DataFrame,
        title: str = "포트폴리오 성과",
        show_drawdown: bool = True,
        benchmark_data: pd.DataFrame = None
    ) -> go.Figure:
        """향상된 포트폴리오 성과 차트 (호환성 유지)"""
        # 향상된 차트 컴포넌트로 위임
        from components.enhanced_charts import enhanced_charts
        return enhanced_charts.create_portfolio_performance_chart(
            data=data,
            title=title,
            show_benchmark=(benchmark_data is not None),
            benchmark_data=benchmark_data
        )
    
    @staticmethod
    def correlation_heatmap(
        data: pd.DataFrame,
        title: str = "상관관계 히트맵"
    ) -> go.Figure:
        """상관관계 히트맵 (향상된 차트로 위임)"""
        from components.enhanced_charts import enhanced_charts
        return enhanced_charts.create_correlation_heatmap(data=data, title=title)
    
    @staticmethod
    def risk_return_scatter(
        portfolios: List[Dict],
        title: str = "위험-수익 산점도"
    ) -> go.Figure:
        """위험-수익 산점도 (향상된 차트로 위임)"""
        from components.enhanced_charts import enhanced_charts
        return enhanced_charts.create_risk_return_scatter(portfolios=portfolios, title=title)

class DataTable:
    """개선된 데이터 테이블"""
    
    @staticmethod
    def render(
        data: pd.DataFrame,
        title: str = None,
        format_dict: Dict[str, str] = None,
        highlight_columns: List[str] = None,
        sortable: bool = True
    ):
        """
        데이터 테이블 렌더링
        
        Args:
            data: 표시할 데이터
            title: 테이블 제목
            format_dict: 컬럼별 포맷 딕셔너리
            highlight_columns: 하이라이트할 컬럼
            sortable: 정렬 가능 여부
        """
        if title:
            st.markdown(f"### {title}")
        
        # 포맷 적용
        if format_dict:
            for col, fmt in format_dict.items():
                if col in data.columns:
                    data[col] = data[col].apply(lambda x: fmt.format(x))
        
        # 스타일 적용
        styled_data = data.style
        
        if highlight_columns:
            styled_data = styled_data.background_gradient(
                subset=highlight_columns,
                cmap='RdYlGn'
            )
        
        st.dataframe(
            styled_data,
            use_container_width=True,
            hide_index=False if data.index.name else True
        )

class AlertBox:
    """알림 박스 컴포넌트"""
    
    @staticmethod
    def info(message: str, title: str = "정보"):
        """정보 알림"""
        st.info(f"**{title}**\n\n{message}")
    
    @staticmethod
    def success(message: str, title: str = "성공"):
        """성공 알림"""
        st.success(f"**{title}**\n\n{message}")
    
    @staticmethod
    def warning(message: str, title: str = "경고"):
        """경고 알림"""
        st.warning(f"**{title}**\n\n{message}")
    
    @staticmethod
    def error(message: str, title: str = "오류"):
        """에러 알림"""
        st.error(f"**{title}**\n\n{message}")

class InputValidator:
    """입력 검증 컴포넌트"""
    
    @staticmethod
    def validate_ticker(ticker: str) -> bool:
        """티커 심볼 검증"""
        import re
        pattern = r'^[A-Z0-9\.\-\^]{1,10}$'
        return bool(re.match(pattern, ticker.upper()))
    
    @staticmethod
    def validate_date_range(start_date, end_date) -> bool:
        """날짜 범위 검증"""
        return start_date < end_date
    
    @staticmethod
    def validate_weight(weight: float) -> bool:
        """포트폴리오 가중치 검증"""
        return 0 <= weight <= 1
    
    @staticmethod
    def show_validation_error(field: str, message: str):
        """검증 에러 표시"""
        st.error(f"⚠️ {field}: {message}")

class ResponsiveLayout:
    """반응형 레이아웃 헬퍼"""
    
    @staticmethod
    def create_columns(
        ratios: List[int],
        gap: str = "small"
    ):
        """
        반응형 컬럼 생성
        
        Args:
            ratios: 컬럼 비율 리스트
            gap: 컬럼 간격 ('small', 'medium', 'large')
        """
        return st.columns(ratios, gap=gap)
    
    @staticmethod
    def create_tabs(
        tabs: List[str],
        icons: List[str] = None
    ):
        """
        탭 생성
        
        Args:
            tabs: 탭 이름 리스트
            icons: 탭 아이콘 리스트
        """
        if icons:
            tab_labels = [f"{icon} {tab}" for icon, tab in zip(icons, tabs)]
        else:
            tab_labels = tabs
            
        return st.tabs(tab_labels)

class LoadingManager:
    """향상된 로딩 상태 관리자"""
    
    def __init__(self, theme_manager: ThemeManager):
        self.theme = theme_manager.get_current_theme()
    
    def show_loading_spinner(self, message: str = "데이터를 불러오는 중...", 
                           style: str = "spinner") -> Any:
        """로딩 스피너 표시"""
        
        if style == "dots":
            loading_html = f"""
                <div class='custom-loading'>
                    <div class='loading-dots'>
                        <div class='loading-dot'></div>
                        <div class='loading-dot'></div>
                        <div class='loading-dot'></div>
                    </div>
                    <div style='color: {self.theme["text_secondary"]}; margin-top: 1rem; font-weight: 500;'>
                        {message}
                    </div>
                </div>
            """
        else:
            loading_html = f"""
                <div class='custom-loading'>
                    <div class='loading-spinner'></div>
                    <div style='color: {self.theme["text_secondary"]}; font-weight: 500;'>
                        {message}
                    </div>
                </div>
            """
        
        return st.markdown(loading_html, unsafe_allow_html=True)
    
    def show_progress_status(self, 
                           current: int, 
                           total: int, 
                           message: str = "처리 중...",
                           show_details: bool = True) -> Any:
        """향상된 진행 상태 표시"""
        progress = current / total if total > 0 else 0
        percentage = int(progress * 100)
        
        # 프로그레스 바
        progress_bar = st.progress(progress)
        
        # 상태 메시지
        if show_details:
            status_cols = st.columns([3, 1])
            with status_cols[0]:
                st.markdown(f"""
                    <div style='color: {self.theme["text"]}; font-weight: 600; margin-bottom: 0.25rem;'>
                        {message}
                    </div>
                    <div style='color: {self.theme["text_secondary"]}; font-size: 0.875rem;'>
                        {current}/{total} 완료
                    </div>
                """, unsafe_allow_html=True)
            
            with status_cols[1]:
                st.markdown(f"""
                    <div style='text-align: right; color: {self.theme["primary"]}; font-weight: 700; font-size: 1.5rem;'>
                        {percentage}%
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div style='text-align: center; color: {self.theme["text"]}; font-weight: 500;'>
                    {message} ({percentage}%)
                </div>
            """, unsafe_allow_html=True)
        
        return progress_bar
    
    def create_status_placeholder(self) -> Dict[str, Any]:
        """상태 플레이스홀더 생성"""
        container = st.container()
        with container:
            status = st.empty()
            progress = st.empty()
            details = st.empty()
        
        return {
            'container': container,
            'status': status,
            'progress': progress,
            'details': details
        }

class EnhancedAlerts:
    """향상된 알림 시스템"""
    
    def __init__(self, theme_manager: ThemeManager):
        self.theme = theme_manager.get_current_theme()
    
    def show_success(self, title: str, message: str = "", 
                    dismissible: bool = True, icon: str = "✅") -> None:
        """성공 알림"""
        self._show_alert(title, message, "success", icon, dismissible)
    
    def show_warning(self, title: str, message: str = "", 
                    dismissible: bool = True, icon: str = "⚠️") -> None:
        """경고 알림"""
        self._show_alert(title, message, "warning", icon, dismissible)
    
    def show_error(self, title: str, message: str = "", 
                  dismissible: bool = True, icon: str = "❌") -> None:
        """에러 알림"""
        self._show_alert(title, message, "error", icon, dismissible)
    
    def show_info(self, title: str, message: str = "", 
                 dismissible: bool = True, icon: str = "ℹ️") -> None:
        """정보 알림"""
        self._show_alert(title, message, "info", icon, dismissible)
    
    def _show_alert(self, title: str, message: str, alert_type: str, 
                   icon: str, dismissible: bool) -> None:
        """알림 표시 (내부 메서드)"""
        
        message_html = f"""
            <div style='margin-top: 0.5rem; opacity: 0.9; line-height: 1.4;'>
                {message}
            </div>
        """ if message else ""
        
        dismiss_html = """
            <div style='margin-left: auto; cursor: pointer; opacity: 0.7;'>
                ×
            </div>
        """ if dismissible else ""
        
        alert_html = f"""
            <div class='custom-alert alert-{alert_type}'>
                <div style='display: flex; align-items: flex-start;'>
                    <div style='margin-right: 0.75rem; font-size: 1.25rem; flex-shrink: 0;'>
                        {icon}
                    </div>
                    <div style='flex: 1;'>
                        <div style='font-weight: 600; font-size: 1rem;'>
                            {title}
                        </div>
                        {message_html}
                    </div>
                    {dismiss_html}
                </div>
            </div>
        """
        
        st.markdown(alert_html, unsafe_allow_html=True)
    
    def show_toast(self, message: str, duration: int = 3000, 
                  position: str = "top-right") -> None:
        """토스트 알림 (JavaScript 기반)"""
        toast_js = f"""
        <script>
        function showToast() {{
            const toast = document.createElement('div');
            toast.innerHTML = '{message}';
            toast.style.cssText = `
                position: fixed;
                {position.split('-')[0]}: 20px;
                {position.split('-')[1]}: 20px;
                background: {self.theme['primary']};
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                z-index: 10000;
                font-weight: 500;
                animation: slideIn 0.3s ease;
            `;
            
            document.body.appendChild(toast);
            
            setTimeout(() => {{
                toast.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => document.body.removeChild(toast), 300);
            }}, {duration});
        }}
        
        showToast();
        </script>
        
        <style>
        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateX(100%); }}
            to {{ opacity: 1; transform: translateX(0); }}
        }}
        @keyframes slideOut {{
            from {{ opacity: 1; transform: translateX(0); }}
            to {{ opacity: 0; transform: translateX(100%); }}
        }}
        </style>
        """
        
        st.markdown(toast_js, unsafe_allow_html=True)

# 전역 매니저 인스턴스들
theme_manager = ThemeManager()
enhanced_metrics = EnhancedMetrics(theme_manager)
loading_manager = LoadingManager(theme_manager)
alert_system = EnhancedAlerts(theme_manager)