#!/usr/bin/env python3
"""
MCP 서버 디버그 래퍼 - Claude Desktop 실행 환경에서 정확한 에러 캡처
"""

import sys
import os
import subprocess
import json
import time
from datetime import datetime

def log_message(msg):
    """디버그 로그 작성"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = "/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester/mcp_server/debug.log"
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}", file=sys.stderr)

def main():
    """디버그 래퍼 메인 함수"""

    log_message("=== MCP Server Debug Wrapper Started ===")

    # 환경 정보 로깅
    log_message(f"Python version: {sys.version}")
    log_message(f"Working directory: {os.getcwd()}")
    log_message(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    log_message(f"FASTMCP_QUIET: {os.environ.get('FASTMCP_QUIET', 'Not set')}")
    log_message(f"FASTMCP_NO_BANNER: {os.environ.get('FASTMCP_NO_BANNER', 'Not set')}")

    # 파일 존재 확인
    server_path = "/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester/mcp_server/portfolio_mcp_server.py"
    if os.path.exists(server_path):
        log_message(f"✅ Server file exists: {server_path}")
    else:
        log_message(f"❌ Server file NOT found: {server_path}")
        sys.exit(1)

    # 필수 모듈 import 테스트
    try:
        import fastmcp
        log_message(f"✅ FastMCP available: {fastmcp.__version__}")
    except ImportError as e:
        log_message(f"❌ FastMCP import failed: {e}")
        sys.exit(1)

    # 데이터베이스 접근 테스트
    try:
        sys.path.insert(0, "/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester")
        from utils.database import SessionLocal, Portfolio
        session = SessionLocal()
        count = session.query(Portfolio).count()
        session.close()
        log_message(f"✅ Database accessible: {count} portfolios")
    except Exception as e:
        log_message(f"⚠️ Database issue: {e}")

    # 실제 서버 실행
    log_message("🚀 Starting actual MCP server...")

    try:
        # 환경 변수 설정
        env = os.environ.copy()
        env['PYTHONPATH'] = '/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester'
        env['FASTMCP_QUIET'] = '1'
        env['FASTMCP_NO_BANNER'] = '1'

        # 서버 실행
        process = subprocess.Popen(
            [sys.executable, server_path],
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=subprocess.PIPE,  # stderr만 캡처
            env=env,
            cwd='/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester'
        )

        # stderr 모니터링
        def monitor_stderr():
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                log_message(f"STDERR: {line.decode().strip()}")

        import threading
        stderr_thread = threading.Thread(target=monitor_stderr)
        stderr_thread.daemon = True
        stderr_thread.start()

        # 프로세스 대기
        return_code = process.wait()
        log_message(f"Server exited with code: {return_code}")

    except Exception as e:
        log_message(f"❌ Server execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("🛑 Server stopped by user")
    except Exception as e:
        log_message(f"💥 Wrapper crashed: {e}")
        sys.exit(1)