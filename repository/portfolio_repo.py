"""
포트폴리오 데이터베이스 CRUD 작업
"""
from sqlalchemy.orm import Session
from utils.database import Portfolio

def get_portfolio_by_id(db: Session, portfolio_id: int):
    return db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()

def get_portfolio_by_name(db: Session, name: str):
    return db.query(Portfolio).filter(Portfolio.name == name).first()

def get_all_portfolios(db: Session):
    return db.query(Portfolio).order_by(Portfolio.name).all()

def create_portfolio(db: Session, name: str, description: str = ""):
    db_portfolio = Portfolio(name=name, description=description)
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def update_portfolio(db: Session, portfolio_id: int, name: str, description: str):
    db_portfolio = get_portfolio_by_id(db, portfolio_id)
    if db_portfolio:
        db_portfolio.name = name
        db_portfolio.description = description
        db.commit()
        db.refresh(db_portfolio)
        return db_portfolio
    return None

def delete_portfolio(db: Session, portfolio_id: int):
    db_portfolio = get_portfolio_by_id(db, portfolio_id)
    if db_portfolio:
        db.delete(db_portfolio)
        db.commit()
        return True
    return False

def upsert_portfolio(db: Session, name: str, description: str = ""):
    db_portfolio = get_portfolio_by_name(db, name)
    if db_portfolio:
        return db_portfolio
    return create_portfolio(db, name, description)
