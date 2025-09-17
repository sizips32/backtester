"""
포트폴리오 성과 이력 데이터베이스 CRUD 작업
"""
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert
from utils.database import PortfolioPerformance

def get_portfolio_performance(db: Session, portfolio_id: int, start_date: str = None, end_date: str = None):
    query = db.query(PortfolioPerformance).filter(PortfolioPerformance.portfolio_id == portfolio_id)
    if start_date:
        query = query.filter(PortfolioPerformance.date >= start_date)
    if end_date:
        query = query.filter(PortfolioPerformance.date <= end_date)
    return query.order_by(PortfolioPerformance.date).all()

def record_portfolio_performance(db: Session, portfolio_id: int, date: str, total_value: float, daily_return: float = None):
    # SQLite의 INSERT OR REPLACE 동작을 에뮬레이트
    stmt = insert(PortfolioPerformance).values(
        portfolio_id=portfolio_id, 
        date=date, 
        total_value=total_value, 
        daily_return=daily_return
    )
    
    # ON CONFLICT DO UPDATE
    # 고유 제약 조건(portfolio_id, date) 충돌 시, 지정된 열을 업데이트
    do_update_stmt = stmt.on_conflict_do_update(
        index_elements=['portfolio_id', 'date'],
        set_=dict(total_value=stmt.excluded.total_value, daily_return=stmt.excluded.daily_return)
    )
    
    db.execute(do_update_stmt)
    db.commit()
    return True
