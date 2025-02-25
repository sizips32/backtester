"""커스텀 예외 클래스"""

class PortfolioError(Exception):
    """포트폴리오 관련 기본 예외"""
    pass

class DataValidationError(PortfolioError):
    """데이터 검증 실패 예외"""
    pass

class MarketDataError(PortfolioError):
    """시장 데이터 관련 예외"""
    pass

class OptimizationError(PortfolioError):
    """최적화 관련 예외"""
    pass

class BacktestError(PortfolioError):
    """백테스트 관련 예외"""
    pass

class RebalancingError(PortfolioError):
    """리밸런싱 실패 예외"""
    pass 
