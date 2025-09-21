#!/usr/bin/env python3
"""
표준 MCP 서버 테스트
"""

import subprocess
import json
import time
import sys

def test_standard_server():
    """표준 MCP 서버 연결 테스트"""

    server_cmd = [
        '/Library/Frameworks/Python.framework/Versions/3.12/bin/python3',
        'mcp_server/portfolio_standard_server.py'
    ]

    try:
        print("🧪 포트폴리오 표준 MCP 서버 테스트 시작...")

        # 환경 설정
        import os
        env = os.environ.copy()
        env['PYTHONPATH'] = '/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester'

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

        # 초기화 요청
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }

        print("📤 초기화 요청 전송...")
        process.stdin.write(json.dumps(init_request) + '\n')
        process.stdin.flush()

        # 응답 대기 (timeout 추가)
        import select
        ready, _, _ = select.select([process.stdout], [], [], 5.0)

        if ready:
            response_line = process.stdout.readline()
            if response_line:
                response = json.loads(response_line.strip())
                server_name = response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')
                print(f"✅ 초기화 성공: {server_name}")

                # 도구 목록 요청
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                }

                print("📤 도구 목록 요청...")
                process.stdin.write(json.dumps(tools_request) + '\n')
                process.stdin.flush()

                # 도구 목록 응답
                ready, _, _ = select.select([process.stdout], [], [], 5.0)
                if ready:
                    tools_response = process.stdout.readline()
                    if tools_response:
                        tools_data = json.loads(tools_response.strip())
                        tools = tools_data.get('result', {}).get('tools', [])
                        print(f"✅ 도구 목록 수신: {len(tools)}개 도구")
                        for tool in tools:
                            print(f"  - {tool.get('name')}: {tool.get('description')}")
                        return True
                    else:
                        print("❌ 도구 목록 응답 없음")
                        return False
                else:
                    print("❌ 도구 목록 응답 시간 초과")
                    return False
            else:
                print("❌ 초기화 응답 없음")
                return False
        else:
            print("❌ 초기화 응답 시간 초과")
            stderr_output = process.stderr.read()
            if stderr_output:
                print(f"STDERR: {stderr_output}")
            return False

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False
    finally:
        if 'process' in locals():
            process.terminate()
            process.wait()

if __name__ == "__main__":
    success = test_standard_server()
    if success:
        print("✅ 표준 서버 테스트 성공!")
        sys.exit(0)
    else:
        print("❌ 표준 서버 테스트 실패!")
        sys.exit(1)