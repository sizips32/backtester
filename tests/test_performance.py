"""
성능 테스트 모듈
시스템 성능, 메모리 사용량, 실행 시간 등을 측정하는 테스트
"""

import pytest
import pandas as pd
import numpy as np
import time
import psutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import sys
import os
from concurrent.futures import ThreadPoolExecutor

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.data_service import DataService
from utils.performance_monitor import performance_monitor, monitor_performance
import backtesting
from utils.validators import DataValidator

class TestDataServicePerformance:
    """데이터 서비스 성능 테스트"""

    @pytest.fixture
    def data_service(self):
        return DataService()

    @pytest.fixture
    def large_ticker_list(self):
        """큰 티커 리스트 생성"""
        us_stocks = [f"STOCK{i:03d}" for i in range(50)]
        kr_stocks = [f"{100000 + i:06d}" for i in range(50)]
        return us_stocks + kr_stocks

    def test_single_stock_fetch_performance(self, data_service):
        """단일 주식 데이터 가져오기 성능 테스트"""
        ticker = 'AAPL'
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()

        # Mock 데이터로 성능 측정
        with patch.object(data_service, '_fetch_from_source') as mock_fetch:
            mock_data = pd.DataFrame({
                'Close': np.random.randn(365).cumsum() + 100
            }, index=pd.date_range(start_date, periods=365))
            mock_fetch.return_value = mock_data

            start_time = time.time()
            memory_before = psutil.Process().memory_info().rss / 1024 / 1024

            result = data_service.fetch_single_stock(ticker, start_date, end_date)

            end_time = time.time()
            memory_after = psutil.Process().memory_info().rss / 1024 / 1024

            execution_time = end_time - start_time
            memory_used = memory_after - memory_before

            # 성능 임계값 검증
            assert execution_time < 1.0  # 1초 이내
            assert memory_used < 50  # 50MB 이내
            assert result is not None

    def test_multiple_stock_fetch_performance(self, data_service):
        """다중 주식 데이터 가져오기 성능 테스트"""
        tickers = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        with patch.object(data_service, 'fetch_single_stock') as mock_fetch:
            mock_data = pd.DataFrame({
                'Close': np.random.randn(30).cumsum() + 100
            })
            mock_fetch.return_value = mock_data

            start_time = time.time()

            results = data_service.fetch_multiple_stocks(tickers, start_date, end_date)

            end_time = time.time()
            execution_time = end_time - start_time

            # 병렬 처리로 선형 시간보다 빨라야 함
            assert execution_time < len(tickers) * 0.5  # 각 티커당 0.5초보다 빠름
            assert len(results) <= len(tickers)

    def test_cache_performance(self, data_service):
        """캐시 성능 테스트"""
        ticker = 'AAPL'
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        with patch.object(data_service, '_fetch_from_source') as mock_fetch:
            mock_data = pd.DataFrame({'Close': [100, 101, 102]})
            mock_fetch.return_value = mock_data

            # 첫 번째 호출 (캐시 미스)
            start_time = time.time()
            result1 = data_service.fetch_single_stock(ticker, start_date, end_date)
            first_call_time = time.time() - start_time

            # 두 번째 호출 (캐시 히트)
            start_time = time.time()
            result2 = data_service.fetch_single_stock(ticker, start_date, end_date)
            second_call_time = time.time() - start_time

            # 캐시된 호출이 훨씬 빨라야 함
            assert second_call_time < first_call_time * 0.1  # 10배 이상 빠름
            assert mock_fetch.call_count == 1  # 실제 호출은 1번만

class TestBacktestingPerformance:
    """백테스팅 성능 테스트"""

    @pytest.fixture
    def large_portfolio_data(self):
        """대규모 포트폴리오 데이터"""
        dates = pd.date_range('2020-01-01', '2023-12-31', freq='D')
        tickers = [f'STOCK{i:03d}' for i in range(100)]  # 100개 종목

        data = {}
        for ticker in tickers:
            returns = np.random.normal(0.0005, 0.02, len(dates))
            prices = 100 * np.exp(np.cumsum(returns))
            data[ticker] = prices

        return pd.DataFrame(data, index=dates)

    @pytest.fixture
    def equal_weights(self):
        """동일 가중치"""
        tickers = [f'STOCK{i:03d}' for i in range(100)]
        weight = 1.0 / len(tickers)
        return {ticker: weight for ticker in tickers}

    def test_large_portfolio_calculation_performance(self, large_portfolio_data, equal_weights):
        """대규모 포트폴리오 계산 성능 테스트"""
        start_time = time.time()
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024

        portfolio_value = backtesting.calculate_portfolio_value(large_portfolio_data, equal_weights)

        end_time = time.time()
        memory_after = psutil.Process().memory_info().rss / 1024 / 1024

        execution_time = end_time - start_time
        memory_used = memory_after - memory_before

        # 성능 기준 검증
        assert execution_time < 5.0  # 5초 이내
        assert memory_used < 200  # 200MB 이내
        assert len(portfolio_value) == len(large_portfolio_data)

    def test_vectorized_vs_iterative_performance(self, large_portfolio_data, equal_weights):
        """벡터화 vs 반복문 성능 비교"""
        # 벡터화 방식 (현재 구현)
        start_time = time.time()
        vectorized_result = backtesting.calculate_portfolio_value(large_portfolio_data, equal_weights)
        vectorized_time = time.time() - start_time

        # 반복문 방식 (성능 비교용)
        def calculate_portfolio_value_iterative(data, weights):
            portfolio_values = []
            for i in range(len(data)):
                if i == 0:
                    portfolio_values.append(1.0)
                else:
                    daily_return = 0
                    for ticker in weights:
                        if ticker in data.columns:
                            price_change = (data[ticker].iloc[i] - data[ticker].iloc[i-1]) / data[ticker].iloc[i-1]
                            daily_return += weights[ticker] * price_change
                    portfolio_values.append(portfolio_values[-1] * (1 + daily_return))
            return pd.Series(portfolio_values, index=data.index)

        start_time = time.time()
        iterative_result = calculate_portfolio_value_iterative(large_portfolio_data.iloc[:100], equal_weights)
        iterative_time = time.time() - start_time

        # 벡터화 방식이 훨씬 빨라야 함
        speedup_ratio = iterative_time / vectorized_time
        assert speedup_ratio > 10, f"Speedup ratio: {speedup_ratio:.2f}x"

    def test_risk_metrics_calculation_performance(self, large_portfolio_data, equal_weights):
        """리스크 지표 계산 성능 테스트"""
        portfolio_value = backtesting.calculate_portfolio_value(large_portfolio_data, equal_weights)
        returns = portfolio_value.pct_change().dropna()

        start_time = time.time()
        metrics = backtesting.calculate_metrics(returns)
        execution_time = time.time() - start_time

        # 리스크 지표 계산이 빨라야 함
        assert execution_time < 1.0  # 1초 이내
        assert isinstance(metrics, dict)
        assert len(metrics) > 0

class TestMemoryPerformance:
    """메모리 성능 테스트"""

    def test_memory_usage_under_load(self):
        """부하 상황에서 메모리 사용량 테스트"""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # 대량의 데이터 생성 및 처리
        large_datasets = []
        for i in range(10):
            data = pd.DataFrame(
                np.random.randn(1000, 50),
                columns=[f'col_{j}' for j in range(50)]
            )
            large_datasets.append(data)

        peak_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # 데이터 정리
        del large_datasets
        import gc
        gc.collect()

        final_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # 메모리 증가량이 합리적이어야 함
        memory_increase = peak_memory - initial_memory
        memory_freed = peak_memory - final_memory

        assert memory_increase < 500  # 500MB 미만
        assert memory_freed > memory_increase * 0.7  # 70% 이상 해제

    @monitor_performance("memory_optimization_test")
    def test_memory_optimization_decorator(self):
        """메모리 최적화 데코레이터 테스트"""
        # 메모리 집약적 작업
        data = pd.DataFrame(np.random.randn(10000, 100))
        result = data.sum().sum()
        del data
        return result

    def test_performance_monitor_integration(self):
        """성능 모니터 통합 테스트"""
        # 모니터링된 함수 실행
        self.test_memory_optimization_decorator()

        # 메트릭 확인
        stats = performance_monitor.get_function_stats("memory_optimization_test")
        assert stats is not None
        assert stats['call_count'] >= 1
        assert 'avg_execution_time' in stats
        assert 'avg_memory_usage' in stats

class TestConcurrencyPerformance:
    """동시성 성능 테스트"""

    def test_concurrent_data_fetching(self):
        """동시 데이터 가져오기 성능 테스트"""
        data_service = DataService()
        tickers = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN'] * 4  # 20개

        with patch.object(data_service, 'fetch_single_stock') as mock_fetch:
            # Mock 지연 시뮬레이션
            def slow_fetch(*args, **kwargs):
                time.sleep(0.1)  # 100ms 지연
                return pd.DataFrame({'Close': [100, 101, 102]})

            mock_fetch.side_effect = slow_fetch

            # 순차 처리 시간 측정
            start_time = time.time()
            for ticker in tickers[:5]:  # 5개만 테스트
                data_service.fetch_single_stock(ticker, datetime.now(), datetime.now())
            sequential_time = time.time() - start_time

            # 병렬 처리 시간 측정
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(data_service.fetch_single_stock, ticker, datetime.now(), datetime.now())
                    for ticker in tickers[5:10]
                ]
                for future in futures:
                    future.result()
            parallel_time = time.time() - start_time

            # 병렬 처리가 더 빨라야 함
            speedup = sequential_time / parallel_time
            assert speedup > 2.0, f"Parallel speedup: {speedup:.2f}x"

class TestDataValidationPerformance:
    """데이터 검증 성능 테스트"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    def test_large_portfolio_validation_performance(self, validator):
        """대규모 포트폴리오 검증 성능 테스트"""
        # 1000개 종목 포트폴리오
        large_weights = {f'STOCK{i:04d}': 0.001 for i in range(1000)}

        start_time = time.time()
        is_valid, errors = validator.validate_portfolio_weights(large_weights)
        execution_time = time.time() - start_time

        # 검증이 빨라야 함
        assert execution_time < 0.1  # 100ms 이내
        assert is_valid

    def test_bulk_ticker_validation_performance(self, validator):
        """대량 티커 검증 성능 테스트"""
        tickers = [f'STOCK{i:04d}' for i in range(1000)]

        start_time = time.time()
        results = [validator.validate_ticker(ticker) for ticker in tickers]
        execution_time = time.time() - start_time

        # 대량 검증이 빨라야 함
        assert execution_time < 1.0  # 1초 이내
        assert len(results) == len(tickers)

class TestStreamlitPerformance:
    """Streamlit 관련 성능 테스트"""

    def test_dataframe_rendering_performance(self):
        """DataFrame 렌더링 성능 테스트"""
        # 큰 DataFrame 생성
        large_df = pd.DataFrame(
            np.random.randn(1000, 20),
            columns=[f'Column_{i}' for i in range(20)]
        )

        # 메모리 사용량 측정
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024

        # DataFrame 처리 시뮬레이션 (실제 Streamlit 렌더링은 하지 않음)
        processed_df = large_df.describe()
        formatted_df = large_df.round(2)

        memory_after = psutil.Process().memory_info().rss / 1024 / 1024
        memory_used = memory_after - memory_before

        # 메모리 사용량이 합리적이어야 함
        assert memory_used < 100  # 100MB 미만
        assert len(processed_df) > 0
        assert len(formatted_df) == len(large_df)

@pytest.mark.benchmark
class TestBenchmarks:
    """벤치마크 테스트"""

    def test_portfolio_calculation_benchmark(self, benchmark):
        """포트폴리오 계산 벤치마크"""
        # 중간 크기 포트폴리오
        dates = pd.date_range('2023-01-01', periods=252, freq='D')
        tickers = [f'STOCK{i:02d}' for i in range(20)]

        data = pd.DataFrame(
            {ticker: 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 252)))
             for ticker in tickers},
            index=dates
        )

        weights = {ticker: 1/len(tickers) for ticker in tickers}

        # 벤치마크 실행
        result = benchmark(backtesting.calculate_portfolio_value, data, weights)
        assert len(result) == len(data)

if __name__ == "__main__":
    # 성능 테스트 실행
    pytest.main([__file__, "-v", "--benchmark-only"])