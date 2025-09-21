#!/usr/bin/env python3
"""
기존 포트폴리오의 Holdings 데이터를 기반으로 목표 비중(Target Weights) 자동 생성
"""

from sqlalchemy.orm import Session
from utils.database import get_db, init_db
from repository.portfolio_repo import get_all_portfolios
from repository.holdings_repo import get_portfolio_holdings
from repository.target_weights_repo import set_portfolio_target_weights, get_portfolio_target_weights
import yfinance as yf
from datetime import datetime

def get_current_price(symbol):
    """현재 주가 조회 (yfinance 사용)"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
        return None
    except Exception:
        return None

def migrate_holdings_to_target_weights():
    """Holdings 데이터를 기반으로 목표 비중 자동 생성"""

    init_db()
    db: Session = next(get_db())

    try:
        portfolios = get_all_portfolios(db)

        processed_count = 0
        skipped_count = 0

        print("🔄 Holdings → Target Weights 마이그레이션 시작")
        print("=" * 60)

        for portfolio in portfolios:
            print(f"\n📁 처리 중: {portfolio.name} (ID: {portfolio.id})")

            # 이미 목표 비중이 있는지 확인
            existing_weights = get_portfolio_target_weights(db, portfolio.id)
            if existing_weights:
                print(f"   ⚠️ 건너뜀: 이미 목표 비중 존재 ({len(existing_weights)}개 자산)")
                skipped_count += 1
                continue

            # Holdings 데이터 조회
            holdings = get_portfolio_holdings(db, portfolio.id)
            if not holdings:
                print(f"   ❌ 건너뜀: Holdings 데이터 없음")
                skipped_count += 1
                continue

            print(f"   📊 Holdings: {len(holdings)}개 자산")

            # 현재 가치 계산 (Holdings의 purchase_price 사용)
            total_value = 0
            asset_values = {}

            for holding in holdings:
                # Holdings에 저장된 매수가 사용
                current_price = holding.purchase_price
                value = holding.quantity * current_price
                total_value += value
                asset_values[holding.symbol] = value

                print(f"      • {holding.symbol}: {holding.quantity:.2f} 주 × ${current_price:.2f} = ${value:,.2f}")

            if total_value <= 0:
                print(f"   ❌ 건너뜀: 총 가치가 0")
                skipped_count += 1
                continue

            # 비중 계산
            target_weights = {}
            for symbol, value in asset_values.items():
                weight = value / total_value
                target_weights[symbol] = weight

            # 목표 비중 저장
            success = set_portfolio_target_weights(db, portfolio.id, target_weights)

            if success:
                print(f"   ✅ 성공: 목표 비중 생성 (총 가치: ${total_value:,.2f})")

                # 상위 5개 자산 비중 표시
                sorted_weights = sorted(target_weights.items(), key=lambda x: x[1], reverse=True)
                print(f"   📈 주요 자산 비중:")
                for symbol, weight in sorted_weights[:5]:
                    print(f"      - {symbol}: {weight*100:.1f}%")

                processed_count += 1
            else:
                print(f"   ❌ 실패: 목표 비중 저장 실패")
                skipped_count += 1

        print("\n" + "=" * 60)
        print(f"🎉 마이그레이션 완료!")
        print(f"   ✅ 처리 완료: {processed_count}개 포트폴리오")
        print(f"   ⚠️ 건너뜀: {skipped_count}개 포트폴리오")
        print(f"   📊 총 포트폴리오: {len(portfolios)}개")

        return processed_count

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        db.rollback()
        return 0
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Holdings → Target Weights 마이그레이션 시작...")
    processed = migrate_holdings_to_target_weights()
    if processed > 0:
        print(f"\n✅ {processed}개 포트폴리오에 목표 비중이 추가되었습니다!")
        print("📱 이제 백테스팅 페이지에서 모든 포트폴리오를 확인할 수 있습니다.")
        print("🌐 Streamlit 앱: http://localhost:7700")
    else:
        print("\n⚠️ 처리된 포트폴리오가 없습니다.")