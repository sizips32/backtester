"""
성능 모니터링 및 최적화 유틸리티
메모리 사용량, 실행 시간, 캐시 효율성 모니터링
"""

import functools
import time
import psutil
import gc
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import logging
import pandas as pd
import streamlit as st

# 로거 설정
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """성능 지표 데이터 클래스"""
    function_name: str
    execution_time: float
    memory_before: float
    memory_after: float
    memory_peak: float
    cache_hit: bool = False
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @property
    def memory_used(self) -> float:
        """사용된 메모리량 (MB)"""
        return self.memory_after - self.memory_before

    @property
    def memory_freed(self) -> float:
        """해제된 메모리량 (MB)"""
        return max(0, self.memory_before - self.memory_after)

class PerformanceMonitor:
    """성능 모니터링 클래스"""

    def __init__(self):
        self.metrics: Dict[str, list[PerformanceMetrics]] = {}
        self.thresholds = {
            'memory_mb': 100,  # 100MB 이상 사용시 경고
            'execution_time': 5.0,  # 5초 이상 실행시 경고
            'memory_growth_rate': 0.1  # 10% 이상 메모리 증가시 경고
        }

    def get_memory_usage(self) -> float:
        """현재 프로세스의 메모리 사용량 (MB)"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def get_system_memory(self) -> Dict[str, float]:
        """시스템 메모리 정보"""
        memory = psutil.virtual_memory()
        return {
            'total': memory.total / 1024 / 1024 / 1024,  # GB
            'available': memory.available / 1024 / 1024 / 1024,  # GB
            'percent': memory.percent,
            'used': memory.used / 1024 / 1024 / 1024  # GB
        }

    def force_garbage_collection(self) -> int:
        """강제 가비지 컬렉션 실행"""
        collected = gc.collect()
        logger.debug(f"가비지 컬렉션으로 {collected}개 객체 정리")
        return collected

    def monitor_function(self, func_name: str = None):
        """함수 성능 모니터링 데코레이터"""
        def decorator(func: Callable) -> Callable:
            name = func_name or func.__name__

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # 모니터링 시작
                memory_before = self.get_memory_usage()
                start_time = time.time()
                peak_memory = memory_before

                try:
                    # 함수 실행
                    result = func(*args, **kwargs)

                    # 실행 중 최대 메모리 사용량 측정
                    current_memory = self.get_memory_usage()
                    peak_memory = max(peak_memory, current_memory)

                    return result

                finally:
                    # 모니터링 종료
                    end_time = time.time()
                    memory_after = self.get_memory_usage()
                    execution_time = end_time - start_time

                    # 메트릭 생성 및 저장
                    metric = PerformanceMetrics(
                        function_name=name,
                        execution_time=execution_time,
                        memory_before=memory_before,
                        memory_after=memory_after,
                        memory_peak=peak_memory
                    )

                    self._record_metric(metric)
                    self._check_thresholds(metric)

            return wrapper
        return decorator

    def _record_metric(self, metric: PerformanceMetrics):
        """메트릭 기록"""
        if metric.function_name not in self.metrics:
            self.metrics[metric.function_name] = []

        self.metrics[metric.function_name].append(metric)

        # 최근 100개 기록만 유지
        if len(self.metrics[metric.function_name]) > 100:
            self.metrics[metric.function_name] = self.metrics[metric.function_name][-100:]

    def _check_thresholds(self, metric: PerformanceMetrics):
        """임계값 체크 및 경고"""
        warnings = []

        if metric.execution_time > self.thresholds['execution_time']:
            warnings.append(f"실행 시간 초과: {metric.execution_time:.2f}초")

        if abs(metric.memory_used) > self.thresholds['memory_mb']:
            warnings.append(f"메모리 사용량 초과: {metric.memory_used:.1f}MB")

        if warnings:
            logger.warning(
                f"성능 경고 - {metric.function_name}: {', '.join(warnings)}"
            )

    def get_function_stats(self, function_name: str) -> Optional[Dict[str, Any]]:
        """특정 함수의 성능 통계"""
        if function_name not in self.metrics:
            return None

        metrics = self.metrics[function_name]
        execution_times = [m.execution_time for m in metrics]
        memory_usages = [m.memory_used for m in metrics]

        return {
            'call_count': len(metrics),
            'avg_execution_time': sum(execution_times) / len(execution_times),
            'max_execution_time': max(execution_times),
            'min_execution_time': min(execution_times),
            'avg_memory_usage': sum(memory_usages) / len(memory_usages),
            'max_memory_usage': max(memory_usages),
            'total_memory_used': sum(memory_usages),
            'last_called': metrics[-1].timestamp
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """시스템 전체 성능 통계"""
        system_memory = self.get_system_memory()
        process_memory = self.get_memory_usage()

        return {
            'system_memory': system_memory,
            'process_memory_mb': process_memory,
            'memory_usage_percent': (process_memory / 1024) / system_memory['total'] * 100,
            'functions_monitored': len(self.metrics),
            'total_function_calls': sum(len(metrics) for metrics in self.metrics.values())
        }

    def generate_report(self) -> pd.DataFrame:
        """성능 리포트 생성"""
        report_data = []

        for func_name in self.metrics:
            stats = self.get_function_stats(func_name)
            if stats:
                report_data.append({
                    '함수명': func_name,
                    '호출 횟수': stats['call_count'],
                    '평균 실행시간(s)': f"{stats['avg_execution_time']:.3f}",
                    '최대 실행시간(s)': f"{stats['max_execution_time']:.3f}",
                    '평균 메모리(MB)': f"{stats['avg_memory_usage']:.1f}",
                    '최대 메모리(MB)': f"{stats['max_memory_usage']:.1f}",
                    '총 메모리(MB)': f"{stats['total_memory_used']:.1f}",
                    '마지막 호출': stats['last_called'].strftime('%H:%M:%S')
                })

        return pd.DataFrame(report_data)

    def optimize_memory(self):
        """메모리 최적화 실행"""
        before = self.get_memory_usage()

        # 가비지 컬렉션
        collected = self.force_garbage_collection()

        # Streamlit 캐시 정리
        if hasattr(st, 'cache_data'):
            try:
                st.cache_data.clear()
            except:
                pass

        after = self.get_memory_usage()
        freed = before - after

        logger.info(f"메모리 최적화 완료: {freed:.1f}MB 해제, {collected}개 객체 정리")

        return {
            'memory_freed_mb': freed,
            'objects_collected': collected,
            'memory_before_mb': before,
            'memory_after_mb': after
        }

# 전역 성능 모니터 인스턴스
performance_monitor = PerformanceMonitor()

# 편의 함수들
def monitor_performance(func_name: str = None):
    """성능 모니터링 데코레이터"""
    return performance_monitor.monitor_function(func_name)

def get_memory_usage() -> float:
    """현재 메모리 사용량 (MB)"""
    return performance_monitor.get_memory_usage()

def optimize_memory() -> Dict[str, Any]:
    """메모리 최적화"""
    return performance_monitor.optimize_memory()

def show_performance_dashboard():
    """Streamlit 성능 대시보드"""
    st.subheader("🔍 성능 모니터링 대시보드")

    # 시스템 현황
    system_stats = performance_monitor.get_system_stats()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("프로세스 메모리", f"{system_stats['process_memory_mb']:.1f}MB")
    with col2:
        st.metric("시스템 메모리 사용률", f"{system_stats['system_memory']['percent']:.1f}%")
    with col3:
        st.metric("모니터링 함수", f"{system_stats['functions_monitored']}개")
    with col4:
        st.metric("총 함수 호출", f"{system_stats['total_function_calls']}회")

    # 메모리 최적화 버튼
    if st.button("🗑️ 메모리 최적화"):
        result = optimize_memory()
        st.success(f"메모리 {result['memory_freed_mb']:.1f}MB 해제됨")

    # 함수별 성능 리포트
    if performance_monitor.metrics:
        st.subheader("📊 함수별 성능 리포트")
        report_df = performance_monitor.generate_report()
        st.dataframe(report_df, use_container_width=True)
    else:
        st.info("아직 모니터링된 함수 실행이 없습니다.")