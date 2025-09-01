"""
향상된 차트 컴포넌트 라이브러리
인터랙티브하고 반응형인 포트폴리오 차트들
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
import streamlit as st
from datetime import datetime, timedelta

from config.app_config import get_ui_config
from components.ui_components import theme_manager

class EnhancedCharts:
    """향상된 차트 컴포넌트"""
    
    def __init__(self):
        self.ui_config = get_ui_config()
        self.theme = theme_manager.get_current_theme()
        self.is_dark_mode = st.session_state.get('dark_mode', False)
        self.chart_template = 'plotly_dark' if self.is_dark_mode else 'plotly_white'
    
    def create_portfolio_performance_chart(self, 
                                         data: pd.DataFrame,
                                         title: str = "포트폴리오 성과",
                                         show_benchmark: bool = True,
                                         benchmark_data: pd.DataFrame = None) -> go.Figure:
        """포트폴리오 성과 차트"""
        
        fig = make_subplots(
            rows=3 if 'drawdown' in data.columns else 2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=(
                '누적 수익률', 
                '일간 수익률', 
                '최대 낙폭'
            ) if 'drawdown' in data.columns else ('누적 수익률', '일간 수익률'),
            row_heights=[0.5, 0.3, 0.2] if 'drawdown' in data.columns else [0.7, 0.3]
        )
        
        # 누적 수익률
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data['cumulative'] * 100 if 'cumulative' in data.columns else data.iloc[:, 0] * 100,
                mode='lines',
                name='포트폴리오',
                line=dict(
                    color=self.theme['primary'],
                    width=3,
                    shape='spline'
                ),
                hovertemplate='%{x}<br>수익률: %{y:.2f}%<extra></extra>',
                fill='tonexty' if show_benchmark else None,
                fillcolor=f"rgba({','.join(str(int(self.theme['primary'][i:i+2], 16)) for i in (1, 3, 5))}, 0.1)"
            ),
            row=1, col=1
        )
        
        # 벤치마크
        if show_benchmark and benchmark_data is not None:
            fig.add_trace(
                go.Scatter(
                    x=benchmark_data.index,
                    y=benchmark_data.iloc[:, 0] * 100,
                    mode='lines',
                    name='벤치마크',
                    line=dict(
                        color=self.theme['secondary'],
                        width=2,
                        dash='dash'
                    ),
                    hovertemplate='%{x}<br>벤치마크: %{y:.2f}%<extra></extra>'
                ),
                row=1, col=1
            )
        
        # 일간 수익률 히스토그램
        if 'returns' in data.columns:
            returns_data = data['returns'].dropna() * 100
            
            fig.add_trace(
                go.Histogram(
                    x=returns_data,
                    name='수익률 분포',
                    nbinsx=50,
                    marker=dict(
                        color=self.theme['info'],
                        opacity=0.7,
                        line=dict(color=self.theme['border'], width=1)
                    ),
                    hovertemplate='수익률: %{x:.2f}%<br>빈도: %{y}<extra></extra>'
                ),
                row=2, col=1
            )
        
        # 최대 낙폭
        if 'drawdown' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['drawdown'] * 100,
                    mode='lines',
                    name='낙폭',
                    fill='tozeroy',
                    line=dict(color=self.theme['danger'], width=1.5),
                    fillcolor=f"rgba({','.join(str(int(self.theme['danger'][i:i+2], 16)) for i in (1, 3, 5))}, 0.3)",
                    hovertemplate='%{x}<br>낙폭: %{y:.2f}%<extra></extra>'
                ),
                row=3, col=1
            )
        
        # 레이아웃 설정
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=24, family=self.ui_config.font_family),
                x=0.5
            ),
            template=self.chart_template,
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            height=600 if 'drawdown' in data.columns else 500,
            margin=dict(t=80, b=40, l=60, r=40),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        # 축 설정
        fig.update_xaxes(
            title_text="날짜",
            showgrid=True,
            gridwidth=1,
            gridcolor=self.theme['border']
        )
        fig.update_yaxes(
            title_text="누적 수익률 (%)",
            showgrid=True,
            gridwidth=1,
            gridcolor=self.theme['border'],
            row=1, col=1
        )
        
        return fig
    
    def create_asset_allocation_chart(self, 
                                    weights: Dict[str, float],
                                    title: str = "자산 배분") -> go.Figure:
        """자산 배분 파이 차트"""
        
        # 색상 팔레트
        colors = px.colors.qualitative.Set3[:len(weights)]
        
        fig = go.Figure(data=[
            go.Pie(
                labels=list(weights.keys()),
                values=list(weights.values()),
                hole=0.4,
                marker=dict(
                    colors=colors,
                    line=dict(color=self.theme['border'], width=2)
                ),
                textfont=dict(size=14, family=self.ui_config.font_family),
                hovertemplate='<b>%{label}</b><br>비중: %{percent}<br>값: %{value:.2%}<extra></extra>',
                pull=[0.05 if v == max(weights.values()) else 0 for v in weights.values()]
            )
        ])
        
        # 중앙 텍스트
        total_assets = len(weights)
        fig.add_annotation(
            text=f"<b>총 {total_assets}개<br>자산</b>",
            x=0.5, y=0.5,
            font_size=16,
            font_color=self.theme['text'],
            showarrow=False
        )
        
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=20, family=self.ui_config.font_family),
                x=0.5
            ),
            template=self.chart_template,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05
            ),
            height=500,
            margin=dict(t=60, b=40, l=40, r=120),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        return fig
    
    def create_risk_return_scatter(self, 
                                 portfolios: List[Dict[str, Any]],
                                 title: str = "위험-수익 분석") -> go.Figure:
        """위험-수익 산점도"""
        
        fig = go.Figure()
        
        # 효율 프론티어 곡선 (있는 경우)
        if any('frontier' in p for p in portfolios):
            frontier_data = [p for p in portfolios if 'frontier' in p.get('name', '')]
            if frontier_data:
                risks = [p['risk'] for p in frontier_data]
                returns = [p['return'] for p in frontier_data]
                
                fig.add_trace(go.Scatter(
                    x=risks,
                    y=returns,
                    mode='lines',
                    name='효율 프론티어',
                    line=dict(
                        color=self.theme['secondary'],
                        width=3,
                        dash='dot'
                    ),
                    hovertemplate='위험: %{x:.2f}%<br>수익: %{y:.2f}%<extra></extra>'
                ))
        
        # 포트폴리오 점들
        regular_portfolios = [p for p in portfolios if 'frontier' not in p.get('name', '')]
        
        for i, portfolio in enumerate(regular_portfolios):
            color = self.theme['primary'] if i == 0 else px.colors.qualitative.Set1[i % 10]
            size = 15 if i == 0 else 12
            
            fig.add_trace(go.Scatter(
                x=[portfolio['risk']],
                y=[portfolio['return']],
                mode='markers+text',
                name=portfolio['name'],
                text=[portfolio['name']],
                textposition="top center",
                marker=dict(
                    size=size,
                    color=color,
                    line=dict(color=self.theme['border'], width=2),
                    symbol='circle'
                ),
                hovertemplate=(
                    f"<b>{portfolio['name']}</b><br>"
                    f"예상 수익률: %{{y:.2f}}%<br>"
                    f"위험(변동성): %{{x:.2f}}%<br>"
                    f"샤프 비율: {portfolio.get('sharpe', 0):.2f}<br>"
                    f"최대 낙폭: {portfolio.get('max_drawdown', 0):.2f}%"
                    "<extra></extra>"
                )
            ))
        
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=20, family=self.ui_config.font_family),
                x=0.5
            ),
            xaxis_title="위험 (연간 변동성 %)",
            yaxis_title="기대 수익률 (연간 %)",
            template=self.chart_template,
            hovermode='closest',
            height=500,
            margin=dict(t=60, b=60, l=60, r=40),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            )
        )
        
        # 격자와 축 설정
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor=self.theme['border'],
            zeroline=True,
            zerolinecolor=self.theme['border']
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor=self.theme['border'],
            zeroline=True,
            zerolinecolor=self.theme['border']
        )
        
        return fig
    
    def create_correlation_heatmap(self, 
                                 data: pd.DataFrame,
                                 title: str = "자산간 상관관계") -> go.Figure:
        """상관관계 히트맵"""
        
        corr = data.corr()
        
        # 마스크 생성 (대각선 위쪽 제거)
        mask = np.triu(np.ones_like(corr, dtype=bool))
        corr_masked = corr.mask(mask)
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_masked.values,
            x=corr.columns,
            y=corr.columns,
            colorscale='RdBu',
            zmid=0,
            zmin=-1,
            zmax=1,
            text=np.around(corr_masked.values, decimals=2),
            texttemplate='%{text}',
            textfont={"size": 12, "color": self.theme['text']},
            hovertemplate='<b>%{y} vs %{x}</b><br>상관계수: %{z:.3f}<extra></extra>',
            colorbar=dict(
                title=dict(
                    text="상관계수",
                    font=dict(size=14, color=self.theme['text'])
                ),
                tickfont=dict(color=self.theme['text'])
            )
        ))
        
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=20, family=self.ui_config.font_family),
                x=0.5
            ),
            template=self.chart_template,
            height=500,
            margin=dict(t=60, b=60, l=100, r=100),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        fig.update_xaxes(
            tickangle=45,
            tickfont=dict(color=self.theme['text'])
        )
        fig.update_yaxes(
            tickfont=dict(color=self.theme['text'])
        )
        
        return fig
    
    def create_rolling_metrics_chart(self, 
                                   data: pd.DataFrame,
                                   metrics: List[str] = ['returns', 'volatility', 'sharpe'],
                                   title: str = "롤링 지표 분석") -> go.Figure:
        """롤링 지표 차트"""
        
        fig = make_subplots(
            rows=len(metrics),
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=[m.replace('_', ' ').title() for m in metrics]
        )
        
        colors = [self.theme['primary'], self.theme['secondary'], self.theme['info']]
        
        for i, metric in enumerate(metrics):
            if metric in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=data[metric],
                        mode='lines',
                        name=metric.replace('_', ' ').title(),
                        line=dict(
                            color=colors[i % len(colors)],
                            width=2
                        ),
                        hovertemplate=f'%{{x}}<br>{metric}: %{{y:.3f}}<extra></extra>'
                    ),
                    row=i+1, col=1
                )
        
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=20, family=self.ui_config.font_family),
                x=0.5
            ),
            template=self.chart_template,
            height=150 * len(metrics) + 100,
            hovermode='x unified',
            showlegend=False,
            margin=dict(t=60, b=40, l=60, r=40),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        # 축 설정
        for i in range(len(metrics)):
            fig.update_xaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor=self.theme['border'],
                row=i+1, col=1
            )
            fig.update_yaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor=self.theme['border'],
                row=i+1, col=1
            )
        
        fig.update_xaxes(title_text="날짜", row=len(metrics), col=1)
        
        return fig
    
    def create_monte_carlo_chart(self, 
                               simulations: np.ndarray,
                               percentiles: List[int] = [5, 25, 50, 75, 95],
                               title: str = "몬테카를로 시뮬레이션") -> go.Figure:
        """몬테카를로 시뮬레이션 결과 차트"""
        
        fig = go.Figure()
        
        # 시뮬레이션 경로들 (투명하게)
        for i in range(min(100, simulations.shape[0])):  # 최대 100개만 표시
            fig.add_trace(go.Scatter(
                x=list(range(simulations.shape[1])),
                y=simulations[i] * 100,
                mode='lines',
                line=dict(
                    color=self.theme['primary'],
                    width=0.5,
                    opacity=0.1
                ),
                hoverinfo='skip',
                showlegend=False
            ))
        
        # 백분위수 경로들
        colors = [self.theme['danger'], self.theme['warning'], 
                 self.theme['success'], self.theme['warning'], self.theme['danger']]
        
        for i, pct in enumerate(percentiles):
            pct_data = np.percentile(simulations, pct, axis=0) * 100
            
            fig.add_trace(go.Scatter(
                x=list(range(len(pct_data))),
                y=pct_data,
                mode='lines',
                name=f'{pct}th %ile',
                line=dict(
                    color=colors[i % len(colors)],
                    width=3 if pct == 50 else 2,
                    dash='solid' if pct == 50 else 'dash'
                ),
                hovertemplate=f'{pct}th percentile<br>Period: %{{x}}<br>Return: %{{y:.2f}}%<extra></extra>'
            ))
        
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=20, family=self.ui_config.font_family),
                x=0.5
            ),
            xaxis_title="기간",
            yaxis_title="누적 수익률 (%)",
            template=self.chart_template,
            height=500,
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            margin=dict(t=80, b=60, l=60, r=40),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor=self.theme['border']
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor=self.theme['border']
        )
        
        return fig

# 전역 차트 매니저 인스턴스
enhanced_charts = EnhancedCharts()