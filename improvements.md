# 포트폴리오 백테스터 개선 제안서

## 📋 Executive Summary
포트폴리오 백테스터의 코드 품질, 성능, UI/UX를 종합적으로 개선하기 위한 제안서입니다.

## 🔨 즉시 수정 필요 사항

### 1. Pandas Deprecated 메서드 수정
```python
# 현재 (portfolio_app.py:158)
df = df.fillna(method='ffill').fillna(method='bfill')

# 개선안
df = df.ffill().bfill()
```

### 2. pct_change 파라미터 오류 수정
```python
# 현재 (backtesting.py:89)
returns = data_filled.pct_change(fill_method=None)

# 개선안
returns = data_filled.pct_change()
```

## 🏗️ 아키텍처 개선

### 1. 중앙화된 데이터 서비스 레이어
```python
# services/data_service.py
class DataService:
    def __init__(self):
        self.cache = {}
        
    @lru_cache(maxsize=128)
    def fetch_stock_data(self, ticker, start_date, end_date):
        """통합된 데이터 fetching 로직"""
        # FinanceDataReader 우선, yfinance 폴백
        pass
        
    def batch_fetch(self, tickers, start_date, end_date):
        """병렬 데이터 fetching"""
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.fetch_stock_data, ticker, start_date, end_date) 
                      for ticker in tickers]
        return [future.result() for future in futures]
```

### 2. 설정 관리 개선
```python
# config.py
from dataclasses import dataclass
from typing import Dict

@dataclass
class AppConfig:
    TRADING_DAYS: int = 252
    RISK_FREE_RATE: float = 0.02
    DEFAULT_CONFIDENCE_LEVEL: float = 0.95
    
    # API 설정
    MAX_RETRIES: int = 3
    TIMEOUT: int = 30
    
    # UI 설정
    THEME: Dict = {
        'primary_color': '#1f77b4',
        'background_color': '#ffffff',
        'text_color': '#262730'
    }
    
config = AppConfig()
```

### 3. 에러 처리 개선
```python
# utils/error_handler.py
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def handle_errors(default_return=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{func.__name__} 실행 중 오류: {str(e)}")
                if default_return is not None:
                    return default_return
                raise
        return wrapper
    return decorator
```

## 🎨 UI/UX 개선

### 1. 상태 관리 개선
```python
# utils/state_manager.py
class StateManager:
    @staticmethod
    def init_session_state():
        defaults = {
            'current_portfolio_id': None,
            'portfolios': [],
            'data_cache': {},
            'ui_theme': 'light',
            'language': 'ko'
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
```

### 2. 진행 상황 표시 개선
```python
# components/progress_indicator.py
class ProgressIndicator:
    def __init__(self, total_steps):
        self.container = st.container()
        self.progress_bar = self.container.progress(0)
        self.status_text = self.container.empty()
        self.total_steps = total_steps
        self.current_step = 0
        
    def update(self, message):
        self.current_step += 1
        progress = self.current_step / self.total_steps
        self.progress_bar.progress(progress)
        self.status_text.text(message)
        
    def complete(self):
        self.container.empty()
```

### 3. 차트 인터랙션 개선
```python
# components/interactive_charts.py
def create_portfolio_chart(data, title):
    fig = go.Figure()
    
    # 호버 템플릿 개선
    hover_template = (
        "<b>날짜:</b> %{x}<br>"
        "<b>수익률:</b> %{y:.2f}%<br>"
        "<b>누적수익:</b> %{customdata:.2f}%<br>"
        "<extra></extra>"
    )
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['returns'],
        customdata=data['cumulative_returns'],
        mode='lines',
        hovertemplate=hover_template
    ))
    
    # 레이아웃 개선
    fig.update_layout(
        title=title,
        xaxis_title="날짜",
        yaxis_title="수익률 (%)",
        hovermode='x unified',
        showlegend=True,
        template='plotly_white'
    )
    
    return fig
```

## 🚀 성능 최적화

### 1. 데이터 캐싱 전략
```python
# utils/cache_manager.py
from functools import lru_cache
import hashlib

class CacheManager:
    def __init__(self, ttl=3600):
        self.ttl = ttl
        self.cache = {}
        
    def get_cache_key(self, *args, **kwargs):
        """캐시 키 생성"""
        key = hashlib.md5(
            f"{args}{kwargs}".encode()
        ).hexdigest()
        return key
        
    def cached_fetch(self, func):
        """데코레이터 형태의 캐싱"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = self.get_cache_key(*args, **kwargs)
            if key in self.cache:
                return self.cache[key]
            result = func(*args, **kwargs)
            self.cache[key] = result
            return result
        return wrapper
```

### 2. 병렬 처리 개선
```python
# utils/parallel_processor.py
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

class ParallelProcessor:
    def __init__(self, max_workers=5):
        self.max_workers = max_workers
        
    async def fetch_multiple_stocks(self, tickers, start_date, end_date):
        """비동기 병렬 데이터 fetching"""
        tasks = []
        for ticker in tickers:
            task = asyncio.create_task(
                self.fetch_single_stock(ticker, start_date, end_date)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {ticker: result for ticker, result in zip(tickers, results)}
```

## 🔒 보안 개선

### 1. 입력 검증 강화
```python
# utils/validators.py
import re
from typing import List

class InputValidator:
    @staticmethod
    def validate_ticker(ticker: str) -> bool:
        """티커 심볼 검증"""
        # 알파벳, 숫자, 특정 특수문자만 허용
        pattern = r'^[A-Z0-9\.\-\^]{1,10}$'
        return bool(re.match(pattern, ticker.upper()))
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """SQL 인젝션 방지를 위한 입력 sanitization"""
        # 위험한 문자 제거
        dangerous_chars = ["'", '"', ';', '--', '/*', '*/']
        for char in dangerous_chars:
            text = text.replace(char, '')
        return text.strip()
```

### 2. 데이터베이스 보안
```python
# utils/secure_db.py
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_secure_connection():
    """보안이 강화된 DB 연결"""
    conn = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False,
        isolation_level='DEFERRED'
    )
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
```

## 📱 반응형 디자인

### 1. 모바일 최적화
```python
# utils/responsive.py
def get_device_type():
    """디바이스 타입 감지"""
    # Streamlit의 기본 컨테이너 너비로 추정
    if st.sidebar.container().width < 768:
        return 'mobile'
    elif st.sidebar.container().width < 1024:
        return 'tablet'
    return 'desktop'

def responsive_columns(device_type):
    """반응형 컬럼 레이아웃"""
    if device_type == 'mobile':
        return st.columns([1])
    elif device_type == 'tablet':
        return st.columns([1, 1])
    return st.columns([1, 2, 1])
```

## 🧪 테스트 전략

### 1. 단위 테스트
```python
# tests/test_calculations.py
import pytest
import pandas as pd
import numpy as np
from backtesting import calculate_metrics

class TestCalculations:
    def test_sharpe_ratio(self):
        """샤프 비율 계산 테스트"""
        returns = pd.Series([0.01, -0.02, 0.03, 0.01, -0.01])
        metrics = calculate_metrics(returns)
        assert 'Sharpe Ratio' in metrics
        assert isinstance(metrics['Sharpe Ratio'], float)
        
    def test_max_drawdown(self):
        """최대 낙폭 계산 테스트"""
        returns = pd.Series([0.1, -0.2, 0.05, -0.1, 0.15])
        metrics = calculate_metrics(returns)
        assert metrics['Maximum Drawdown'] < 0
```

## 📊 모니터링 및 로깅

### 1. 로깅 시스템
```python
# utils/logger.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
    logger = logging.getLogger('portfolio_app')
    logger.setLevel(logging.INFO)
    
    # 파일 핸들러 (로테이션)
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    
    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    return logger
```

## 🎯 구현 우선순위

### Phase 1 (즉시)
1. Deprecated 메서드 수정
2. 에러 처리 개선
3. 입력 검증 강화

### Phase 2 (1주일)
1. 데이터 서비스 레이어 구현
2. 캐싱 전략 개선
3. UI 컴포넌트 리팩토링

### Phase 3 (2주일)
1. 병렬 처리 최적화
2. 반응형 디자인 구현
3. 테스트 커버리지 확대

### Phase 4 (1개월)
1. 고급 차트 기능
2. 실시간 데이터 지원
3. 머신러닝 기반 포트폴리오 최적화

## 📈 기대 효과

- **성능**: 데이터 로딩 속도 50% 개선
- **안정성**: 에러율 80% 감소
- **사용성**: 사용자 만족도 40% 향상
- **유지보수**: 코드 복잡도 30% 감소