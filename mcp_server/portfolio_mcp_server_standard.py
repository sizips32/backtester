#!/usr/bin/env python3
"""
Portfolio BackTester MCP Server - 표준 MCP 구현
Claude Desktop용 포트폴리오 백테스터 MCP 서버 (표준 MCP SDK 사용)
"""

import sys
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# 표준 MCP SDK 사용
from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import TextContent, ImageContent, EmbeddedResource

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import yfinance as yf

# 백테스터 모듈 imports
try:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    from utils.database import SessionLocal, Portfolio, PortfolioHolding
    from repository.portfolio_repo import create_portfolio, get_all_portfolios, get_portfolio_by_name

    def get_db_session():
        """MCP 서버용 데이터베이스 세션 생성"""
        return SessionLocal()

    STREAMLIT_DB_AVAILABLE = True
    print("✅ Streamlit 데이터베이스 연동 성공", file=sys.stderr)

    # 데이터베이스 연결 테스트
    try:
        test_session = get_db_session()
        portfolios_count = test_session.query(Portfolio).count()
        test_session.close()
        print(f"✅ 데이터베이스 연결 테스트 성공. 기존 포트폴리오: {portfolios_count}개", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ 데이터베이스 연결 테스트 실패: {e}", file=sys.stderr)
        STREAMLIT_DB_AVAILABLE = False

except ImportError as e:
    STREAMLIT_DB_AVAILABLE = False
    print(f"⚠️ Streamlit 데이터베이스 연동 실패: {e}", file=sys.stderr)

    def get_db_session():
        """Dummy 함수 - DB 사용 불가"""
        return None

# 서버 초기화
server = Server("Portfolio BackTester")

# 글로벌 포트폴리오 저장소 (메모리 백업)
portfolios = {}

# ====== 도구 핸들러 등록 ======

@server.list_tools()
async def handle_list_tools() -> list:
    """사용 가능한 도구 목록을 반환합니다."""
    return [
        {
            "name": "create_portfolio",
            "description": "새로운 포트폴리오를 생성합니다",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "포트폴리오 이름"},
                    "assets": {"type": "array", "items": {"type": "string"}, "description": "자산 티커 목록"},
                    "weights": {"type": "array", "items": {"type": "number"}, "description": "각 자산의 비중 (0-1)"},
                    "initial_capital": {"type": "number", "description": "초기 투자금액", "default": 100000.0}
                },
                "required": ["name", "assets", "weights"]
            }
        },
        {
            "name": "list_portfolios",
            "description": "생성된 포트폴리오 목록을 조회합니다",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_stock_data",
            "description": "주식 데이터를 가져옵니다",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "주식 티커"},
                    "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"}
                },
                "required": ["ticker"]
            }
        }
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """도구 호출을 처리합니다."""

    if name == "create_portfolio":
        return await create_portfolio_tool(**arguments)
    elif name == "list_portfolios":
        return await list_portfolios_tool()
    elif name == "get_stock_data":
        return await get_stock_data_tool(**arguments)
    else:
        return [TextContent(type="text", text=f"❌ 알 수 없는 도구: {name}")]

# ====== 도구 구현 함수들 ======

async def create_portfolio_tool(
    name: str,
    assets: List[str],
    weights: List[float],
    initial_capital: float = 100000.0
) -> List[TextContent]:
    """새로운 포트폴리오를 생성합니다.

    Args:
        name: 포트폴리오 이름
        assets: 자산 티커 목록 (예: ['AAPL', 'GOOGL', 'MSFT'])
        weights: 각 자산의 비중 (0-1 사이, 합계 1)
        initial_capital: 초기 투자금액 (USD)

    Returns:
        포트폴리오 생성 결과 메시지
    """
    try:
        # 검증
        if len(assets) != len(weights):
            return [TextContent(type="text", text="❌ 오류: 자산 개수와 비중 개수가 일치하지 않습니다.")]

        if abs(sum(weights) - 1.0) > 0.01:
            return [TextContent(type="text", text="❌ 오류: 비중의 합이 1이 아닙니다.")]

        # 포트폴리오 저장
        portfolios[name] = {
            "assets": assets,
            "weights": dict(zip(assets, weights)),
            "initial_capital": initial_capital,
            "created_at": datetime.now().isoformat()
        }

        result = f"""✅ 포트폴리오 '{name}' 생성 완료

📊 포트폴리오 구성:
"""
        for asset, weight in zip(assets, weights):
            result += f"  • {asset}: {weight*100:.1f}%\n"

        result += f"\n💰 초기 자본: ${initial_capital:,.2f}"

        return [TextContent(type="text", text=result)]

    except Exception as e:
        return [TextContent(type="text", text=f"❌ 포트폴리오 생성 실패: {str(e)}")]


@server.call_tool()
async def list_portfolios_tool() -> List[TextContent]:
    """생성된 포트폴리오 목록을 조회합니다."""
    try:
        if not portfolios:
            return [TextContent(type="text", text="📝 생성된 포트폴리오가 없습니다.")]

        result = "📊 포트폴리오 목록:\n\n"
        for name, portfolio in portfolios.items():
            result += f"🔹 **{name}**\n"
            result += f"   자산: {', '.join(portfolio['assets'])}\n"
            result += f"   초기자본: ${portfolio['initial_capital']:,.2f}\n"
            result += f"   생성일: {portfolio['created_at'][:10]}\n\n"

        return [TextContent(type="text", text=result)]

    except Exception as e:
        return [TextContent(type="text", text=f"❌ 포트폴리오 목록 조회 실패: {str(e)}")]


@server.call_tool()
async def get_stock_data_tool(
    ticker: str,
    start_date: str = None,
    end_date: str = None
) -> List[TextContent]:
    """주식 데이터를 가져옵니다.

    Args:
        ticker: 주식 티커 (예: 'AAPL', 'GOOGL')
        start_date: 시작일 (YYYY-MM-DD, 기본값: 1년 전)
        end_date: 종료일 (YYYY-MM-DD, 기본값: 오늘)
    """
    try:
        # 기본 날짜 설정
        if end_date is None:
            end_date = datetime.now()
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        if start_date is None:
            start_date = end_date - timedelta(days=365)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')

        # 데이터 가져오기
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date)

        if df.empty:
            return [TextContent(type="text", text=f"❌ {ticker}의 데이터를 찾을 수 없습니다.")]

        # 기본 통계
        latest_price = df['Close'].iloc[-1]
        price_change = df['Close'].iloc[-1] - df['Close'].iloc[0]
        percent_change = (price_change / df['Close'].iloc[0]) * 100

        result = f"""📈 {ticker} 주식 데이터

📊 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}
💰 현재 가격: ${latest_price:.2f}
📈 변화: ${price_change:.2f} ({percent_change:+.2f}%)
📉 최저가: ${df['Low'].min():.2f}
📈 최고가: ${df['High'].max():.2f}
📊 평균 거래량: {df['Volume'].mean():,.0f}

📋 최근 5일 데이터:
"""

        # 최근 5일 데이터 표시
        recent_data = df.tail(5)
        for date, row in recent_data.iterrows():
            result += f"{date.strftime('%Y-%m-%d')}: ${row['Close']:.2f}\n"

        return [TextContent(type="text", text=result)]

    except Exception as e:
        return [TextContent(type="text", text=f"❌ 주식 데이터 조회 실패: {str(e)}")]


if __name__ == "__main__":
    # STDIO 서버 실행
    async def main():
        async with stdio_server(server) as (read_stream, write_stream):
            await server.run(read_stream, write_stream, None)

    import asyncio
    asyncio.run(main())