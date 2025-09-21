#!/usr/bin/env python3
"""
MCP 서버 연결 테스트 스크립트
"""

import subprocess
import sys
import json
import time
import os

def test_mcp_server():
    """MCP 서버 기본 연결 및 응답 테스트"""

    # 환경 설정
    env = os.environ.copy()
    env['PYTHONPATH'] = '/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester'

    # MCP 서버 시작
    server_cmd = [
        '/Library/Frameworks/Python.framework/Versions/3.12/bin/python3',
        'mcp_server/portfolio_mcp_server.py'
    ]

    try:
        print("🚀 MCP 서버 시작 중...")
        process = subprocess.Popen(
            server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd='/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester'
        )

        # 서버 시작 대기
        time.sleep(2)

        # 기본 MCP 요청 (initialize)
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        print("📤 초기화 요청 전송 중...")
        process.stdin.write(json.dumps(init_request) + '\n')
        process.stdin.flush()

        # 응답 대기
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            print(f"✅ 초기화 응답 수신: {response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")
            return True
        else:
            stderr_output = process.stderr.read()
            print(f"❌ 응답 없음. stderr: {stderr_output}")
            return False

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False
    finally:
        if 'process' in locals():
            process.terminate()
            process.wait()

if __name__ == "__main__":
    print("🧪 MCP 서버 연결 테스트 시작")
    success = test_mcp_server()

    if success:
        print("✅ MCP 서버 테스트 성공!")
        sys.exit(0)
    else:
        print("❌ MCP 서버 테스트 실패!")
        sys.exit(1)