#!/usr/bin/env python3
"""
포트폴리오 백테스터 MCP 서버 - 표준 MCP 구현 (FastMCP 없음)
"""

import asyncio
import json
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# 프로젝트 경로 추가
sys.path.insert(0, "/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester")

# 포트폴리오 백테스터 모듈들
try:
    import pandas as pd
    import numpy as np
    import yfinance as yf
    from utils.database import SessionLocal, Portfolio, PortfolioHolding
    from repository.portfolio_repo import create_portfolio, get_all_portfolios, get_portfolio_by_name
    from repository.holdings_repo import get_portfolio_holdings, add_holding_to_portfolio
    DB_AVAILABLE = True
except ImportError as e:
    DB_AVAILABLE = False

# 글로벌 포트폴리오 저장소 (메모리 백업)
portfolios = {}

def get_db_session():
    """데이터베이스 세션 생성"""
    if DB_AVAILABLE:
        return SessionLocal()
    return None

def create_portfolio_tool(name: str, assets: List[str], weights: List[float], initial_capital: float = 100000.0) -> str:
    """포트폴리오 생성"""
    try:
        # 검증
        if len(assets) != len(weights):
            return "❌ 오류: 자산 개수와 비중 개수가 일치하지 않습니다."

        if abs(sum(weights) - 1.0) > 0.01:
            return "❌ 오류: 비중의 합이 1이 아닙니다."

        # 포트폴리오 저장
        portfolios[name] = {
            "assets": assets,
            "weights": dict(zip(assets, weights)),
            "initial_capital": initial_capital,
            "created_at": datetime.now().isoformat()
        }

        result = f"✅ 포트폴리오 '{name}' 생성 완료\n\n📊 포트폴리오 구성:\n"
        for asset, weight in zip(assets, weights):
            result += f"  • {asset}: {weight*100:.1f}%\n"
        result += f"\n💰 초기 자본: ${initial_capital:,.2f}"

        return result
    except Exception as e:
        return f"❌ 포트폴리오 생성 실패: {str(e)}"

def list_portfolios_tool() -> str:
    """포트폴리오 목록 조회"""
    try:
        if not portfolios:
            return "📝 생성된 포트폴리오가 없습니다."

        result = "📊 포트폴리오 목록:\n\n"
        for name, portfolio in portfolios.items():
            result += f"🔹 **{name}**\n"
            result += f"   자산: {', '.join(portfolio['assets'])}\n"
            result += f"   초기자본: ${portfolio['initial_capital']:,.2f}\n"
            result += f"   생성일: {portfolio['created_at'][:10]}\n\n"

        return result
    except Exception as e:
        return f"❌ 포트폴리오 목록 조회 실패: {str(e)}"

def get_stock_data_tool(ticker: str, start_date: str = None, end_date: str = None) -> str:
    """주식 데이터 조회"""
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
            return f"❌ {ticker}의 데이터를 찾을 수 없습니다."

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

        return result
    except Exception as e:
        return f"❌ 주식 데이터 조회 실패: {str(e)}"

def backtest_portfolio_tool(portfolio_name: str, start_date: str, end_date: str) -> str:
    """포트폴리오 백테스팅"""
    try:
        if portfolio_name not in portfolios:
            return f"❌ 포트폴리오 '{portfolio_name}'을 찾을 수 없습니다."

        portfolio = portfolios[portfolio_name]
        assets = portfolio['assets']
        weights = [portfolio['weights'][asset] for asset in assets]
        initial_capital = portfolio['initial_capital']

        # 기간 설정
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        # 각 자산의 데이터 수집
        data = {}
        for asset in assets:
            stock = yf.Ticker(asset)
            df = stock.history(start=start_dt, end=end_dt)
            if not df.empty:
                data[asset] = df['Close']

        if not data:
            return "❌ 데이터를 가져올 수 없습니다."

        # 포트폴리오 가치 계산
        combined_df = pd.DataFrame(data).ffill().dropna()

        if combined_df.empty:
            return "❌ 유효한 데이터가 없습니다."

        # 정규화 및 가중치 적용
        normalized = combined_df / combined_df.iloc[0]
        portfolio_value = (normalized * weights).sum(axis=1) * initial_capital

        # 성과 지표 계산
        total_return = (portfolio_value.iloc[-1] / portfolio_value.iloc[0] - 1) * 100
        max_value = portfolio_value.max()
        min_value = portfolio_value.min()
        volatility = portfolio_value.pct_change().std() * np.sqrt(252) * 100

        result = f"""📊 '{portfolio_name}' 백테스팅 결과

📅 기간: {start_date} ~ {end_date}
💰 초기 자본: ${initial_capital:,.2f}
💵 최종 가치: ${portfolio_value.iloc[-1]:,.2f}
📈 총 수익률: {total_return:+.2f}%
📊 최고 가치: ${max_value:,.2f}
📉 최저 가치: ${min_value:,.2f}
📊 변동성: {volatility:.2f}%

🔍 자산별 구성:
"""

        for asset, weight in zip(assets, weights):
            result += f"  • {asset}: {weight*100:.1f}%\n"

        return result
    except Exception as e:
        return f"❌ 백테스팅 실패: {str(e)}"

async def handle_request(message: dict) -> dict:
    """MCP 요청 처리"""
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "Portfolio BackTester",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "notifications/initialized":
        return None  # 응답 없음

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [
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
                        "inputSchema": {"type": "object", "properties": {}, "required": []}
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
                    },
                    {
                        "name": "backtest_portfolio",
                        "description": "포트폴리오 백테스팅을 수행합니다",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "portfolio_name": {"type": "string", "description": "포트폴리오 이름"},
                                "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                                "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"}
                            },
                            "required": ["portfolio_name", "start_date", "end_date"]
                        }
                    }
                ]
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "create_portfolio":
                result_text = create_portfolio_tool(**arguments)
            elif tool_name == "list_portfolios":
                result_text = list_portfolios_tool()
            elif tool_name == "get_stock_data":
                result_text = get_stock_data_tool(**arguments)
            elif tool_name == "backtest_portfolio":
                result_text = backtest_portfolio_tool(**arguments)
            else:
                result_text = f"❌ 알 수 없는 도구: {tool_name}"

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": result_text}]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": f"도구 실행 오류: {str(e)}"
                }
            }

    else:
        if msg_id:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"알 수 없는 메서드: {method}"
                }
            }

async def main():
    """메인 서버 루프"""
    try:
        while True:
            try:
                line = sys.stdin.readline()
                if not line or line.strip() == "":
                    continue

                message = json.loads(line.strip())
                response = await handle_request(message)

                if response:
                    print(json.dumps(response, ensure_ascii=False))
                    sys.stdout.flush()

            except json.JSONDecodeError:
                continue
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                # 예상치 못한 에러는 로그만 남기고 계속 실행
                continue
    except Exception:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except:
        sys.exit(1)