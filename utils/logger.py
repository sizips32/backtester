"""
포트폴리오 백테스터용 로깅 시스템
개발, 디버깅, 모니터링을 위한 통합 로깅 솔루션
"""

import logging
import logging.handlers
import os
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import streamlit as st
import pandas as pd

# 설정 시스템 import
from config.app_config import get_config, get_logging_config

class PortfolioLogger:
    """포트폴리오 앱 전용 로거"""
    
    def __init__(self, name: str = "portfolio_app") -> None:
        self.name = name
        self.config = get_logging_config()
        self.logger = self._setup_logger()
        self._ensure_log_directory()
    
    def _ensure_log_directory(self) -> None:
        """로그 디렉토리 생성"""
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(exist_ok=True)
    
    def _setup_logger(self) -> logging.Logger:
        """로거 설정"""
        logger = logging.getLogger(self.name)
        
        # 이미 핸들러가 있으면 중복 생성 방지
        if logger.handlers:
            return logger
        
        logger.setLevel(getattr(logging, self.config.log_level))
        
        # 파일 핸들러 (로테이션)
        file_handler = logging.handlers.RotatingFileHandler(
            f"{self.config.log_dir}/{self.config.app_log_file}",
            maxBytes=self.config.max_bytes,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        
        # 에러 전용 핸들러
        error_handler = logging.handlers.RotatingFileHandler(
            f"{self.config.log_dir}/{self.config.error_log_file}",
            maxBytes=self.config.max_bytes // 2,
            backupCount=self.config.backup_count - 2,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        # 포매터 설정
        detailed_formatter = logging.Formatter(
            self.config.log_format,
            datefmt=self.config.date_format
        )
        
        error_formatter = logging.Formatter(
            f"{self.config.log_format}\nStack trace:\n%(exc_info)s\n" + '-' * 80,
            datefmt=self.config.date_format
        )
        
        file_handler.setFormatter(detailed_formatter)
        error_handler.setFormatter(error_formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
        
        return logger
    
    def log_user_action(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """사용자 액션 로깅"""
        message = f"USER_ACTION: {action}"
        if details:
            message += f" | Details: {json.dumps(details, ensure_ascii=False)}"
        
        self.logger.info(message)
    
    def log_data_fetch(self, ticker: str, success: bool, error: Optional[str] = None, 
                      data_points: Optional[int] = None) -> None:
        """데이터 가져오기 로깅"""
        if success:
            message = f"DATA_FETCH_SUCCESS: {ticker}"
            if data_points:
                message += f" | Data points: {data_points}"
        else:
            message = f"DATA_FETCH_FAILED: {ticker} | Error: {error}"
        
        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, message)
    
    def log_calculation(self, calc_type: str, success: bool, 
                       input_data: Dict[str, Any] = None, 
                       result: Any = None, error: str = None):
        """계산 결과 로깅"""
        message = f"CALCULATION: {calc_type}"
        
        if success:
            message += " | SUCCESS"
            if result is not None:
                if isinstance(result, dict):
                    message += f" | Result: {json.dumps(result, default=str, ensure_ascii=False)}"
                else:
                    message += f" | Result: {str(result)[:100]}"
        else:
            message += f" | FAILED | Error: {error}"
        
        if input_data:
            message += f" | Input: {json.dumps(input_data, default=str, ensure_ascii=False)[:200]}"
        
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, message)
    
    def log_portfolio_operation(self, operation: str, portfolio_id: int = None, 
                              symbols: list = None, success: bool = True, 
                              details: Dict[str, Any] = None):
        """포트폴리오 작업 로깅"""
        message = f"PORTFOLIO_OP: {operation}"
        
        if portfolio_id:
            message += f" | Portfolio ID: {portfolio_id}"
        
        if symbols:
            message += f" | Symbols: {symbols[:5]}"  # 처음 5개만
            if len(symbols) > 5:
                message += f" (+{len(symbols)-5} more)"
        
        if details:
            message += f" | Details: {json.dumps(details, default=str, ensure_ascii=False)}"
        
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, message)
    
    def log_performance_metric(self, metric_name: str, value: float, 
                              portfolio_id: int = None, timeframe: str = None):
        """성과 지표 로깅"""
        message = f"PERFORMANCE: {metric_name} = {value:.4f}"
        
        if portfolio_id:
            message += f" | Portfolio ID: {portfolio_id}"
        
        if timeframe:
            message += f" | Timeframe: {timeframe}"
        
        self.logger.info(message)
    
    def log_system_info(self, info_type: str, data: Dict[str, Any]):
        """시스템 정보 로깅"""
        message = f"SYSTEM_INFO: {info_type} | {json.dumps(data, default=str, ensure_ascii=False)}"
        self.logger.info(message)
    
    def log_validation_result(self, validation_type: str, passed: bool, 
                            errors: list = None, warnings: list = None):
        """검증 결과 로깅"""
        status = "PASSED" if passed else "FAILED"
        message = f"VALIDATION: {validation_type} | {status}"
        
        if errors:
            message += f" | Errors: {errors}"
        
        if warnings:
            message += f" | Warnings: {warnings}"
        
        level = logging.INFO if passed else logging.WARNING
        self.logger.log(level, message)
    
    def log_exception(self, exception: Exception, context: Dict[str, Any] = None):
        """예외 로깅"""
        message = f"EXCEPTION: {type(exception).__name__}: {str(exception)}"
        
        if context:
            message += f" | Context: {json.dumps(context, default=str, ensure_ascii=False)}"
        
        # 스택 트레이스 포함
        self.logger.error(message, exc_info=True)

class StreamlitLogHandler(logging.Handler):
    """Streamlit UI에 로그 표시하는 핸들러"""
    
    def __init__(self, container=None):
        super().__init__()
        self.container = container or st.container()
        self.logs = []
        self.max_logs = 100
    
    def emit(self, record):
        """로그 레코드를 Streamlit UI에 표시"""
        try:
            msg = self.format(record)
            timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
            
            # 로그 레벨별 색상
            if record.levelno >= logging.ERROR:
                icon = "🔴"
            elif record.levelno >= logging.WARNING:
                icon = "🟡"
            elif record.levelno >= logging.INFO:
                icon = "🔵"
            else:
                icon = "⚪"
            
            log_entry = {
                'timestamp': timestamp,
                'level': record.levelname,
                'message': msg,
                'icon': icon
            }
            
            self.logs.append(log_entry)
            
            # 최대 로그 수 제한
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs:]
                
        except Exception:
            self.handleError(record)
    
    def show_logs(self, level_filter: str = "ALL"):
        """Streamlit UI에 로그 표시"""
        with self.container:
            if not self.logs:
                st.info("표시할 로그가 없습니다.")
                return
            
            # 레벨 필터 적용
            filtered_logs = self.logs
            if level_filter != "ALL":
                filtered_logs = [log for log in self.logs if log['level'] == level_filter]
            
            # 최신 로그부터 표시
            for log in reversed(filtered_logs[-50:]):  # 최근 50개
                st.text(f"{log['icon']} {log['timestamp']} | {log['level']} | {log['message']}")

class LogAnalyzer:
    """로그 분석 클래스"""
    
    def __init__(self, log_file: str = "logs/portfolio_app.log"):
        self.log_file = log_file
    
    def get_log_stats(self, hours: int = 24) -> Dict[str, Any]:
        """로그 통계 분석"""
        if not os.path.exists(self.log_file):
            return {"error": "로그 파일이 없습니다."}
        
        try:
            stats = {
                "total_lines": 0,
                "error_count": 0,
                "warning_count": 0,
                "info_count": 0,
                "user_actions": [],
                "data_fetches": {"success": 0, "failed": 0},
                "calculations": {"success": 0, "failed": 0},
                "top_errors": {}
            }
            
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        stats["total_lines"] += 1
                        
                        # 시간 필터링
                        if ' | ' in line:
                            timestamp_str = line.split(' | ')[0]
                            try:
                                log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f').timestamp()
                                if log_time < cutoff_time:
                                    continue
                            except ValueError:
                                continue  # 타임스탬프 파싱 실패시 스킵
                        
                        # 로그 레벨 카운트
                        if "| ERROR |" in line:
                            stats["error_count"] += 1
                            # 에러 타입 추출
                            if "EXCEPTION:" in line:
                                error_type = line.split("EXCEPTION:")[1].split(":")[0].strip()
                                stats["top_errors"][error_type] = stats["top_errors"].get(error_type, 0) + 1
                        elif "| WARNING |" in line:
                            stats["warning_count"] += 1
                        elif "| INFO |" in line:
                            stats["info_count"] += 1
                        
                        # 특별한 로그 타입 분석
                        if "USER_ACTION:" in line:
                            action = line.split("USER_ACTION:")[1].split(" |")[0].strip()
                            stats["user_actions"].append(action)
                        
                        if "DATA_FETCH_SUCCESS:" in line:
                            stats["data_fetches"]["success"] += 1
                        elif "DATA_FETCH_FAILED:" in line:
                            stats["data_fetches"]["failed"] += 1
                        
                        if "CALCULATION:" in line and "SUCCESS" in line:
                            stats["calculations"]["success"] += 1
                        elif "CALCULATION:" in line and "FAILED" in line:
                            stats["calculations"]["failed"] += 1
                            
                    except Exception as e:
                        continue  # 개별 라인 파싱 에러는 무시
            
            return stats
            
        except Exception as e:
            return {"error": f"로그 분석 중 오류: {str(e)}"}
    
    def get_recent_errors(self, count: int = 10) -> list:
        """최근 에러 로그 가져오기"""
        if not os.path.exists(self.log_file):
            return []
        
        errors = []
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in reversed(lines):
                if "| ERROR |" in line and len(errors) < count:
                    errors.append(line.strip())
            
            return errors
            
        except Exception:
            return []

# 전역 로거 인스턴스
portfolio_logger = PortfolioLogger()

# 편의 함수들
def log_user_action(action: str, **kwargs):
    """사용자 액션 로깅 (편의 함수)"""
    portfolio_logger.log_user_action(action, kwargs)

def log_data_operation(operation: str, success: bool, **kwargs):
    """데이터 작업 로깅 (편의 함수)"""
    if success:
        portfolio_logger.logger.info(f"DATA_OP_SUCCESS: {operation} | {kwargs}")
    else:
        portfolio_logger.logger.error(f"DATA_OP_FAILED: {operation} | {kwargs}")

def log_calculation_result(calc_type: str, result: Any = None, error: str = None):
    """계산 결과 로깅 (편의 함수)"""
    success = error is None
    portfolio_logger.log_calculation(calc_type, success, result=result, error=error)

# Streamlit UI 컴포넌트
def show_log_dashboard():
    """로그 대시보드 표시"""
    st.subheader("📊 시스템 로그 대시보드")
    
    analyzer = LogAnalyzer()
    
    # 시간 범위 선택
    hours = st.selectbox(
        "분석 기간", 
        options=[1, 6, 12, 24, 48, 72],
        index=3,
        format_func=lambda x: f"최근 {x}시간"
    )
    
    # 통계 가져오기
    stats = analyzer.get_log_stats(hours)
    
    if "error" in stats:
        st.error(stats["error"])
        return
    
    # 메트릭 표시
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총 로그 수", stats["total_lines"])
    
    with col2:
        st.metric("에러 수", stats["error_count"])
    
    with col3:
        st.metric("경고 수", stats["warning_count"])
    
    with col4:
        success_rate = 0
        total_ops = stats["data_fetches"]["success"] + stats["data_fetches"]["failed"]
        if total_ops > 0:
            success_rate = (stats["data_fetches"]["success"] / total_ops) * 100
        st.metric("데이터 성공률", f"{success_rate:.1f}%")
    
    # 상세 정보
    col1, col2 = st.columns(2)
    
    with col1:
        if stats["top_errors"]:
            st.subheader("주요 에러")
            error_df = pd.DataFrame(
                list(stats["top_errors"].items()), 
                columns=["에러 타입", "발생 횟수"]
            )
            st.dataframe(error_df, use_container_width=True)
    
    with col2:
        if stats["user_actions"]:
            st.subheader("사용자 액션")
            action_counts = pd.Series(stats["user_actions"]).value_counts().head(10)
            st.bar_chart(action_counts)
    
    # 최근 에러들
    if st.expander("최근 에러 로그", expanded=False):
        recent_errors = analyzer.get_recent_errors(20)
        for error in recent_errors:
            st.text(error)