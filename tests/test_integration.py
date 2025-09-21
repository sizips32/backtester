"""
통합 테스트 모듈
시스템 컴포넌트 간 상호작용 및 End-to-End 플로우 테스트
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.data_service import DataService
from utils.validators import DataValidator
from utils.database import get_db
from repository import portfolio_repo, target_weights_repo, holdings_repo
from config.app_config import get_config
import backtesting

class TestDataServiceIntegration:
    """데이터 서비스 통합 테스트"""

    @pytest.fixture
    def data_service(self):
        return DataService()

    @pytest.fixture
    def sample_tickers(self):
        return ['AAPL', 'GOOGL', 'MSFT', '005930']  # US + Korean stock

    def test_multi_stock_data_fetching(self, data_service, sample_tickers):
        """다중 종목 데이터 가져오기 통합 테스트"""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        # Mock 데이터로 테스트 (실제 API 호출 없이)
        with patch.object(data_service, 'fetch_single_stock') as mock_fetch:
            # Mock 반환 데이터
            mock_data = pd.DataFrame({
                'Close': np.random.randn(20).cumsum() + 100
            }, index=pd.date_range(start_date, periods=20))
            mock_fetch.return_value = mock_data

            results = data_service.fetch_multiple_stocks(
                sample_tickers, start_date, end_date
            )

            assert len(results) <= len(sample_tickers)  # 일부는 실패할 수 있음
            assert mock_fetch.call_count == len(sample_tickers)

    def test_data_caching_mechanism(self, data_service):
        """데이터 캐싱 메커니즘 테스트"""
        ticker = 'TEST'
        start_date = datetime.now() - timedelta(days=10)
        end_date = datetime.now()

        with patch.object(data_service, '_fetch_from_source') as mock_source:
            mock_data = pd.DataFrame({'Close': [100, 101, 102]})
            mock_source.return_value = mock_data

            # 첫 번째 호출
            result1 = data_service.fetch_single_stock(ticker, start_date, end_date)

            # 두 번째 호출 (캐시에서 가져와야 함)
            result2 = data_service.fetch_single_stock(ticker, start_date, end_date)

            # 실제 소스는 한 번만 호출되어야 함
            assert mock_source.call_count == 1
            pd.testing.assert_frame_equal(result1, result2)

class TestPortfolioWorkflow:
    """포트폴리오 워크플로우 통합 테스트"""

    @pytest.fixture
    def db_session(self):
        """테스트용 DB 세션"""
        db = next(get_db())
        yield db
        db.close()

    @pytest.fixture
    def sample_portfolio_data(self):
        return {
            'name': '테스트 포트폴리오',
            'description': '통합 테스트용 포트폴리오',
            'assets': ['AAPL', 'GOOGL', 'MSFT'],
            'weights': [0.4, 0.3, 0.3]
        }

    def test_complete_portfolio_creation_workflow(self, db_session, sample_portfolio_data):
        """완전한 포트폴리오 생성 워크플로우 테스트"""
        # 1. 포트폴리오 생성
        portfolio = portfolio_repo.create_portfolio(
            db_session,
            sample_portfolio_data['name'],
            sample_portfolio_data['description']
        )
        assert portfolio.id is not None

        # 2. 목표 비중 설정
        weights = dict(zip(sample_portfolio_data['assets'], sample_portfolio_data['weights']))
        target_weights_repo.set_portfolio_target_weights(db_session, portfolio.id, weights)

        # 3. 목표 비중 조회 및 검증
        retrieved_weights = target_weights_repo.get_portfolio_target_weights(db_session, portfolio.id)
        assert len(retrieved_weights) == len(weights)
        assert abs(sum(retrieved_weights.values()) - 1.0) < 0.01

        # 4. 포트폴리오 삭제
        portfolio_repo.delete_portfolio(db_session, portfolio.id)
        deleted_portfolio = portfolio_repo.get_portfolio_by_id(db_session, portfolio.id)
        assert deleted_portfolio is None

    def test_portfolio_holdings_integration(self, db_session):
        """포트폴리오 보유 종목 통합 테스트"""
        # 포트폴리오 생성
        portfolio = portfolio_repo.create_portfolio(db_session, '홀딩스 테스트', '')

        # 보유 종목 추가
        holdings_data = [
            {'symbol': 'AAPL', 'quantity': 10, 'purchase_price': 150.0},
            {'symbol': 'GOOGL', 'quantity': 5, 'purchase_price': 2500.0}
        ]

        for holding in holdings_data:
            holdings_repo.add_holding(
                db_session, portfolio.id, holding['symbol'],
                holding['quantity'], holding['purchase_price'],
                datetime.now(), 'US_STOCK'
            )

        # 보유 종목 조회
        holdings = holdings_repo.get_portfolio_holdings(db_session, portfolio.id)
        assert len(holdings) == 2

        # 총 투자금액 검증
        total_investment = sum(h.quantity * h.purchase_price for h in holdings)
        expected_total = 10 * 150.0 + 5 * 2500.0
        assert abs(total_investment - expected_total) < 0.01

        # 정리
        portfolio_repo.delete_portfolio(db_session, portfolio.id)

class TestBacktestingIntegration:
    """백테스팅 통합 테스트"""

    @pytest.fixture
    def sample_price_data(self):
        """샘플 가격 데이터"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        data = {}

        for ticker in ['AAPL', 'GOOGL', 'MSFT']:
            # 랜덤 워크로 가격 시뮬레이션
            returns = np.random.normal(0.001, 0.02, 100)
            prices = 100 * np.exp(np.cumsum(returns))
            data[ticker] = pd.Series(prices, index=dates)

        return pd.DataFrame(data)

    def test_portfolio_backtest_calculation(self, sample_price_data):
        """포트폴리오 백테스트 계산 통합 테스트"""
        weights = {'AAPL': 0.4, 'GOOGL': 0.3, 'MSFT': 0.3}

        # 포트폴리오 가치 계산
        portfolio_value = backtesting.calculate_portfolio_value(sample_price_data, weights)

        assert len(portfolio_value) == len(sample_price_data)
        assert portfolio_value.iloc[0] == 1.0  # 초기값은 1
        assert not portfolio_value.isna().any()  # NaN 없어야 함

    def test_risk_metrics_calculation(self, sample_price_data):
        """리스크 지표 계산 통합 테스트"""
        weights = {'AAPL': 0.4, 'GOOGL': 0.3, 'MSFT': 0.3}
        portfolio_value = backtesting.calculate_portfolio_value(sample_price_data, weights)
        returns = portfolio_value.pct_change().dropna()

        metrics = backtesting.calculate_metrics(returns)

        # 필수 지표들이 계산되었는지 확인
        required_metrics = ['annual_return', 'annual_vol', 'sharpe_ratio', 'max_drawdown']
        for metric in required_metrics:
            assert metric in metrics
            assert not pd.isna(metrics[metric])

class TestDataValidationIntegration:
    """데이터 검증 통합 테스트"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    def test_portfolio_weights_validation_workflow(self, validator):
        """포트폴리오 가중치 검증 워크플로우 테스트"""
        # 유효한 가중치
        valid_weights = {'AAPL': 0.4, 'GOOGL': 0.3, 'MSFT': 0.3}
        is_valid, errors = validator.validate_portfolio_weights(valid_weights)
        assert is_valid
        assert len(errors) == 0

        # 무효한 가중치 (합계가 1이 아님)
        invalid_weights = {'AAPL': 0.5, 'GOOGL': 0.3, 'MSFT': 0.3}
        is_valid, errors = validator.validate_portfolio_weights(invalid_weights)
        assert not is_valid
        assert len(errors) > 0

    def test_ticker_validation_integration(self, validator):
        """티커 검증 통합 테스트"""
        # 다양한 형태의 티커 테스트
        test_cases = [
            ('AAPL', True),      # US 주식
            ('005930', True),    # 한국 주식
            ('005930.KS', True), # 한국 주식 (KS)
            ('INVALID_TICKER_NAME', False),  # 무효한 티커
            ('', False),         # 빈 문자열
            (None, False)        # None
        ]

        for ticker, expected in test_cases:
            result = validator.validate_ticker(ticker)
            assert result == expected, f"Ticker {ticker} validation failed"

class TestSystemIntegration:
    """시스템 전체 통합 테스트"""

    @patch('services.data_service.DataService.fetch_single_stock')
    def test_end_to_end_portfolio_analysis(self, mock_fetch, db_session):
        """End-to-End 포트폴리오 분석 테스트"""
        # Mock 데이터 설정
        mock_data = pd.DataFrame({
            'Close': np.random.randn(50).cumsum() + 100
        }, index=pd.date_range('2023-01-01', periods=50))
        mock_fetch.return_value = mock_data

        # 1. 포트폴리오 생성
        portfolio = portfolio_repo.create_portfolio(db_session, 'E2E 테스트', '')

        # 2. 목표 비중 설정
        weights = {'AAPL': 0.5, 'GOOGL': 0.5}
        target_weights_repo.set_portfolio_target_weights(db_session, portfolio.id, weights)

        # 3. 데이터 가져오기
        data_service = DataService()
        start_date = datetime.now() - timedelta(days=60)
        end_date = datetime.now()

        portfolio_data = {}
        for ticker in weights.keys():
            data = data_service.fetch_single_stock(ticker, start_date, end_date)
            if data is not None:
                portfolio_data[ticker] = data

        # 4. 백테스트 실행
        if len(portfolio_data) >= 2:
            price_df = pd.DataFrame(portfolio_data)
            portfolio_value = backtesting.calculate_portfolio_value(price_df, weights)
            returns = portfolio_value.pct_change().dropna()
            metrics = backtesting.calculate_metrics(returns)

            # 결과 검증
            assert len(portfolio_value) > 0
            assert 'sharpe_ratio' in metrics
            assert not pd.isna(metrics['sharpe_ratio'])

        # 5. 정리
        portfolio_repo.delete_portfolio(db_session, portfolio.id)

    def test_error_handling_integration(self):
        """에러 처리 통합 테스트"""
        data_service = DataService()

        # 존재하지 않는 티커로 테스트
        with patch.object(data_service, '_fetch_from_source', side_effect=Exception("Network error")):
            result = data_service.fetch_single_stock(
                'INVALID',
                datetime.now() - timedelta(days=30),
                datetime.now()
            )
            # 에러가 발생해도 None을 반환해야 함 (예외 발생하지 않음)
            assert result is None

if __name__ == "__main__":
    # 개별 테스트 실행을 위한 코드
    pytest.main([__file__, "-v"])