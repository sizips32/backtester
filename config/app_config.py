"""
포트폴리오 백테스터 통합 설정 관리
중앙화된 설정 시스템으로 유지보수성 향상
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import timedelta
import logging

@dataclass
class APIConfig:
    """API 관련 설정"""
    # 데이터 소스 설정
    primary_data_source: str = "FinanceDataReader"
    fallback_data_source: str = "yfinance"
    
    # 요청 설정
    max_retries: int = 3
    timeout_seconds: int = 30
    backoff_factor: float = 1.0
    
    # 캐시 설정
    cache_ttl_seconds: int = 3600  # 1시간
    enable_caching: bool = True
    
    # 병렬 처리 설정
    max_workers: int = 5
    batch_size: int = 10

@dataclass
class TradingConfig:
    """거래 관련 설정"""
    # 거래일 설정
    trading_days_per_year: int = 252
    
    # 기본 무위험 수익률
    risk_free_rate: float = 0.02
    
    # 거래 비용
    transaction_cost: float = 0.001  # 0.1%
    slippage: float = 0.0005  # 0.05%
    
    # 리밸런싱
    rebalance_threshold: float = 0.05  # 5%
    min_cash_ratio: float = 0.02  # 2%

@dataclass
class AnalysisConfig:
    """분석 관련 설정"""
    # 날짜 범위 제한
    min_analysis_days: int = 30
    max_analysis_days: int = 3650  # 10년
    
    # 데이터 품질 기준
    min_data_completeness: float = 0.8
    max_missing_data_ratio: float = 0.5
    
    # 성과 지표 설정
    confidence_levels: Dict[str, float] = field(default_factory=lambda: {
        "standard": 0.95,
        "strict": 0.99
    })
    
    # 롤링 윈도우
    rolling_windows: Dict[str, int] = field(default_factory=lambda: {
        "short": 20,
        "medium": 60,
        "long": 252
    })

@dataclass
class DatabaseConfig:
    """데이터베이스 설정"""
    # SQLite 설정
    db_path: str = "data/portfolio.db"
    connection_timeout: int = 30
    
    # 백업 설정
    enable_backup: bool = True
    backup_interval_hours: int = 24
    max_backups: int = 7
    
    # 성능 설정
    pragma_settings: Dict[str, Any] = field(default_factory=lambda: {
        "journal_mode": "WAL",
        "synchronous": "NORMAL",
        "cache_size": -64000,  # 64MB
        "temp_store": "MEMORY"
    })

@dataclass
class UIConfig:
    """UI 관련 설정"""
    # 페이지 설정
    page_title: str = "포트폴리오 백테스터"
    page_icon: str = "💰"
    layout: str = "wide"
    
    # 테마 설정
    default_theme: str = "light"
    colors: Dict[str, str] = field(default_factory=lambda: {
        'primary': '#1f77b4',
        'success': '#2ca02c',
        'danger': '#d62728',
        'warning': '#ff7f0e',
        'info': '#17a2b8',
        'light': '#f8f9fa',
        'dark': '#343a40'
    })
    
    # 차트 설정
    chart_template: str = 'plotly_white'
    chart_height: int = 500
    font_family: str = 'Arial, sans-serif'
    
    # 테이블 설정
    max_table_rows: int = 1000
    default_page_size: int = 50

@dataclass
class LoggingConfig:
    """로깅 설정"""
    # 로그 레벨
    log_level: str = "INFO"
    
    # 파일 설정
    log_dir: str = "logs"
    app_log_file: str = "portfolio_app.log"
    error_log_file: str = "portfolio_errors.log"
    
    # 로그 로테이션
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    # 포맷
    log_format: str = "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"

@dataclass
class ValidationConfig:
    """검증 설정"""
    # 종목 코드 패턴
    ticker_patterns: Dict[str, str] = field(default_factory=lambda: {
        'US_STOCK': r'^[A-Z]{1,5}$',
        'US_INDEX': r'^\^[A-Z0-9]{1,10}$',
        'KR_STOCK': r'^\d{6}$',
        'KR_STOCK_KS': r'^\d{6}\.KS$',
        'KR_STOCK_KQ': r'^\d{6}\.KQ$',
        'CRYPTO': r'^[A-Z]{3,10}-[A-Z]{3,4}$',
        'ETF': r'^[A-Z]{3,5}$',
    })
    
    # 자산 유형별 제한
    asset_limits: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'Stock': {'min_price': 0.01, 'max_price': 100000, 'min_quantity': 0.001},
        'ETF': {'min_price': 0.01, 'max_price': 10000, 'min_quantity': 0.001},
        'Bond': {'min_price': 0.01, 'max_price': 10000, 'min_quantity': 0.001},
        'Crypto': {'min_price': 0.000001, 'max_price': 1000000, 'min_quantity': 0.00000001},
        'Cash': {'min_price': 0.01, 'max_price': 1000000, 'min_quantity': 0.01},
        'Commodity': {'min_price': 0.01, 'max_price': 100000, 'min_quantity': 0.001},
    })
    
    # 포트폴리오 제한
    max_portfolio_assets: int = 50
    weight_tolerance: float = 0.01
    max_single_asset_weight: float = 0.5  # 50%

@dataclass
class PerformanceConfig:
    """성능 설정"""
    # 메모리 관리
    max_cache_size: int = 128
    cache_cleanup_interval: int = 3600  # 1시간
    
    # 병렬 처리
    enable_parallel_processing: bool = True
    chunk_size: int = 1000
    
    # 프로파일링
    enable_profiling: bool = False
    profile_output_dir: str = "profiles"

@dataclass
class AppConfig:
    """통합 애플리케이션 설정"""
    # 서브 설정들
    api: APIConfig = field(default_factory=APIConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # 애플리케이션 메타정보
    app_name: str = "Portfolio BackTester"
    version: str = "2.0.0"
    debug_mode: bool = False
    
    def __post_init__(self):
        """초기화 후 추가 설정"""
        # 환경변수에서 설정 오버라이드
        self._load_from_environment()
        
        # 필수 디렉토리 생성
        self._ensure_directories()
        
        # 설정 검증
        self._validate_config()
    
    def _load_from_environment(self) -> None:
        """환경변수에서 설정 로드"""
        # 디버그 모드
        if os.getenv("PORTFOLIO_DEBUG", "false").lower() == "true":
            self.debug_mode = True
            self.logging.log_level = "DEBUG"
        
        # API 설정
        if max_workers := os.getenv("PORTFOLIO_MAX_WORKERS"):
            self.api.max_workers = int(max_workers)
        
        if timeout := os.getenv("PORTFOLIO_TIMEOUT"):
            self.api.timeout_seconds = int(timeout)
        
        # 데이터베이스 경로
        if db_path := os.getenv("PORTFOLIO_DB_PATH"):
            self.database.db_path = db_path
        
        # 로그 레벨
        if log_level := os.getenv("PORTFOLIO_LOG_LEVEL"):
            self.logging.log_level = log_level.upper()
    
    def _ensure_directories(self) -> None:
        """필수 디렉토리 생성"""
        directories = [
            self.logging.log_dir,
            os.path.dirname(self.database.db_path),
            "data",
            "cache"
        ]
        
        if self.performance.enable_profiling:
            directories.append(self.performance.profile_output_dir)
        
        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
    
    def _validate_config(self) -> None:
        """설정 검증"""
        # API 설정 검증
        assert self.api.max_retries > 0, "max_retries는 0보다 커야 합니다"
        assert self.api.timeout_seconds > 0, "timeout_seconds는 0보다 커야 합니다"
        assert self.api.max_workers > 0, "max_workers는 0보다 커야 합니다"
        
        # 거래 설정 검증
        assert 0 <= self.trading.risk_free_rate <= 1, "risk_free_rate는 0~1 사이여야 합니다"
        assert 0 <= self.trading.transaction_cost <= 0.1, "transaction_cost는 0~0.1 사이여야 합니다"
        
        # 분석 설정 검증
        assert self.analysis.min_analysis_days > 0, "min_analysis_days는 0보다 커야 합니다"
        assert self.analysis.max_analysis_days > self.analysis.min_analysis_days, \
               "max_analysis_days는 min_analysis_days보다 커야 합니다"
        
        # 검증 설정 검증
        assert 0 < self.validation.weight_tolerance < 1, "weight_tolerance는 0~1 사이여야 합니다"
        assert 0 < self.validation.max_single_asset_weight <= 1, \
               "max_single_asset_weight는 0~1 사이여야 합니다"
    
    def get_log_level(self) -> int:
        """로그 레벨을 숫자로 반환"""
        return getattr(logging, self.logging.log_level, logging.INFO)
    
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.debug_mode or os.getenv("ENVIRONMENT", "production").lower() in ["dev", "development"]
    
    def get_database_url(self) -> str:
        """데이터베이스 URL 생성"""
        return f"sqlite:///{self.database.db_path}"
    
    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환 (디버깅용)"""
        import json
        from dataclasses import asdict
        
        try:
            return asdict(self)
        except Exception as e:
            # 직렬화 실패시 기본 정보만 반환
            return {
                "app_name": self.app_name,
                "version": self.version,
                "debug_mode": self.debug_mode,
                "error": str(e)
            }

# 전역 설정 인스턴스
config = AppConfig()

# 편의 함수들
def get_config() -> AppConfig:
    """전역 설정 인스턴스 반환"""
    return config

def get_api_config() -> APIConfig:
    """API 설정 반환"""
    return config.api

def get_trading_config() -> TradingConfig:
    """거래 설정 반환"""
    return config.trading

def get_analysis_config() -> AnalysisConfig:
    """분석 설정 반환"""
    return config.analysis

def get_ui_config() -> UIConfig:
    """UI 설정 반환"""
    return config.ui

def get_validation_config() -> ValidationConfig:
    """검증 설정 반환"""
    return config.validation

def get_logging_config() -> LoggingConfig:
    """로깅 설정 반환"""
    return config.logging

def get_database_config() -> DatabaseConfig:
    """데이터베이스 설정 반환"""
    return config.database

def get_performance_config() -> PerformanceConfig:
    """성능 설정 반환"""
    return config.performance

def reload_config():
    """설정 재로드"""
    global config
    config = AppConfig()
    return config