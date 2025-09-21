#!/usr/bin/env python3
"""
FastMCP 서버 래퍼 - Claude Desktop 호환성을 위한 조용한 시작
"""

import sys
import os
import subprocess

def main():
    """FastMCP 서버를 조용한 모드로 실행"""

    # 환경 변수 설정
    env = os.environ.copy()
    env['PYTHONPATH'] = '/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester'
    env['FASTMCP_QUIET'] = '1'
    env['FASTMCP_NO_BANNER'] = '1'
    env['MCP_STDIO_QUIET'] = '1'

    # FastMCP 서버 실행
    server_path = os.path.join(os.path.dirname(__file__), 'portfolio_mcp_server.py')
    python_path = '/Library/Frameworks/Python.framework/Versions/3.12/bin/python3'

    try:
        # stderr를 devnull로 리다이렉트하여 로고 출력 억제
        with open(os.devnull, 'w') as devnull:
            process = subprocess.Popen(
                [python_path, server_path],
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=devnull,  # stderr 출력 억제
                env=env,
                cwd='/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester'
            )
            process.wait()
    except KeyboardInterrupt:
        process.terminate()
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()