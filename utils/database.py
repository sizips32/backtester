"""
SQLAlchemy 데이터베이스 설정 및 모델 정의
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func
from config.app_config import get_database_config

# 데이터베이스 설정 가져오기
db_config = get_database_config()
DATABASE_URL = f"sqlite:///{db_config.db_path}"

# 데이터베이스 디렉토리 확인 및 생성
os.makedirs(os.path.dirname(db_config.db_path), exist_ok=True)

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}, # Streamlit은 다중 스레드에서 실행될 수 있음
    echo=False # SQL 로그 비활성화 (디버깅 시 True로 변경)
)

# 세션 로컬 클래스 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모델 클래스의 베이스 클래스
Base = declarative_base()

# --- SQLAlchemy 모델 정의 ---

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계 설정
    holdings = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")
    performance = relationship("PortfolioPerformance", back_populates="portfolio", cascade="all, delete-orphan")
    target_weights = relationship("PortfolioTargetWeight", back_populates="portfolio", cascade="all, delete-orphan")

class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String, nullable=False)
    quantity = Column(Float, nullable=False, default=0)
    purchase_price = Column(Float, nullable=False, default=0)
    purchase_date = Column(String) # 날짜를 문자열로 저장 (YYYY-MM-DD)
    asset_type = Column(String, default='Stock')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (UniqueConstraint('portfolio_id', 'symbol', name='_portfolio_symbol_uc'),)
    
    # 관계 설정
    portfolio = relationship("Portfolio", back_populates="holdings")

class PortfolioPerformance(Base):
    __tablename__ = "portfolio_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    date = Column(String, nullable=False) # 날짜를 문자열로 저장 (YYYY-MM-DD)
    total_value = Column(Float, nullable=False)
    daily_return = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint('portfolio_id', 'date', name='_portfolio_date_uc'),)
    
    # 관계 설정
    portfolio = relationship("Portfolio", back_populates="performance")

class PortfolioTargetWeight(Base):
    __tablename__ = "portfolio_target_weights"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String, nullable=False)
    weight = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (UniqueConstraint('portfolio_id', 'symbol', name='_portfolio_target_weight_uc'),)
    
    # 관계 설정
    portfolio = relationship("Portfolio", back_populates="target_weights")


def init_db():
    """데이터베이스의 모든 테이블을 생성합니다."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """데이터베이스 세션을 생성하고 제공하는 제너레이터"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 애플리케이션 시작 시 DB 초기화
init_db()
