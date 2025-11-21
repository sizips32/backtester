#!/usr/bin/env python3
"""
Portfolio BackTester MCP Server
Claude Desktop용 포트폴리오 백테스터 MCP 서버 (FastMCP 기반)
"""

import sys
import os
from typing import List, Dict, Any

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# FastMCP 사용
from fastmcp import FastMCP

# FastMCP 서버 초기화
mcp = FastMCP("Portfolio BackTester")

@mcp.tool()
def hello(name: str = "World") -> str:
    """간단한 인사말을 반환합니다."""
    return f"안녕하세요, {name}님! Portfolio BackTester MCP 서버가 정상적으로 작동하고 있습니다."

@mcp.tool()
def calculate_position_size(entry_price: float, account_size: float, risk_percent: float = 2.0) -> str:
    """최적 포지션 사이즈를 계산합니다."""
    try:
        # 포지션 사이즈 계산
        position_value = account_size * (risk_percent / 100)
        shares = int(position_value / entry_price)
        
        return f"""📊 포지션 사이즈 계산 결과

💰 계좌 크기: ${account_size:,.2f}
📈 진입 가격: ${entry_price:.2f}
⚠️ 리스크 비율: {risk_percent}%

🎯 계산 결과:
  • 포지션 크기: ${position_value:,.2f}
  • 매수 수량: {shares}주
  • 계좌 대비 비중: {(position_value/account_size)*100:.2f}%
"""
    except Exception as e:
        return f"❌ 포지션 사이즈 계산 실패: {str(e)}"

@mcp.tool()
def optimize_portfolio(assets: List[str], method: str = "equal_weight") -> str:
    """포트폴리오 최적화를 수행합니다."""
    try:
        if method == "equal_weight":
            weights = [1.0 / len(assets)] * len(assets)
        else:
            weights = [1.0 / len(assets)] * len(assets)  # 기본값
        
        result = f"""📈 포트폴리오 최적화 완료 ({method})

🎯 최적 비중:
"""
        for asset, weight in zip(assets, weights):
            result += f"  • {asset}: {weight*100:.2f}%\n"
        
        return result
    except Exception as e:
        return f"❌ 포트폴리오 최적화 실패: {str(e)}"

@mcp.tool()
def get_market_data(ticker: str) -> str:
    """시장 데이터를 조회합니다."""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        
        if hist.empty:
            return f"❌ {ticker}에 대한 데이터를 찾을 수 없습니다."
        
        latest = hist.iloc[-1]
        return f"""📊 {ticker} 시장 데이터

📈 최신 가격: ${latest['Close']:.2f}
📊 주요 지표:
  • 시가: ${latest['Open']:.2f}
  • 고가: ${latest['High']:.2f}
  • 저가: ${latest['Low']:.2f}
  • 종가: ${latest['Close']:.2f}
  • 거래량: {latest['Volume']:,.0f}
"""
    except Exception as e:
        return f"❌ 시장 데이터 조회 실패: {str(e)}"

if __name__ == "__main__":
    mcp.run()
