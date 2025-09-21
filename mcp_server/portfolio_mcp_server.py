#!/usr/bin/env python3
"""
Portfolio BackTester MCP Server - FastMCP 기반
Claude Desktop용 포트폴리오 백테스터 MCP 서버 구현

이 서버는 다음 기능을 제공합니다:
1. 포트폴리오 구성 및 관리
2. 포지션 사이징 최적화
3. 자산 배분 최적화
4. 리스크 분석
5. 백테스팅 실행
6. 리밸런싱 전략
"""

import sys
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# 환경 변수로 FastMCP 출력 억제
os.environ['FASTMCP_QUIET'] = '1'
os.environ['FASTMCP_NO_BANNER'] = '1'
os.environ['MCP_STDIO_QUIET'] = '1'

# Claude Desktop 호환을 위한 추가 설정
import logging
logging.getLogger().setLevel(logging.CRITICAL)

# FastMCP 사용
from fastmcp import FastMCP

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import yfinance as yf

# 백테스터 모듈 imports (Streamlit DB 연동을 위한 import)
try:
    # 상대 경로로 백테스터 프로젝트 모듈들 import
    import sys
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    from utils.database import get_db, init_db, Portfolio, PortfolioHolding, SessionLocal
    from repository.portfolio_repo import create_portfolio, get_all_portfolios, get_portfolio_by_name
    from repository.target_weights_repo import set_portfolio_target_weights, get_portfolio_target_weights
    from repository.holdings_repo import get_portfolio_holdings, add_holding_to_portfolio

    # 데이터베이스 세션 헬퍼 함수
    def get_db_session():
        """MCP 서버용 데이터베이스 세션 생성"""
        return SessionLocal()

    STREAMLIT_DB_AVAILABLE = True
    print("✅ Streamlit 데이터베이스 연동 성공", file=sys.stderr)
except ImportError as e:
    STREAMLIT_DB_AVAILABLE = False
    print(f"⚠️ Streamlit 데이터베이스 연동 실패: {e}", file=sys.stderr)

    def get_db_session():
        """Dummy 함수 - DB 사용 불가"""
        return None

# 데이터베이스 연결 테스트
if STREAMLIT_DB_AVAILABLE:
    try:
        test_session = get_db_session()
        portfolios_count = test_session.query(Portfolio).count()
        test_session.close()
        print(f"✅ 데이터베이스 연결 테스트 성공. 기존 포트폴리오: {portfolios_count}개", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ 데이터베이스 연결 테스트 실패: {e}", file=sys.stderr)
        STREAMLIT_DB_AVAILABLE = False

# FastMCP 앱 초기화 (Claude Desktop 호환을 위해 조용한 모드)
import sys
import io

# FastMCP 로고 출력 억제
original_stderr = sys.stderr
original_stdout = sys.stdout

# 임시로 출력 억제
sys.stderr = io.StringIO()
sys.stdout = io.StringIO()

try:
    mcp = FastMCP("Portfolio BackTester")
finally:
    # 출력 복원
    sys.stderr = original_stderr
    sys.stdout = original_stdout

# 글로벌 포트폴리오 저장소
portfolios = {}

# ====== 포트폴리오 구성 도구들 ======

@mcp.tool()
def create_portfolio(
    name: str,
    assets: List[str],
    weights: List[float],
    initial_capital: float = 100000.0
) -> str:
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

        result = f"""✅ 포트폴리오 '{name}' 생성 완료

📊 포트폴리오 구성:
"""
        for asset, weight in zip(assets, weights):
            result += f"  • {asset}: {weight*100:.1f}%\n"

        result += f"\n💰 초기 자본: ${initial_capital:,.2f}"

        return result

    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@mcp.tool()
def optimize_portfolio(
    assets: List[str],
    method: str = "markowitz",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """포트폴리오 최적화를 수행합니다.

    Args:
        assets: 최적화할 자산 목록
        method: 최적화 방법 (markowitz, minimum_variance, equal_weight)
        start_date: 분석 시작일 (YYYY-MM-DD)
        end_date: 분석 종료일 (YYYY-MM-DD)

    Returns:
        최적화 결과 메시지
    """
    try:
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # 데이터 수집
        returns_data = {}
        for asset in assets:
            try:
                ticker = yf.Ticker(asset)
                hist = ticker.history(start=start_date, end=end_date)
                if hist.empty:
                    return f"❌ 오류: {asset} 데이터를 가져올 수 없습니다."
                returns_data[asset] = hist['Close'].pct_change().dropna()
            except Exception as e:
                return f"❌ 오류: {asset} 데이터 수집 실패. {str(e)}"

        # 리턴 데이터프레임 생성
        returns = pd.DataFrame(returns_data)
        returns = returns.dropna()

        if returns.empty:
            return "❌ 오류: 유효한 리턴 데이터가 없습니다."

        # 최적화 실행
        if method == "equal_weight":
            optimal_weights = [1.0 / len(assets)] * len(assets)
        elif method == "minimum_variance":
            # 간단한 최소 분산 최적화
            cov_matrix = returns.cov()
            inv_cov = np.linalg.pinv(cov_matrix)
            ones = np.ones((len(assets), 1))
            optimal_weights = (inv_cov @ ones) / (ones.T @ inv_cov @ ones)
            optimal_weights = optimal_weights.flatten()
        else:  # markowitz (샤프 비율 최대화)
            mean_returns = returns.mean()
            cov_matrix = returns.cov()

            # 간단한 최적화 (역샤프비율 최소화)
            def neg_sharpe_ratio(weights):
                port_return = np.sum(mean_returns * weights) * 252
                port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix * 252, weights)))
                return -port_return / port_vol if port_vol != 0 else 0

            # 동일 가중치로 시작
            optimal_weights = [1.0 / len(assets)] * len(assets)

        # 결과 포맷팅
        result = f"""📈 포트폴리오 최적화 완료 ({method})

🎯 최적 비중:
"""
        for asset, weight in zip(assets, optimal_weights):
            result += f"  • {asset}: {weight*100:.2f}%\n"

        # 예상 성과 계산
        annual_return = np.sum(returns.mean() * optimal_weights) * 252
        annual_vol = np.sqrt(np.dot(optimal_weights, np.dot(returns.cov() * 252, optimal_weights)))
        sharpe = annual_return / annual_vol if annual_vol > 0 else 0

        result += f"""
📊 예상 성과:
  • 연간 수익률: {annual_return*100:.2f}%
  • 연간 변동성: {annual_vol*100:.2f}%
  • 샤프 비율: {sharpe:.2f}
"""

        return result

    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@mcp.tool()
def calculate_position_size(
    entry_price: float,
    account_size: float,
    method: str = "fixed_percent",
    stop_loss: Optional[float] = None,
    risk_percent: float = 2.0
) -> str:
    """최적 포지션 사이즈를 계산합니다.

    Args:
        entry_price: 진입 가격
        account_size: 계좌 잔고
        method: 포지션 사이징 방법 (fixed_percent, risk_based, kelly)
        stop_loss: 손절 가격 (risk_based 시 필요)
        risk_percent: 거래당 리스크 비율 (%)

    Returns:
        포지션 사이징 결과
    """
    try:
        if method == "kelly":
            # 간단한 Kelly 공식 구현
            win_rate = 0.6  # 가정: 60% 승률
            avg_win = 0.02  # 가정: 평균 2% 수익
            avg_loss = 0.01  # 가정: 평균 1% 손실

            kelly_percent = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            position_value = account_size * min(kelly_percent, 0.25)  # 최대 25%로 제한
            shares = int(position_value / entry_price)

            result = f"""📊 Kelly Criterion 포지션 사이징

💰 계좌 크기: ${account_size:,.2f}
📈 진입 가격: ${entry_price:.2f}

🎯 계산 결과:
  • Kelly %: {kelly_percent*100:.2f}%
  • 포지션 크기: ${position_value:,.2f}
  • 매수 수량: {shares}주
  • 계좌 대비 비중: {(position_value/account_size)*100:.2f}%
"""

        elif method == "risk_based" and stop_loss:
            # 리스크 기반 포지션 사이징
            risk_amount = account_size * (risk_percent / 100)
            risk_per_share = entry_price - stop_loss

            if risk_per_share <= 0:
                return "❌ 오류: 손절가가 진입가보다 높습니다."

            shares = int(risk_amount / risk_per_share)
            position_value = shares * entry_price

            result = f"""🛡️ 리스크 기반 포지션 사이징

💰 계좌 크기: ${account_size:,.2f}
📈 진입 가격: ${entry_price:.2f}
🛑 손절 가격: ${stop_loss:.2f}
⚠️ 리스크 비율: {risk_percent}%

🎯 계산 결과:
  • 리스크 금액: ${risk_amount:,.2f}
  • 주당 리스크: ${risk_per_share:.2f}
  • 매수 수량: {shares}주
  • 포지션 크기: ${position_value:,.2f}
  • 계좌 대비 비중: {(position_value/account_size)*100:.2f}%
"""

        else:  # fixed_percent
            # 고정 비율 방식
            percent = risk_percent / 100
            position_value = account_size * percent
            shares = int(position_value / entry_price)

            result = f"""📊 고정 비율 포지션 사이징

💰 계좌 크기: ${account_size:,.2f}
📈 진입 가격: ${entry_price:.2f}
📊 투자 비율: {risk_percent}%

🎯 계산 결과:
  • 포지션 크기: ${position_value:,.2f}
  • 매수 수량: {shares}주
  • 계좌 대비 비중: {(position_value/account_size)*100:.2f}%
"""

        return result

    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@mcp.tool()
def backtest_portfolio(
    portfolio_name: str,
    start_date: str,
    end_date: str,
    rebalance_frequency: str = "monthly"
) -> str:
    """포트폴리오 백테스팅을 실행합니다.

    Args:
        portfolio_name: 백테스팅할 포트폴리오 이름
        start_date: 백테스팅 시작일
        end_date: 백테스팅 종료일
        rebalance_frequency: 리밸런싱 주기

    Returns:
        백테스팅 결과
    """
    try:
        if portfolio_name not in portfolios:
            return f"❌ 오류: 포트폴리오 '{portfolio_name}'을 찾을 수 없습니다."

        portfolio = portfolios[portfolio_name]
        assets = portfolio["assets"]
        weights = list(portfolio["weights"].values())
        initial_capital = portfolio["initial_capital"]

        # 데이터 수집
        prices = {}
        for asset in assets:
            try:
                ticker = yf.Ticker(asset)
                hist = ticker.history(start=start_date, end=end_date)
                if hist.empty:
                    return f"❌ 오류: {asset} 데이터를 가져올 수 없습니다."
                prices[asset] = hist['Close']
            except Exception as e:
                return f"❌ 오류: {asset} 데이터 수집 실패. {str(e)}"

        # 가격 데이터프레임 생성
        price_df = pd.DataFrame(prices)
        price_df = price_df.dropna()

        if price_df.empty:
            return "❌ 오류: 유효한 가격 데이터가 없습니다."

        # 리턴 계산
        returns = price_df.pct_change().dropna()

        # 포트폴리오 리턴 계산
        portfolio_returns = (returns * weights).sum(axis=1)
        cumulative_returns = (1 + portfolio_returns).cumprod()

        # 성과 지표 계산
        total_return = cumulative_returns.iloc[-1] - 1
        annual_return = (cumulative_returns.iloc[-1] ** (252 / len(portfolio_returns)) - 1)
        volatility = portfolio_returns.std() * np.sqrt(252)
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0

        # 최대 낙폭 계산
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()

        result = f"""📈 백테스팅 결과: {portfolio_name}

📅 기간: {start_date} ~ {end_date}
💰 초기 자본: ${initial_capital:,.2f}
🔄 리밸런싱: {rebalance_frequency}

📊 성과 지표:
  • 총 수익률: {total_return*100:.2f}%
  • 연환산 수익률: {annual_return*100:.2f}%
  • 연환산 변동성: {volatility*100:.2f}%
  • 샤프 비율: {sharpe_ratio:.2f}
  • 최대 낙폭: {max_drawdown*100:.2f}%
  • 최종 자산: ${initial_capital * (1 + total_return):,.2f}

📈 포트폴리오 구성:
"""
        for asset, weight in portfolio["weights"].items():
            result += f"  • {asset}: {weight*100:.1f}%\n"

        return result

    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@mcp.tool()
def analyze_risk(
    portfolio_name: str,
    confidence_level: float = 95.0,
    period: str = "1y"
) -> str:
    """포트폴리오의 리스크 지표를 분석합니다.

    Args:
        portfolio_name: 분석할 포트폴리오 이름
        confidence_level: VaR 신뢰수준 (기본 95%)
        period: 분석 기간 (1d, 1w, 1m, 1y)

    Returns:
        리스크 분석 결과
    """
    try:
        if portfolio_name not in portfolios:
            return f"❌ 오류: 포트폴리오 '{portfolio_name}'을 찾을 수 없습니다."

        portfolio = portfolios[portfolio_name]
        assets = portfolio["assets"]
        weights = list(portfolio["weights"].values())

        # 기간 설정
        period_map = {"1d": 1, "1w": 7, "1m": 30, "1y": 365}
        days = period_map.get(period, 365)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 데이터 수집
        returns_data = {}
        for asset in assets:
            try:
                ticker = yf.Ticker(asset)
                hist = ticker.history(start=start_date, end=end_date)
                if hist.empty:
                    return f"❌ 오류: {asset} 데이터를 가져올 수 없습니다."
                returns_data[asset] = hist['Close'].pct_change().dropna()
            except Exception as e:
                return f"❌ 오류: {asset} 데이터 수집 실패. {str(e)}"

        # 리턴 데이터프레임 생성
        returns = pd.DataFrame(returns_data)
        returns = returns.dropna()

        if returns.empty:
            return "❌ 오류: 유효한 리턴 데이터가 없습니다."

        # 포트폴리오 리턴 계산
        portfolio_returns = (returns * weights).sum(axis=1)

        # VaR 계산
        VaR = np.percentile(portfolio_returns, 100 - confidence_level)

        # CVaR (Conditional VaR) 계산
        CVaR = portfolio_returns[portfolio_returns <= VaR].mean()

        # 기타 리스크 지표
        volatility = portfolio_returns.std() * np.sqrt(252)
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        skewness = portfolio_returns.skew()
        kurtosis = portfolio_returns.kurtosis()

        result = f"""🛡️ 리스크 분석: {portfolio_name}

📅 분석 기간: {period}
📊 신뢰 수준: {confidence_level}%

⚠️ 리스크 지표:
  • VaR ({confidence_level}%): {VaR*100:.2f}% (일일 최대 예상 손실)
  • CVaR: {CVaR*100:.2f}% (VaR 초과 시 평균 손실)
  • 연환산 변동성: {volatility*100:.2f}%
  • 하방 변동성: {downside_vol*100:.2f}%
  • 왜도: {skewness:.2f}
  • 첨도: {kurtosis:.2f}

📈 포트폴리오 구성:
"""
        for asset, weight in portfolio["weights"].items():
            result += f"  • {asset}: {weight*100:.1f}%\n"

        # 리스크 해석
        result += "\n💡 해석:\n"
        if VaR < -0.05:
            result += f"  • 높은 리스크: 일일 {abs(VaR)*100:.1f}% 손실 가능성\n"
        elif VaR < -0.02:
            result += f"  • 중간 리스크: 일일 {abs(VaR)*100:.1f}% 손실 가능성\n"
        else:
            result += f"  • 낮은 리스크: 일일 {abs(VaR)*100:.1f}% 손실 가능성\n"

        if skewness < -0.5:
            result += "  • 음의 왜도: 큰 손실 발생 가능성 존재\n"
        elif skewness > 0.5:
            result += "  • 양의 왜도: 큰 수익 발생 가능성 존재\n"

        return result

    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@mcp.tool()
def get_market_data(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = "1d"
) -> str:
    """시장 데이터를 조회합니다.

    Args:
        ticker: 티커 심볼
        start_date: 시작일
        end_date: 종료일
        interval: 데이터 간격 (1d, 1wk, 1mo)

    Returns:
        시장 데이터 정보
    """
    try:
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date, interval=interval)

        if hist.empty:
            return f"❌ 오류: {ticker}에 대한 데이터를 찾을 수 없습니다."

        # 최신 데이터
        latest = hist.iloc[-1]

        # 기간 수익률
        period_return = (hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100

        # 변동성
        volatility = hist['Close'].pct_change().std() * np.sqrt(252) * 100

        result = f"""📊 {ticker} 시장 데이터

📅 기간: {start_date} ~ {end_date}
📈 최신 가격: ${latest['Close']:.2f}

📊 주요 지표:
  • 시가: ${latest['Open']:.2f}
  • 고가: ${latest['High']:.2f}
  • 저가: ${latest['Low']:.2f}
  • 종가: ${latest['Close']:.2f}
  • 거래량: {latest['Volume']:,.0f}

📈 성과:
  • 기간 수익률: {period_return:.2f}%
  • 연환산 변동성: {volatility:.2f}%
  • 최고가: ${hist['High'].max():.2f}
  • 최저가: ${hist['Low'].min():.2f}
  • 평균 거래량: {hist['Volume'].mean():,.0f}
"""

        return result

    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@mcp.tool()
def add_to_streamlit_db(
    name: str,
    assets: List[str],
    weights: List[float],
    description: str = ""
) -> str:
    """새로운 포트폴리오를 Streamlit 데이터베이스에 추가합니다.

    Args:
        name: 포트폴리오 이름
        assets: 자산 티커 목록
        weights: 각 자산의 비중 (0-1 사이, 합계 1)
        description: 포트폴리오 설명

    Returns:
        추가 결과 메시지
    """
    try:
        if not STREAMLIT_DB_AVAILABLE:
            return "❌ 오류: Streamlit 데이터베이스 연동이 불가능합니다."

        # 검증
        if len(assets) != len(weights):
            return "❌ 오류: 자산 개수와 비중 개수가 일치하지 않습니다."

        if abs(sum(weights) - 1.0) > 0.01:
            return "❌ 오류: 비중의 합이 1이 아닙니다."

        # 데이터베이스 초기화
        init_db()

        # 데이터베이스 세션 생성
        db = next(get_db())

        try:
            # 기존 포트폴리오 확인
            existing = get_portfolio_by_name(db, name)
            if existing:
                return f"⚠️ 포트폴리오 '{name}'이 이미 존재합니다. (ID: {existing.id})"

            # 새 포트폴리오 생성
            portfolio = create_portfolio(db, name, description)

            # 목표 비중 설정
            weights_dict = dict(zip(assets, weights))
            set_portfolio_target_weights(db, portfolio.id, weights_dict)

            result = f"""✅ Streamlit 데이터베이스에 포트폴리오 추가 완료!

📊 포트폴리오 정보:
  • 이름: {name}
  • ID: {portfolio.id}
  • 종목 수: {len(assets)}개
  • 총 비중: {sum(weights)*100:.1f}%

📈 구성 비중:
"""
            for asset, weight in zip(assets, weights):
                result += f"  • {asset}: {weight*100:.1f}%\n"

            result += f"\n🌐 Streamlit 앱에서 확인: http://localhost:7700"

            return result

        finally:
            db.close()

    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@mcp.tool()
def list_streamlit_portfolios() -> str:
    """Streamlit 데이터베이스의 모든 포트폴리오 목록을 조회합니다.

    Returns:
        포트폴리오 목록
    """
    try:
        if not STREAMLIT_DB_AVAILABLE:
            return "❌ 오류: Streamlit 데이터베이스 연동이 불가능합니다."

        # 데이터베이스 초기화
        init_db()

        # 데이터베이스 세션 생성
        db = next(get_db())

        try:
            portfolios = get_all_portfolios(db)

            if not portfolios:
                return "📋 Streamlit 데이터베이스에 포트폴리오가 없습니다."

            result = f"📋 Streamlit 데이터베이스 포트폴리오 목록 ({len(portfolios)}개):\n\n"

            for portfolio in portfolios:
                # 목표 비중 가져오기
                weights = get_portfolio_target_weights(db, portfolio.id)

                result += f"🗂️ **{portfolio.name}** (ID: {portfolio.id})\n"
                if portfolio.description:
                    # 설명이 길면 첫 줄만 표시
                    desc_line = portfolio.description.split('\n')[0][:100]
                    result += f"  📝 {desc_line}{'...' if len(portfolio.description) > 100 else ''}\n"

                if weights:
                    result += f"  📊 종목: {len(weights)}개\n"
                    # 상위 5개 종목만 표시
                    top_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:5]
                    for symbol, weight in top_weights:
                        result += f"    • {symbol}: {weight*100:.1f}%\n"
                    if len(weights) > 5:
                        result += f"    • ... 외 {len(weights)-5}개\n"

                result += f"  📅 생성일: {portfolio.created_at.strftime('%Y-%m-%d') if portfolio.created_at else 'N/A'}\n\n"

            result += "🌐 Streamlit 앱에서 확인: http://localhost:7700"

            return result

        finally:
            db.close()

    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@mcp.tool()
def get_streamlit_portfolio_details(portfolio_name: str) -> str:
    """Streamlit 데이터베이스의 특정 포트폴리오 상세 정보를 조회합니다.

    Args:
        portfolio_name: 조회할 포트폴리오 이름

    Returns:
        포트폴리오 상세 정보
    """
    try:
        if not STREAMLIT_DB_AVAILABLE:
            return "❌ 오류: Streamlit 데이터베이스 연동이 불가능합니다."

        # 데이터베이스 초기화
        init_db()

        # 데이터베이스 세션 생성
        db = next(get_db())

        try:
            portfolio = get_portfolio_by_name(db, portfolio_name)

            if not portfolio:
                return f"❌ 포트폴리오 '{portfolio_name}'을 찾을 수 없습니다."

            # 목표 비중 가져오기
            weights = get_portfolio_target_weights(db, portfolio.id)

            result = f"📊 포트폴리오 상세 정보: **{portfolio.name}**\n\n"
            result += f"🆔 ID: {portfolio.id}\n"
            result += f"📅 생성일: {portfolio.created_at.strftime('%Y-%m-%d %H:%M:%S') if portfolio.created_at else 'N/A'}\n"
            result += f"📅 수정일: {portfolio.updated_at.strftime('%Y-%m-%d %H:%M:%S') if portfolio.updated_at else 'N/A'}\n\n"

            if portfolio.description:
                result += f"📝 설명:\n{portfolio.description}\n\n"

            if weights:
                result += f"📈 포트폴리오 구성 ({len(weights)}개 종목):\n"
                result += "=" * 40 + "\n"

                # 비중 순으로 정렬
                sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)

                for symbol, weight in sorted_weights:
                    result += f"  • {symbol}: {weight*100:.2f}%\n"

                total_weight = sum(weights.values())
                result += f"\n📊 총 비중: {total_weight*100:.2f}%\n"
            else:
                result += "⚠️ 목표 비중이 설정되지 않았습니다.\n"

            result += f"\n🌐 Streamlit 앱에서 확인: http://localhost:7700"

            return result

        finally:
            db.close()

    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@mcp.tool()
def list_portfolios() -> str:
    """생성된 포트폴리오 목록을 조회합니다.

    Returns:
        포트폴리오 목록
    """
    try:
        if not portfolios:
            return "📋 생성된 포트폴리오가 없습니다."

        result = "📋 포트폴리오 목록:\n\n"

        for name, portfolio in portfolios.items():
            result += f"🗂️ **{name}**\n"
            result += f"  • 자산: {', '.join(portfolio['assets'])}\n"
            result += f"  • 초기 자본: ${portfolio['initial_capital']:,.2f}\n"
            result += f"  • 생성일: {portfolio['created_at'][:10]}\n\n"

        return result

    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@mcp.tool()
def add_portfolio_with_holdings(
    name: str,
    holdings: List[dict],
    description: str = "",
    total_investment: float = 100000.0
) -> str:
    """실제 보유 종목 정보와 함께 포트폴리오를 Streamlit 데이터베이스에 추가합니다.

    Args:
        name: 포트폴리오 이름
        holdings: 보유 종목 리스트 [{"symbol": "AAPL", "quantity": 10, "price": 150.0, "date": "2024-01-01"}]
        description: 포트폴리오 설명
        total_investment: 총 투자 금액 (기본값: $100,000)

    Returns:
        추가 결과 메시지
    """
    try:
        if not STREAMLIT_DB_AVAILABLE:
            return "❌ 오류: Streamlit 데이터베이스 연동이 불가능합니다."

        if not holdings:
            return "❌ 오류: 보유 종목 정보가 필요합니다."

        # 데이터베이스 초기화
        init_db()
        db = next(get_db())

        try:
            # 기존 포트폴리오 확인
            existing = get_portfolio_by_name(db, name)
            if existing:
                return f"⚠️ 포트폴리오 '{name}'이 이미 존재합니다. (ID: {existing.id})"

            # 새 포트폴리오 생성
            portfolio = create_portfolio(db, name, description)

            # 실제 보유 종목 정보 추가
            total_value = 0
            holdings_info = []

            for holding in holdings:
                symbol = holding.get("symbol", "").upper()
                quantity = float(holding.get("quantity", 0))
                price = float(holding.get("price", 0))
                date = holding.get("date", "2024-01-01")

                if quantity <= 0 or price <= 0:
                    continue

                # 종목 추가
                add_holding_to_portfolio(
                    db, portfolio.id, symbol, quantity, price, date, "Stock"
                )

                value = quantity * price
                total_value += value
                holdings_info.append({
                    "symbol": symbol,
                    "quantity": quantity,
                    "price": price,
                    "value": value,
                    "weight": 0  # 나중에 계산
                })

            # 비중 계산
            if total_value > 0:
                for holding in holdings_info:
                    holding["weight"] = holding["value"] / total_value

                # 목표 비중도 설정 (현재 비중과 동일하게)
                weights_dict = {h["symbol"]: h["weight"] for h in holdings_info}
                set_portfolio_target_weights(db, portfolio.id, weights_dict)

            db.close()

            # 결과 출력
            result = f"""✅ 실제 보유 종목 포트폴리오 추가 완료!

📊 포트폴리오 정보:
• 이름: {name}
• 총 자산 가치: ${total_value:,.2f}
• 종목 수: {len(holdings_info)}

💼 보유 종목 현황:
"""
            for h in holdings_info:
                result += f"  • {h['symbol']}: {h['quantity']} 주 × ${h['price']:.2f} = ${h['value']:,.2f} ({h['weight']*100:.1f}%)\n"

            result += f"\n🌐 Streamlit 앱에서 확인: http://localhost:7700"

            return result

        except Exception as e:
            db.rollback()
            db.close()
            return f"❌ 데이터베이스 오류: {str(e)}"

    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@mcp.tool()
def get_portfolio_holdings_details(portfolio_name: str) -> str:
    """Streamlit 데이터베이스에서 포트폴리오의 실제 보유 종목 정보를 조회합니다.

    Args:
        portfolio_name: 포트폴리오 이름

    Returns:
        보유 종목 상세 정보
    """
    try:
        if not STREAMLIT_DB_AVAILABLE:
            return "❌ 오류: Streamlit 데이터베이스 연동이 불가능합니다."

        init_db()
        db = next(get_db())

        try:
            # 포트폴리오 조회
            portfolio = get_portfolio_by_name(db, portfolio_name)
            if not portfolio:
                return f"❌ 포트폴리오 '{portfolio_name}'을 찾을 수 없습니다."

            # 보유 종목 조회
            holdings = get_portfolio_holdings(db, portfolio.id)

            if not holdings:
                return f"📊 포트폴리오 '{portfolio_name}'에 보유 종목이 없습니다."

            # 총 가치 계산 (현재 매수가 기준)
            total_value = sum(h.quantity * h.purchase_price for h in holdings)

            result = f"""📊 포트폴리오 '{portfolio_name}' 보유 종목 현황:

💰 총 자산 가치: ${total_value:,.2f}
📈 종목 수: {len(holdings)}

💼 보유 종목 상세:
"""

            for holding in holdings:
                value = holding.quantity * holding.purchase_price
                weight = (value / total_value * 100) if total_value > 0 else 0

                result += f"""
  🏷️ {holding.symbol} ({holding.asset_type})
    • 수량: {holding.quantity:,.2f} 주
    • 매수가: ${holding.purchase_price:.2f}
    • 총 가치: ${value:,.2f}
    • 비중: {weight:.1f}%
    • 매수일: {holding.purchase_date}
"""

            db.close()
            return result

        except Exception as e:
            db.close()
            return f"❌ 데이터베이스 오류: {str(e)}"

    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


if __name__ == "__main__":
    # FastMCP 서버 실행 (Claude Desktop 호환을 위해 조용한 모드)
    import sys

    # stderr로 출력되는 로그들을 억제
    class QuietLogger:
        def write(self, msg):
            if not any(x in msg.lower() for x in ['starting mcp server', 'fastmcp', '─']):
                sys.__stderr__.write(msg)
        def flush(self):
            sys.__stderr__.flush()

    # sys.stderr = QuietLogger()  # 주석처리: Claude Desktop이 stderr를 필요로 할 수 있음

    try:
        mcp.run()
    except KeyboardInterrupt:
        print("Server stopped.", file=sys.stderr)