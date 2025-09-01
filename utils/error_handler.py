"""
개선된 에러 처리 시스템
사용자 친화적 에러 메시지 및 복구 전략 제공
"""

import streamlit as st
import logging
from functools import wraps
from typing import Any, Callable, Optional, Dict, Union
import traceback
from datetime import datetime

# 설정 시스템 import
from config.app_config import get_config

# 에러 타입별 메시지 정의
ERROR_MESSAGES = {
    'network': {
        'ConnectionError': "인터넷 연결을 확인해주세요.",
        'TimeoutError': "요청 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
        'HTTPError': "서버 응답에 문제가 있습니다. 잠시 후 다시 시도해주세요.",
    },
    'data': {
        'ValueError': "입력된 데이터에 문제가 있습니다. 값을 확인해주세요.",
        'KeyError': "필요한 데이터가 누락되었습니다.",
        'IndexError': "데이터 범위를 벗어났습니다.",
        'TypeError': "잘못된 데이터 형식입니다.",
    },
    'financial': {
        'TickerNotFoundError': "종목 코드를 찾을 수 없습니다. 올바른 종목 코드를 입력해주세요.",
        'DataUnavailableError': "해당 기간의 데이터를 사용할 수 없습니다.",
        'InsufficientDataError': "분석에 필요한 충분한 데이터가 없습니다.",
    },
    'calculation': {
        'ZeroDivisionError': "계산 중 0으로 나누는 오류가 발생했습니다.",
        'OverflowError': "계산 결과가 너무 큽니다.",
        'FloatingPointError': "수치 계산 중 오류가 발생했습니다.",
    }
}

# 커스텀 예외 클래스들
class PortfolioError(Exception):
    """포트폴리오 관련 기본 예외"""
    pass

class TickerNotFoundError(PortfolioError):
    """종목을 찾을 수 없는 경우"""
    pass

class DataUnavailableError(PortfolioError):
    """데이터를 사용할 수 없는 경우"""
    pass

class InsufficientDataError(PortfolioError):
    """충분하지 않은 데이터"""
    pass

class ValidationError(PortfolioError):
    """데이터 검증 실패"""
    pass

class CalculationError(PortfolioError):
    """계산 오류"""
    pass

class ErrorHandler:
    """중앙화된 에러 처리 클래스"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.error_count = {}
    
    def _setup_logger(self):
        """로거 설정"""
        logger = logging.getLogger('portfolio_error_handler')
        logger.setLevel(logging.INFO)
        
        # 핸들러가 이미 있으면 추가하지 않음
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def get_user_friendly_message(self, error: Exception) -> str:
        """사용자 친화적 에러 메시지 생성"""
        error_type = type(error).__name__
        error_str = str(error).lower()
        
        # 네트워크 관련 에러
        if any(keyword in error_str for keyword in ['connection', 'network', 'timeout']):
            category = 'network'
        # 데이터 관련 에러
        elif any(keyword in error_str for keyword in ['data', 'value', 'key', 'index']):
            category = 'data'
        # 금융 데이터 관련 에러
        elif any(keyword in error_str for keyword in ['ticker', 'symbol', 'yahoo', 'finance']):
            category = 'financial'
        # 계산 관련 에러
        elif any(keyword in error_str for keyword in ['division', 'overflow', 'calculation']):
            category = 'calculation'
        else:
            category = 'data'  # 기본값
        
        # 해당 카테고리에서 에러 타입 찾기
        if category in ERROR_MESSAGES and error_type in ERROR_MESSAGES[category]:
            return ERROR_MESSAGES[category][error_type]
        
        # 기본 메시지
        return f"오류가 발생했습니다: {str(error)}"
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """에러 로깅"""
        error_type = type(error).__name__
        
        # 에러 발생 횟수 추적
        self.error_count[error_type] = self.error_count.get(error_type, 0) + 1
        
        # 컨텍스트 정보
        context_info = ""
        if context:
            context_info = f" | Context: {context}"
        
        # 에러 로그 기록
        self.logger.error(
            f"Error: {error_type} - {str(error)} | "
            f"Count: {self.error_count[error_type]}{context_info}"
        )
        
        # 스택 트레이스는 DEBUG 레벨에서만
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None, 
                    show_user_message: bool = True) -> Optional[str]:
        """통합 에러 처리"""
        # 에러 로깅
        self.log_error(error, context)
        
        # 사용자 메시지 생성
        user_message = self.get_user_friendly_message(error)
        
        # Streamlit에 메시지 표시
        if show_user_message:
            if isinstance(error, (ConnectionError, TimeoutError)):
                st.error(f"🌐 연결 오류: {user_message}")
            elif isinstance(error, (TickerNotFoundError, DataUnavailableError)):
                st.error(f"📊 데이터 오류: {user_message}")
            elif isinstance(error, ValidationError):
                st.error(f"✅ 검증 오류: {user_message}")
            else:
                st.error(f"⚠️ {user_message}")
        
        return user_message
    
    def get_error_statistics(self) -> Dict[str, int]:
        """에러 통계 반환"""
        return self.error_count.copy()

# 전역 에러 핸들러 인스턴스
error_handler = ErrorHandler()

def handle_errors(
    default_return: Any = None,
    show_message: bool = True,
    context: Dict[str, Any] = None
):
    """데코레이터: 함수의 에러를 자동으로 처리"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 컨텍스트에 함수 정보 추가
                func_context = {
                    'function': func.__name__,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys()) if kwargs else []
                }
                if context:
                    func_context.update(context)
                
                # 에러 처리
                error_handler.handle_error(e, func_context, show_message)
                
                return default_return
        return wrapper
    return decorator

def safe_execute(
    func: Callable,
    *args,
    default_return: Any = None,
    error_message: str = None,
    **kwargs
) -> Any:
    """안전한 함수 실행"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if error_message:
            st.error(error_message)
        else:
            error_handler.handle_error(e)
        return default_return

def validate_and_execute(
    validation_func: Callable,
    execution_func: Callable,
    *args,
    **kwargs
) -> Any:
    """검증 후 실행"""
    try:
        # 먼저 검증 수행
        if not validation_func(*args, **kwargs):
            raise ValidationError("입력 데이터 검증에 실패했습니다")
        
        # 검증 통과 시 실행
        return execution_func(*args, **kwargs)
        
    except ValidationError:
        raise  # ValidationError는 그대로 전파
    except Exception as e:
        error_handler.handle_error(e)
        return None

class ErrorRecovery:
    """에러 복구 전략"""
    
    @staticmethod
    def retry_with_backoff(
        func: Callable,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        *args,
        **kwargs
    ) -> Any:
        """백오프를 사용한 재시도"""
        import time
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = backoff_factor * (2 ** attempt)
                    st.info(f"재시도 중... ({attempt + 1}/{max_retries}) - {wait_time:.1f}초 대기")
                    time.sleep(wait_time)
                else:
                    error_handler.handle_error(e, {'final_attempt': True})
        
        return None
    
    @staticmethod
    def fallback_chain(fallback_funcs: list, *args, **kwargs) -> Any:
        """폴백 체인 실행"""
        for i, func in enumerate(fallback_funcs):
            try:
                result = func(*args, **kwargs)
                if result is not None:
                    if i > 0:  # 첫 번째 함수가 아닌 경우
                        st.info(f"대체 방법 {i+1}으로 데이터를 가져왔습니다.")
                    return result
            except Exception as e:
                if i == len(fallback_funcs) - 1:  # 마지막 함수인 경우
                    error_handler.handle_error(e, {'final_fallback': True})
                else:
                    error_handler.log_error(e, {'fallback_attempt': i+1})
                continue
        
        return None

# 에러 상태 표시 컴포넌트
class ErrorStatusDisplay:
    """에러 상태 표시"""
    
    @staticmethod
    def show_error_summary():
        """에러 요약 표시"""
        stats = error_handler.get_error_statistics()
        if stats:
            with st.expander("⚠️ 에러 통계", expanded=False):
                for error_type, count in stats.items():
                    st.write(f"• {error_type}: {count}회")
    
    @staticmethod
    def show_system_status():
        """시스템 상태 표시"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("총 에러 수", sum(error_handler.get_error_statistics().values()))
        
        with col2:
            st.metric("에러 타입 수", len(error_handler.get_error_statistics()))
        
        with col3:
            # 간단한 시스템 상태 체크
            try:
                import yfinance as yf
                # 간단한 연결 테스트
                ticker = yf.Ticker("AAPL")
                _ = ticker.info.get('regularMarketPrice')
                status = "✅ 정상"
            except:
                status = "❌ 오류"
            
            st.metric("외부 API", status)