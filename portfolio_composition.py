import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

def show_portfolio_composition():
    st.header("포트폴리오 구성")
    
    # 투자 스타일 선택
    investment_style = st.radio(
        "투자 스타일을 선택하세요:",
        ["보수적 투자자", "균형적 투자자", "공격적 투자자"]
    )
    
    # 초기 자산 입력
    initial_investment = st.number_input(
        "초기 투자금액 (원)",
        min_value=0,
        value=10000000,
        step=1000000,
        format="%d"
    )
    
    # 투자 스타일에 따른 기본 자산 배분
    if investment_style == "보수적 투자자":
        allocations = {
            "채권": 60,
            "주식": 30,
            "현금": 10
        }
    elif investment_style == "균형적 투자자":
        allocations = {
            "주식": 50,
            "채권": 30,
            "대체자산": 20
        }
    else:
        allocations = {
            "주식": 70,
            "대체자산": 20,
            "현금": 10
        }
    
    # 파이 차트로 자산 배분 시각화
    fig = px.pie(
        values=list(allocations.values()),
        names=list(allocations.keys()),
        title="자산 배분 비율"
    )
    st.plotly_chart(fig)
    
    # 금액으로 환산된 자산 배분 표시
    st.subheader("금액별 자산 배분")
    for asset, percentage in allocations.items():
        amount = initial_investment * (percentage / 100)
        st.write(f"{asset}: {amount:,.0f}원 ({percentage}%)") 

def validate_investment_input(amount: float) -> bool:
    """투자금액 유효성 검증"""
    if amount <= 0:
        st.error("투자금액은 0보다 커야 합니다")
        return False
    if amount > 1000000000000:  # 1조원
        st.error("너무 큰 금액입니다")
        return False
    return True 
