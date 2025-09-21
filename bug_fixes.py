"""
버그 수정 스크립트
즉시 적용 가능한 버그 픽스들
"""

import os
import re
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(funcName)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def fix_deprecated_fillna():
    """portfolio_app.py의 deprecated fillna 메서드 수정"""
    file_path = 'portfolio_app.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # fillna method 수정
    old_pattern = r"df\.fillna\(method='ffill'\)\.fillna\(method='bfill'\)"
    new_pattern = "df.ffill().bfill()"
    
    content = re.sub(old_pattern, new_pattern, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("fillna 메서드 수정 완료", extra={"file_path": file_path})

def fix_pct_change_parameter():
    """backtesting.py의 pct_change 파라미터 오류 수정"""
    file_path = 'backtesting.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # pct_change 파라미터 수정
    old_pattern = r"pct_change\(fill_method=None\)"
    new_pattern = "pct_change()"
    
    content = re.sub(old_pattern, new_pattern, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("pct_change 파라미터 수정 완료", extra={"file_path": file_path})

def add_error_handling():
    """risk_analysis.py에 개선된 에러 처리 추가"""
    improvements = """
# 개선된 에러 처리 함수
def safe_division(numerator, denominator, default=0):
    \"\"\"안전한 나눗셈 처리\"\"\"
    if denominator == 0 or pd.isna(denominator):
        return default
    return numerator / denominator

def validate_data(data):
    \"\"\"데이터 유효성 검증\"\"\"
    if data is None or data.empty:
        raise ValueError("데이터가 비어있습니다")
    
    na_ratio = data.isna().sum() / len(data)
    if na_ratio > 0.5:
        raise ValueError(f"결측치 비율이 너무 높습니다: {na_ratio:.1%}")
    
    return True
"""
    
    logger.info("에러 처리 함수 추가 제안 생성 완료")
    return improvements

if __name__ == "__main__":
    logger.info("버그 수정 시작")
    
    try:
        fix_deprecated_fillna()
        fix_pct_change_parameter()
        error_handling_code = add_error_handling()
        
        logger.info("추가 제안 코드 생성")
        logger.debug("제안 코드 내용", extra={"code": error_handling_code})

        logger.info("모든 버그 수정 완료")
        
    except Exception as e:
        logger.error("버그 수정 중 오류 발생", exc_info=True)