#!/usr/bin/env python3
"""
배당 중심 안정형 포트폴리오를 Streamlit 앱 데이터베이스에 추가하는 스크립트
"""

from sqlalchemy.orm import Session
from utils.database import get_db, init_db
from repository.portfolio_repo import create_portfolio, get_portfolio_by_name
from repository.target_weights_repo import set_portfolio_target_weights

def add_dividend_portfolio():
    """배당 중심 안정형 포트폴리오를 데이터베이스에 추가"""

    # 데이터베이스 초기화
    init_db()

    # 데이터베이스 세션 생성
    db: Session = next(get_db())

    try:
        # 포트폴리오 정보
        portfolio_name = "한국투자자_배당안정형_v2"
        portfolio_description = """배당 수익률과 안정성에 중점을 둔 분산 투자 포트폴리오

📊 투자 전략:
• 배당주 ETF 중심 (50%)
• 리츠 & 부동산 (15%)
• 섹터별 배당주 (15%)
• 개별 우량 배당주 (15%)
• 채권 (5%)

🎯 목표:
• 연 4-6% 배당 수익률
• 낮은 변동성
• 인플레이션 헤지
• 장기 안정 성장

💰 목표 자본: $300,000 (약 4억원)"""

        # 포트폴리오가 이미 존재하는지 확인
        existing_portfolio = get_portfolio_by_name(db, portfolio_name)
        if existing_portfolio:
            print(f"⚠️ 포트폴리오 '{portfolio_name}'이 이미 존재합니다.")
            return existing_portfolio.id

        # 새 포트폴리오 생성
        portfolio = create_portfolio(db, portfolio_name, portfolio_description)
        print(f"✅ 포트폴리오 '{portfolio_name}' 생성 완료 (ID: {portfolio.id})")

        # 목표 비중 설정 (비중의 합 = 1.0)
        target_weights = {
            # 배당주 ETF (50%)
            "VYM": 0.12,    # Vanguard High Dividend Yield
            "SCHD": 0.10,   # Schwab US Dividend Equity
            "HDV": 0.08,    # iShares High Dividend
            "VIG": 0.07,    # Vanguard Dividend Appreciation
            "DGRO": 0.06,   # iShares Core Dividend Growth
            "VEA": 0.04,    # Vanguard FTSE Developed Markets
            "VWO": 0.03,    # Vanguard Emerging Markets

            # 리츠 & 부동산 (15%)
            "VNQ": 0.08,    # Vanguard Real Estate
            "O": 0.04,      # Realty Income Corp
            "STAG": 0.03,   # Stag Industrial

            # 섹터별 배당주 (15%)
            "XLU": 0.06,    # Utilities Select SPDR
            "XLP": 0.05,    # Consumer Staples SPDR
            "KMI": 0.04,    # Kinder Morgan

            # 개별 우량 배당주 (15%)
            "JNJ": 0.04,    # Johnson & Johnson
            "PG": 0.04,     # Procter & Gamble
            "KO": 0.03,     # Coca-Cola
            "PEP": 0.02,    # PepsiCo
            "MCD": 0.02,    # McDonald's

            # 채권 (5%)
            "AGG": 0.05,    # Core US Aggregate Bond
        }

        # 비중 합계 확인
        total_weight = sum(target_weights.values())
        print(f"📊 총 비중 합계: {total_weight:.3f}")

        if abs(total_weight - 1.0) > 0.001:
            print(f"⚠️ 비중 합계가 1.0이 아닙니다: {total_weight}")
            return None

        # 목표 비중 저장
        set_portfolio_target_weights(db, portfolio.id, target_weights)
        print(f"✅ 목표 비중 설정 완료 ({len(target_weights)}개 종목)")

        # 포트폴리오 구성 요약 출력
        print("\n📈 포트폴리오 구성 요약:")
        print("=" * 50)

        print("\n🏦 배당주 ETF (50%):")
        etf_weights = {k: v for k, v in target_weights.items() if k in ["VYM", "SCHD", "HDV", "VIG", "DGRO", "VEA", "VWO"]}
        for symbol, weight in etf_weights.items():
            print(f"  • {symbol}: {weight*100:.1f}%")

        print("\n🏢 리츠 & 부동산 (15%):")
        reit_weights = {k: v for k, v in target_weights.items() if k in ["VNQ", "O", "STAG"]}
        for symbol, weight in reit_weights.items():
            print(f"  • {symbol}: {weight*100:.1f}%")

        print("\n⚡ 섹터별 배당주 (15%):")
        sector_weights = {k: v for k, v in target_weights.items() if k in ["XLU", "XLP", "KMI"]}
        for symbol, weight in sector_weights.items():
            print(f"  • {symbol}: {weight*100:.1f}%")

        print("\n🎯 개별 우량 배당주 (15%):")
        individual_weights = {k: v for k, v in target_weights.items() if k in ["JNJ", "PG", "KO", "PEP", "MCD"]}
        for symbol, weight in individual_weights.items():
            print(f"  • {symbol}: {weight*100:.1f}%")

        print("\n💰 채권 (5%):")
        bond_weights = {k: v for k, v in target_weights.items() if k in ["AGG"]}
        for symbol, weight in bond_weights.items():
            print(f"  • {symbol}: {weight*100:.1f}%")

        print(f"\n🎉 포트폴리오 '{portfolio_name}' 추가 완료!")
        print(f"📱 Streamlit 앱 (http://localhost:7700)에서 확인하세요.")

        return portfolio.id

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        db.rollback()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 배당 중심 안정형 포트폴리오 추가 시작...")
    portfolio_id = add_dividend_portfolio()
    if portfolio_id:
        print(f"\n✅ 성공적으로 완료되었습니다! (포트폴리오 ID: {portfolio_id})")
    else:
        print("\n❌ 포트폴리오 추가에 실패했습니다.")