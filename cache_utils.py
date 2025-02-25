"""캐시 유틸리티"""
import streamlit as st
from functools import wraps
from datetime import datetime, timedelta

def cache_with_ttl(ttl_seconds: int = 3600):
    """TTL이 있는 캐시 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}_{str(args)}_{str(kwargs)}"
            
            if cache_key not in st.session_state:
                st.session_state[cache_key] = {
                    'data': None,
                    'timestamp': None
                }
            
            cache = st.session_state[cache_key]
            now = datetime.now()
            
            if (cache['timestamp'] is None or 
                (now - cache['timestamp']).total_seconds() > ttl_seconds):
                result = func(*args, **kwargs)
                cache['data'] = result
                cache['timestamp'] = now
                return result
            
            return cache['data']
        return wrapper
    return decorator 
