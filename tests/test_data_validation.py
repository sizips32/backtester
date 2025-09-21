"""
데이터 검증 강화 테스트 모듈
포트폴리오 데이터의 품질과 유효성을 엄격하게 검증하는 테스트
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

from utils.validators import DataValidator, validate_ticker
from utils.error_handler import ValidationError, InsufficientDataError

class TestEnhancedDataValidation:
    """강화된 데이터 검증 테스트"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    @pytest.fixture
    def sample_price_data(self):
        """샘플 가격 데이터"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        return pd.DataFrame({
            'AAPL': np.random.lognormal(0, 0.2, 100) * 150,
            'GOOGL': np.random.lognormal(0, 0.2, 100) * 2500,
            'MSFT': np.random.lognormal(0, 0.2, 100) * 300
        }, index=dates)

    def test_portfolio_weights_comprehensive_validation(self, validator):
        """포트폴리오 가중치 종합 검증 테스트"""
        # 정상 케이스
        valid_weights = {'AAPL': 0.4, 'GOOGL': 0.3, 'MSFT': 0.3}
        is_valid, errors = validator.validate_portfolio_weights(valid_weights)
        assert is_valid
        assert len(errors) == 0

        # 가중치 합계 오류 (1.1)
        invalid_sum_weights = {'AAPL': 0.5, 'GOOGL': 0.3, 'MSFT': 0.3}
        is_valid, errors = validator.validate_portfolio_weights(invalid_sum_weights)
        assert not is_valid
        assert any('합계' in error for error in errors)

        # 음수 가중치
        negative_weights = {'AAPL': 0.5, 'GOOGL': -0.1, 'MSFT': 0.6}
        is_valid, errors = validator.validate_portfolio_weights(negative_weights)
        assert not is_valid
        assert any('음수' in error for error in errors)

        # 빈 포트폴리오
        empty_weights = {}
        is_valid, errors = validator.validate_portfolio_weights(empty_weights)
        assert not is_valid
        assert any('비어있습니다' in error for error in errors)

        # 단일 자산 (100%)
        single_asset = {'AAPL': 1.0}
        is_valid, errors = validator.validate_portfolio_weights(single_asset)
        assert is_valid  # 단일 자산도 허용

        # 허용 오차 테스트 (0.999)
        near_one_weights = {'AAPL': 0.333, 'GOOGL': 0.333, 'MSFT': 0.333}
        is_valid, errors = validator.validate_portfolio_weights(near_one_weights)
        assert is_valid  # 허용 오차 내

    def test_ticker_validation_edge_cases(self):
        """티커 검증 엣지 케이스 테스트"""
        with patch('services.data_service.data_service.fetch_single_stock') as mock_fetch:
            # 정상 데이터 반환
            mock_data = pd.DataFrame({'Close': [100, 101, 102]})
            mock_fetch.return_value = mock_data

            test_cases = [
                # (ticker, expected_valid, description)
                ('AAPL', True, 'US stock'),
                ('005930', True, 'Korean stock number'),
                ('005930.KS', True, 'Korean stock with KS'),
                ('005930.KQ', True, 'Korean stock with KQ'),
                ('', False, 'Empty string'),
                (None, False, 'None value'),
                ('INVALID_TICKER_123456789', True, 'Long ticker (mocked)'),
                ('12345', False, 'Invalid Korean stock'),
                ('123456789', False, 'Too long number')
            ]

            for ticker, expected, description in test_cases:
                if ticker in [None, ''] or len(str(ticker)) > 10:
                    # 이런 경우는 실제로 검증 실패해야 함
                    mock_fetch.return_value = None

                result, error = validate_ticker(ticker)
                assert result == expected, f"Failed for {description}: {ticker}"

    def test_data_quality_validation(self, validator, sample_price_data):
        """데이터 품질 검증 테스트"""
        # 정상 데이터
        is_valid, issues = validator.validate_data_quality(sample_price_data)
        assert is_valid

        # 결측치가 많은 데이터
        corrupted_data = sample_price_data.copy()
        corrupted_data.iloc[::2] = np.nan  # 50% 결측치
        is_valid, issues = validator.validate_data_quality(corrupted_data)
        assert not is_valid
        assert any('결측치' in issue for issue in issues)

        # 비정상적인 가격 변동 (outliers)
        outlier_data = sample_price_data.copy()
        outlier_data.iloc[50, 0] = outlier_data.iloc[49, 0] * 10  # 1000% 증가
        is_valid, issues = validator.validate_data_quality(outlier_data)
        assert not is_valid
        assert any('비정상적인' in issue for issue in issues)

        # 빈 데이터
        empty_data = pd.DataFrame()
        is_valid, issues = validator.validate_data_quality(empty_data)
        assert not is_valid

    def test_date_range_validation(self, validator):
        """날짜 범위 검증 테스트"""
        today = datetime.now().date()

        # 정상 날짜 범위
        start_date = today - timedelta(days=365)
        end_date = today - timedelta(days=1)
        is_valid, error = validator.validate_date_range(start_date, end_date)
        assert is_valid

        # 역순 날짜
        is_valid, error = validator.validate_date_range(end_date, start_date)
        assert not is_valid
        assert '시작일' in error

        # 미래 날짜
        future_date = today + timedelta(days=30)
        is_valid, error = validator.validate_date_range(start_date, future_date)
        assert not is_valid
        assert '미래' in error

        # 너무 짧은 기간
        short_end = start_date + timedelta(days=5)
        is_valid, error = validator.validate_date_range(start_date, short_end)
        assert not is_valid
        assert '기간이 너무 짧습니다' in error

        # 너무 긴 기간
        very_old_start = today - timedelta(days=10000)
        is_valid, error = validator.validate_date_range(very_old_start, end_date)
        assert not is_valid
        assert '기간이 너무 깁니다' in error

    def test_portfolio_composition_validation(self, validator):
        """포트폴리오 구성 검증 테스트"""
        # 정상 구성
        composition = {
            'US_STOCK': ['AAPL', 'GOOGL', 'MSFT'],
            'KR_STOCK': ['005930', '000660'],
            'weights': [0.3, 0.2, 0.2, 0.15, 0.15]
        }
        is_valid, issues = validator.validate_portfolio_composition(composition)
        assert is_valid

        # 자산과 가중치 개수 불일치
        mismatched_composition = {
            'US_STOCK': ['AAPL', 'GOOGL'],
            'weights': [0.5, 0.3, 0.2]  # 3개 가중치, 2개 자산
        }
        is_valid, issues = validator.validate_portfolio_composition(mismatched_composition)
        assert not is_valid

        # 과도한 집중 (단일 자산에 80% 이상)
        concentrated_composition = {
            'US_STOCK': ['AAPL', 'GOOGL'],
            'weights': [0.9, 0.1]
        }
        is_valid, issues = validator.validate_portfolio_composition(concentrated_composition)
        assert not is_valid
        assert any('집중' in issue for issue in issues)

    def test_risk_parameter_validation(self, validator):
        """리스크 파라미터 검증 테스트"""
        # 정상 파라미터
        params = {
            'risk_free_rate': 0.02,
            'confidence_level': 0.95,
            'volatility_window': 252,
            'max_weight': 0.4
        }
        is_valid, issues = validator.validate_risk_parameters(params)
        assert is_valid

        # 비정상 파라미터들
        invalid_params = [
            ({'risk_free_rate': -0.1}, '음수 무위험 수익률'),
            ({'confidence_level': 1.1}, '신뢰수준 범위 초과'),
            ({'volatility_window': 0}, '변동성 윈도우 0'),
            ({'max_weight': 1.5}, '최대 가중치 초과')
        ]

        for invalid_param, description in invalid_params:
            test_params = params.copy()
            test_params.update(invalid_param)
            is_valid, issues = validator.validate_risk_parameters(test_params)
            assert not is_valid, f"Should fail for {description}"

    def test_performance_metrics_validation(self, validator):
        """성과 지표 검증 테스트"""
        # 정상 성과 지표
        metrics = {
            'total_return': 0.15,
            'annual_return': 0.12,
            'volatility': 0.18,
            'sharpe_ratio': 0.67,
            'max_drawdown': -0.08,
            'calmar_ratio': 1.5
        }
        is_valid, issues = validator.validate_performance_metrics(metrics)
        assert is_valid

        # 비정상적인 지표들
        extreme_metrics = {
            'total_return': 10.0,  # 1000% 수익률
            'volatility': -0.1,    # 음수 변동성
            'sharpe_ratio': float('inf'),  # 무한대
            'max_drawdown': 0.1    # 양수 낙폭
        }
        is_valid, issues = validator.validate_performance_metrics(extreme_metrics)
        assert not is_valid
        assert len(issues) >= 3  # 여러 문제 동시 발견

    def test_data_completeness_validation(self, validator, sample_price_data):
        """데이터 완정성 검증 테스트"""
        # 완전한 데이터
        completeness = validator.check_data_completeness(sample_price_data)
        assert completeness['overall_score'] > 0.9

        # 불완전한 데이터
        incomplete_data = sample_price_data.copy()
        # 특정 기간 데이터 제거
        incomplete_data.iloc[30:40] = np.nan
        # 특정 종목 데이터 부분 제거
        incomplete_data.loc[:, 'AAPL'].iloc[60:70] = np.nan

        completeness = validator.check_data_completeness(incomplete_data)
        assert completeness['overall_score'] < 0.9
        assert 'gaps' in completeness
        assert len(completeness['gaps']) > 0

    def test_correlation_validation(self, validator, sample_price_data):
        """상관관계 검증 테스트"""
        returns = sample_price_data.pct_change().dropna()

        # 정상 상관관계
        correlation_issues = validator.validate_correlations(returns)
        assert isinstance(correlation_issues, list)

        # 완전 상관관계 데이터 생성
        perfect_corr_data = sample_price_data.copy()
        perfect_corr_data['DUPLICATE'] = perfect_corr_data['AAPL']  # 완전 복제
        perfect_returns = perfect_corr_data.pct_change().dropna()

        correlation_issues = validator.validate_correlations(perfect_returns)
        assert len(correlation_issues) > 0
        assert any('완전상관' in issue or '동일' in issue for issue in correlation_issues)

    def test_business_rule_validation(self, validator):
        """비즈니스 규칙 검증 테스트"""
        # 정상 거래 데이터
        trade_data = {
            'symbol': 'AAPL',
            'quantity': 100,
            'price': 150.0,
            'trade_date': datetime.now() - timedelta(days=1),
            'trade_type': 'BUY'
        }
        is_valid, issues = validator.validate_trade_data(trade_data)
        assert is_valid

        # 비정상 거래 데이터들
        invalid_trades = [
            ({'quantity': 0}, '수량 0'),
            ({'price': -100}, '음수 가격'),
            ({'trade_date': datetime.now() + timedelta(days=1)}, '미래 거래일'),
            ({'trade_type': 'INVALID'}, '잘못된 거래 유형')
        ]

        for invalid_data, description in invalid_trades:
            test_trade = trade_data.copy()
            test_trade.update(invalid_data)
            is_valid, issues = validator.validate_trade_data(test_trade)
            assert not is_valid, f"Should fail for {description}"

class TestDataValidationIntegration:
    """데이터 검증 통합 테스트"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    def test_end_to_end_portfolio_validation(self, validator):
        """End-to-End 포트폴리오 검증 테스트"""
        # 완전한 포트폴리오 데이터 구성
        portfolio_data = {
            'name': '통합 검증 포트폴리오',
            'assets': ['AAPL', 'GOOGL', 'MSFT', '005930'],
            'weights': [0.3, 0.25, 0.25, 0.2],
            'start_date': datetime(2023, 1, 1).date(),
            'end_date': datetime(2023, 12, 31).date(),
            'risk_parameters': {
                'risk_free_rate': 0.02,
                'confidence_level': 0.95,
                'max_weight': 0.4
            }
        }

        # 전체 검증 실행
        validation_result = validator.validate_complete_portfolio(portfolio_data)

        assert validation_result['is_valid']
        assert validation_result['validation_score'] > 0.8
        assert len(validation_result['critical_issues']) == 0

    def test_validation_with_real_market_conditions(self, validator):
        """실제 시장 조건 검증 테스트"""
        # 실제 시장 시나리오: 2020년 코로나 크래시
        crash_scenario = {
            'portfolio_returns': [-0.35, -0.20, -0.15, 0.10, 0.25],  # 급락 후 회복
            'market_volatility': 0.45,  # 높은 변동성
            'correlation_spike': True   # 상관관계 급증
        }

        stress_test_result = validator.stress_test_validation(crash_scenario)
        assert 'risk_warnings' in stress_test_result
        assert 'diversification_breakdown' in stress_test_result

    def test_data_validation_performance_under_load(self, validator):
        """부하 상황에서 데이터 검증 성능 테스트"""
        import time

        # 대량 포트폴리오 데이터
        large_portfolio = {
            'assets': [f'STOCK{i:04d}' for i in range(500)],
            'weights': [1/500] * 500
        }

        start_time = time.time()
        is_valid, errors = validator.validate_portfolio_weights(
            dict(zip(large_portfolio['assets'], large_portfolio['weights']))
        )
        validation_time = time.time() - start_time

        # 성능 기준: 500개 자산을 1초 내에 검증
        assert validation_time < 1.0
        assert is_valid

if __name__ == "__main__":
    # 데이터 검증 테스트 실행
    pytest.main([__file__, "-v"])