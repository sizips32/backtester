"""
포트폴리오 백테스터 통합 설정 관리 (Pydantic 기반)
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- 개별 설정 모델 정의 (BaseModel) ---

class APIConfig(BaseModel):
    primary_data_source: str = "FinanceDataReader"
    fallback_data_source: str = "yfinance"
    max_retries: int = Field(3, gt=0)
    timeout_seconds: int = Field(30, gt=0)
    backoff_factor: float = Field(1.0, gt=0)
    cache_ttl_seconds: int = 3600
    enable_caching: bool = True
    max_workers: int = Field(5, gt=0)
    batch_size: int = 10

class TradingConfig(BaseModel):
    trading_days_per_year: int = 252
    risk_free_rate: float = Field(0.02, ge=0, le=1)
    transaction_cost: float = Field(0.001, ge=0, le=0.1)
    slippage: float = Field(0.0005, ge=0, le=0.1)
    rebalance_threshold: float = Field(0.05, ge=0, le=1)
    min_cash_ratio: float = Field(0.02, ge=0, le=1)

class AnalysisConfig(BaseModel):
    min_analysis_days: int = Field(30, gt=0)
    max_analysis_days: int = 3650
    min_data_completeness: float = Field(0.8, ge=0, le=1)
    max_missing_data_ratio: float = Field(0.5, ge=0, le=1)
    confidence_levels: Dict[str, float] = {"standard": 0.95, "strict": 0.99}
    rolling_windows: Dict[str, int] = {"short": 20, "medium": 60, "long": 252}

    @field_validator('max_analysis_days')
    def check_max_days(cls, v, values):
        if 'min_analysis_days' in values.data and v <= values.data['min_analysis_days']:
            raise ValueError("max_analysis_days는 min_analysis_days보다 커야 합니다")
        return v

class DatabaseConfig(BaseModel):
    db_path: str = "data/portfolio.db"
    connection_timeout: int = 30
    enable_backup: bool = True
    backup_interval_hours: int = 24
    max_backups: int = 7
    pragma_settings: Dict[str, Any] = {
        "journal_mode": "WAL",
        "synchronous": "NORMAL",
        "cache_size": -64000,  # 64MB
        "temp_store": "MEMORY"
    }

class UIConfig(BaseModel):
    page_title: str = "포트폴리오 백테스터"
    page_icon: str = "💰"
    layout: str = "wide"
    default_theme: str = "light"
    colors: Dict[str, str] = {
        'primary': '#1f77b4',
        'success': '#2ca02c',
        'danger': '#d62728',
        'warning': '#ff7f0e',
        'info': '#17a2b8',
        'light': '#f8f9fa',
        'dark': '#343a40'
    }
    chart_template: str = 'plotly_white'
    chart_height: int = 500
    font_family: str = 'Arial, sans-serif'
    max_table_rows: int = 1000
    default_page_size: int = 50

class LoggingConfig(BaseModel):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_dir: str = "logs"
    app_log_file: str = "portfolio_app.log"
    error_log_file: str = "portfolio_errors.log"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    log_format: str = "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"

class ValidationConfig(BaseModel):
    ticker_patterns: Dict[str, str] = {
        'US_STOCK': r'^[A-Z]{1,5}$',
        'US_INDEX': r'^\^[A-Z0-9]{1,10}$',  # Yahoo Finance index starts with ^
        'KR_STOCK': r'^\d{6}$',
        'KR_STOCK_KS': r'^\d{6}\.KS$',
        'KR_STOCK_KQ': r'^\d{6}\.KQ$',
        'CRYPTO': r'^[A-Z]{3,10}-[A-Z]{3,4}$',
        'ETF': r'^[A-Z]{3,5}$',
    }
    asset_limits: Dict[str, Dict[str, float]] = {
        'Stock': {
            'min_quantity': 0.001,
            'min_price': 0.01,
            'max_price': 10000.0
        },
        'Bond': {
            'min_quantity': 0.001,
            'min_price': 0.01,
            'max_price': 10000.0
        },
        'ETF': {
            'min_quantity': 0.001,
            'min_price': 0.01,
            'max_price': 10000.0
        },
        'Crypto': {
            'min_quantity': 0.00000001,
            'min_price': 0.000001,
            'max_price': 1000000.0
        },
        'Cash': {
            'min_quantity': 0.01,
            'min_price': 1.0,
            'max_price': 1.0
        },
        'Commodity': {
            'min_quantity': 0.001,
            'min_price': 0.01,
            'max_price': 100000.0
        }
    }
    max_portfolio_assets: int = 50
    weight_tolerance: float = Field(0.01, gt=0, lt=1)
    max_single_asset_weight: float = Field(0.5, gt=0, le=1)

# --- 통합 설정 모델 (BaseSettings) ---

class AppConfig(BaseSettings):
    """환경 변수, .env 파일, 기본값을 통합하여 설정을 관리합니다."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter='__', # 예: LOGGING__LOG_LEVEL
        case_sensitive=False
    )

    # 서브 설정 모델
    api: APIConfig = Field(default_factory=APIConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)

    # 애플리케이션 메타정보
    app_name: str = "Portfolio BackTester"
    version: str = "2.0.0"
    debug_mode: bool = False

    def ensure_directories(self) -> None:
        """설정에 명시된 필수 디렉토리들이 존재하는지 확인하고 없으면 생성합니다."""
        directories = [
            self.logging.log_dir,
            os.path.dirname(self.database.db_path),
            "data",
            "cache"
        ]
        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)

    def get_log_level(self) -> int:
        """로그 레벨을 숫자로 반환합니다."""
        return getattr(logging, self.logging.log_level, logging.INFO)

# --- 전역 설정 인스턴스 및 편의 함수 ---

# 설정 인스턴스 생성
config = AppConfig()
# 필수 디렉토리 생성 실행
config.ensure_directories()

def get_config() -> AppConfig:
    return config

def get_api_config() -> APIConfig:
    return config.api

def get_trading_config() -> TradingConfig:
    return config.trading

def get_analysis_config() -> AnalysisConfig:
    return config.analysis

def get_ui_config() -> UIConfig:
    return config.ui

def get_validation_config() -> ValidationConfig:
    return config.validation

def get_logging_config() -> LoggingConfig:
    return config.logging

def get_database_config() -> DatabaseConfig:
    return config.database
