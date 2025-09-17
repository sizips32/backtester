import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils.database import Base, Portfolio
from repository import portfolio_repo, holdings_repo

# --- 테스트용 데이터베이스 설정 ---
# 메모리 내 SQLite 데이터베이스 사용
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Pytest Fixture --- 
@pytest.fixture(scope="function")
def db_session():
    """테스트용 DB 세션 فixture. 테스트마다 테이블을 생성하고 삭제합니다."""
    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # 모든 테이블 삭제
        Base.metadata.drop_all(bind=engine)

# --- 테스트 케이스 ---

def test_create_and_get_portfolio(db_session):
    """포트폴리오 생성 및 조회 테스트"""
    # 1. 포트폴리오 생성
    portfolio_name = "Test Portfolio"
    portfolio_desc = "This is a test."
    created = portfolio_repo.create_portfolio(db_session, name=portfolio_name, description=portfolio_desc)
    
    assert created is not None
    assert created.name == portfolio_name
    assert created.description == portfolio_desc

    # 2. ID로 조회
    retrieved_by_id = portfolio_repo.get_portfolio_by_id(db_session, created.id)
    assert retrieved_by_id is not None
    assert retrieved_by_id.id == created.id
    assert retrieved_by_id.name == portfolio_name

    # 3. 이름으로 조회
    retrieved_by_name = portfolio_repo.get_portfolio_by_name(db_session, portfolio_name)
    assert retrieved_by_name is not None
    assert retrieved_by_name.id == created.id

    # 4. 전체 목록 조회
    all_portfolios = portfolio_repo.get_all_portfolios(db_session)
    assert len(all_portfolios) == 1
    assert all_portfolios[0].name == portfolio_name

def test_add_and_get_holding(db_session):
    """보유 종목 추가 및 조회 테스트"""
    # 전제 조건: 포트폴리오 생성
    portfolio = portfolio_repo.create_portfolio(db_session, name="Holding Test")
    
    # 1. 보유 종목 추가
    holding = holdings_repo.add_holding_to_portfolio(
        db=db_session,
        portfolio_id=portfolio.id,
        symbol="AAPL",
        quantity=10,
        purchase_price=150.0,
        purchase_date="2023-01-10",
        asset_type="Stock"
    )
    assert holding is not None
    assert holding.symbol == "AAPL"
    assert holding.quantity == 10

    # 2. 보유 종목 조회
    holdings = holdings_repo.get_portfolio_holdings(db_session, portfolio.id)
    assert len(holdings) == 1
    assert holdings[0].symbol == "AAPL"
    assert holdings[0].quantity == 10

def test_delete_portfolio(db_session):
    """포트폴리오 삭제 테스트"""
    # 1. 포트폴리오 및 종목 생성
    portfolio = portfolio_repo.create_portfolio(db_session, name="ToDelete")
    holdings_repo.add_holding_to_portfolio(db_session, portfolio.id, "MSFT", 5, 300.0, "2023-02-01", "Stock")

    # 2. 삭제 전 확인
    assert portfolio_repo.get_portfolio_by_id(db_session, portfolio.id) is not None
    assert len(holdings_repo.get_portfolio_holdings(db_session, portfolio.id)) == 1

    # 3. 포트폴리오 삭제 (cascade delete 확인)
    deleted = portfolio_repo.delete_portfolio(db_session, portfolio.id)
    assert deleted is True

    # 4. 삭제 후 확인
    assert portfolio_repo.get_portfolio_by_id(db_session, portfolio.id) is None
    # cascade 설정으로 holdings도 삭제되어야 함
    assert len(holdings_repo.get_portfolio_holdings(db_session, portfolio.id)) == 0
