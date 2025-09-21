#!/usr/bin/env python3
"""
기존 포트폴리오에 실제 보유 종목 데이터를 추가하는 스크립트
"""

from sqlalchemy.orm import Session
from utils.database import get_db, init_db
from repository.portfolio_repo import get_portfolio_by_name
from repository.target_weights_repo import get_portfolio_target_weights
from repository.holdings_repo import add_holding_to_portfolio, get_portfolio_holdings

def add_holdings_to_dividend_portfolio():
    """한국투자자_배당안정형_v2 포트폴리오에 실제 보유 종목 추가"""

    # 데이터베이스 초기화
    init_db()

    # 데이터베이스 세션 생성
    db: Session = next(get_db())

    try:
        portfolio_name = "한국투자자_배당안정형_v2"

        # 포트폴리오 찾기
        portfolio = get_portfolio_by_name(db, portfolio_name)
        if not portfolio:
            print(f"❌ 포트폴리오 '{portfolio_name}'을 찾을 수 없습니다.")
            return None

        print(f"✅ 포트폴리오 '{portfolio_name}' 발견 (ID: {portfolio.id})")

        # 기존 보유 종목 확인
        existing_holdings = get_portfolio_holdings(db, portfolio.id)
        if existing_holdings:
            print(f"⚠️ 이미 {len(existing_holdings)}개의 보유 종목이 있습니다.")
            return portfolio.id

        # 목표 비중 가져오기
        target_weights = get_portfolio_target_weights(db, portfolio.id)
        if not target_weights:
            print("❌ 목표 비중 데이터가 없습니다.")
            return None

        print(f"📊 목표 비중: {len(target_weights)}개 종목")

        # 가상의 투자 금액 설정 (30만 달러)
        total_investment = 300000.0

        # 각 종목별 대략적인 현재 가격 (2024년 기준 추정)
        estimated_prices = {
            # 배당주 ETF
            "VYM": 115.50,     # Vanguard High Dividend Yield
            "SCHD": 78.25,     # Schwab US Dividend Equity
            "HDV": 104.80,     # iShares High Dividend
            "VIG": 185.60,     # Vanguard Dividend Appreciation
            "DGRO": 63.40,     # iShares Core Dividend Growth
            "VEA": 52.30,      # Vanguard FTSE Developed Markets
            "VWO": 44.15,      # Vanguard Emerging Markets

            # 리츠 & 부동산
            "VNQ": 95.75,      # Vanguard Real Estate
            "O": 58.90,        # Realty Income Corp
            "STAG": 38.20,     # Stag Industrial

            # 섹터별 배당주
            "XLU": 75.45,      # Utilities Select SPDR
            "XLP": 78.30,      # Consumer Staples SPDR
            "KMI": 18.95,      # Kinder Morgan

            # 개별 우량 배당주
            "JNJ": 162.85,     # Johnson & Johnson
            "PG": 165.20,      # Procter & Gamble
            "KO": 61.45,       # Coca-Cola
            "PEP": 175.30,     # PepsiCo
            "MCD": 295.80,     # McDonald's

            # 채권
            "AGG": 98.45,      # Core US Aggregate Bond
        }

        # 매수일 설정 (2024년 초)
        purchase_date = "2024-01-15"

        holdings_added = 0
        total_value = 0

        print("\n💼 보유 종목 추가 중...")
        print("=" * 60)

        for symbol, target_weight in target_weights.items():
            if symbol in estimated_prices:
                price = estimated_prices[symbol]

                # 목표 비중에 따른 투자 금액 계산
                investment_amount = total_investment * target_weight

                # 수량 계산 (소수점 가능)
                quantity = round(investment_amount / price, 2)

                # 실제 투자 금액
                actual_value = quantity * price
                total_value += actual_value

                # 보유 종목 추가
                try:
                    add_holding_to_portfolio(
                        db, portfolio.id, symbol, quantity, price, purchase_date, "Stock"
                    )
                    holdings_added += 1

                    print(f"  ✅ {symbol}: {quantity} 주 × ${price:.2f} = ${actual_value:,.2f} ({target_weight*100:.1f}%)")

                except Exception as e:
                    print(f"  ❌ {symbol} 추가 실패: {str(e)}")
            else:
                print(f"  ⚠️ {symbol}: 가격 정보 없음 (건너뜀)")

        print("=" * 60)
        print(f"✅ 보유 종목 추가 완료!")
        print(f"📊 추가된 종목: {holdings_added}개")
        print(f"💰 총 투자 금액: ${total_value:,.2f}")
        print(f"🎯 목표 금액: ${total_investment:,.2f}")
        print(f"📈 투자 효율: {(total_value/total_investment)*100:.2f}%")

        print(f"\n📱 Streamlit 앱 (http://localhost:7700)에서 확인하세요.")

        return portfolio.id

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        db.rollback()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 기존 포트폴리오에 보유 종목 추가 시작...")
    portfolio_id = add_holdings_to_dividend_portfolio()
    if portfolio_id:
        print(f"\n✅ 성공적으로 완료되었습니다! (포트폴리오 ID: {portfolio_id})")
    else:
        print("\n❌ 보유 종목 추가에 실패했습니다.")