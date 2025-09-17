"""
포트폴리오 목표 비중 데이터베이스 CRUD 작업
"""
from sqlalchemy.orm import Session
from utils.database import PortfolioTargetWeight

def get_portfolio_target_weights(db: Session, portfolio_id: int):
    weights = db.query(PortfolioTargetWeight).filter(PortfolioTargetWeight.portfolio_id == portfolio_id).all()
    return {item.symbol: item.weight for item in weights}

def set_portfolio_target_weights(db: Session, portfolio_id: int, weights: dict):
    # 기존 비중 삭제
    db.query(PortfolioTargetWeight).filter(PortfolioTargetWeight.portfolio_id == portfolio_id).delete()
    
    # 새 비중 추가
    for symbol, weight in weights.items():
        db_weight = PortfolioTargetWeight(portfolio_id=portfolio_id, symbol=symbol, weight=weight)
        db.add(db_weight)
    
    db.commit()
    return True

def delete_portfolio_target_weights(db: Session, portfolio_id: int):
    num_deleted = db.query(PortfolioTargetWeight).filter(PortfolioTargetWeight.portfolio_id == portfolio_id).delete()
    db.commit()
    return num_deleted > 0
