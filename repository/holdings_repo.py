"""
포트폴리오 보유 종목 데이터베이스 CRUD 작업
"""
from sqlalchemy.orm import Session
from utils.database import PortfolioHolding

def get_portfolio_holdings(db: Session, portfolio_id: int):
    return db.query(PortfolioHolding).filter(PortfolioHolding.portfolio_id == portfolio_id).order_by(PortfolioHolding.symbol).all()

def add_holding_to_portfolio(db: Session, portfolio_id: int, symbol: str, quantity: float, purchase_price: float, purchase_date: str, asset_type: str):
    # 중복 체크
    db_holding = db.query(PortfolioHolding).filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
    
    if db_holding:
        # 이미 존재하는 경우, 수량과 평균 매수가 업데이트 (가중 평균)
        new_quantity = db_holding.quantity + quantity
        new_purchase_price = ((db_holding.purchase_price * db_holding.quantity) + (purchase_price * quantity)) / new_quantity
        db_holding.quantity = new_quantity
        db_holding.purchase_price = new_purchase_price
    else:
        # 새로 추가
        db_holding = PortfolioHolding(
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity=quantity,
            purchase_price=purchase_price,
            purchase_date=purchase_date,
            asset_type=asset_type
        )
        db.add(db_holding)
        
    db.commit()
    db.refresh(db_holding)
    return db_holding

def update_holding(db: Session, holding_id: int, quantity: float, purchase_price: float, purchase_date: str, asset_type: str):
    db_holding = db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()
    if db_holding:
        db_holding.quantity = quantity
        db_holding.purchase_price = purchase_price
        db_holding.purchase_date = purchase_date
        db_holding.asset_type = asset_type
        db.commit()
        db.refresh(db_holding)
        return db_holding
    return None

def delete_holding(db: Session, holding_id: int):
    db_holding = db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()
    if db_holding:
        db.delete(db_holding)
        db.commit()
        return True
    return False
