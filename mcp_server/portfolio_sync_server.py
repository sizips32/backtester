#!/usr/bin/env python3
"""
포트폴리오 백테스터 MCP 서버 - 동기 버전 (가장 안정적)
"""

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
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# 글로벌 포트폴리오 저장소
portfolios = {}

def create_portfolio_tool(name: str, assets: List[str], weights: List[float], initial_capital: float = 100000.0) -> str:
    """포트폴리오 생성"""
    try:
        if len(assets) != len(weights):
            return "❌ 오류: 자산 개수와 비중 개수가 일치하지 않습니다."

        if abs(sum(weights) - 1.0) > 0.01:
            return "❌ 오류: 비중의 합이 1이 아닙니다."

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
        if not DB_AVAILABLE:
            return "❌ 필요한 라이브러리가 설치되지 않았습니다."

        if end_date is None:
            end_date = datetime.now()
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        if start_date is None:
            start_date = end_date - timedelta(days=365)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')

        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date)

        if df.empty:
            return f"❌ {ticker}의 데이터를 찾을 수 없습니다."

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
        recent_data = df.tail(5)
        for date, row in recent_data.iterrows():
            result += f"{date.strftime('%Y-%m-%d')}: ${row['Close']:.2f}\n"

        return result
    except Exception as e:
        return f"❌ 주식 데이터 조회 실패: {str(e)}"

def handle_request(message: dict) -> Optional[dict]:
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
                "serverInfo": {"name": "Portfolio BackTester", "version": "1.0.0"}
            }
        }

    elif method == "notifications/initialized":
        return None

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
            else:
                result_text = f"❌ 알 수 없는 도구: {tool_name}"

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": result_text}]}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32603, "message": f"도구 실행 오류: {str(e)}"}
            }

    else:
        if msg_id:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"알 수 없는 메서드: {method}"}
            }

def main():
    """메인 서버 루프"""
    try:
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                message = json.loads(line)
                response = handle_request(message)

                if response:
                    print(json.dumps(response, ensure_ascii=False))
                    sys.stdout.flush()

            except json.JSONDecodeError:
                continue
            except EOFError:
                break
            except Exception:
                continue
    except Exception:
        pass

if __name__ == "__main__":
    main()